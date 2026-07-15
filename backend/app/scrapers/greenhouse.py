"""
Greenhouse Job Board Scraper.
Scrapes Greenhouse-powered career pages for job listings.
Expanded to 50+ popular companies.
"""
import urllib.parse
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_json, build_query, BS4_AVAILABLE,
    parse_posted_date, compute_freshness, _MAX_CONCURRENT
)
from app.models.schemas import JobListing, SearchFilters


# Popular companies using Greenhouse (50+)
GREENHOUSE_COMPANIES = [
    ("airbnb", "Airbnb"), ("stripe", "Stripe"), ("discord", "Discord"),
    ("figma", "Figma"), ("notion", "Notion"), ("gitlab", "GitLab"),
    ("hashicorp", "HashiCorp"), ("databricks", "Databricks"),
    ("rippling", "Rippling"), ("vercel", "Vercel"), ("supabase", "Supabase"),
    ("linear", "Linear"), ("posthog", "PostHog"), ("plaid", "Plaid"),
    ("brex", "Brex"), ("ramp", "Ramp"), ("canva", "Canva"),
    ("loom", "Loom"), ("webflow", "Webflow"), ("retool", "Retool"),
    ("zapier", "Zapier"), ("cal.com", "Cal.com"), ("planetscale", "PlanetScale"),
    ("neon", "Neon"), ("clerk", "Clerk"), ("workos", "WorkOS"),
    ("resend", "Resend"), ("midday", "Midday"), ("livekit", "LiveKit"),
    ("mintlify", "Mintlify"), ("perplexity", "Perplexity"), ("modal", "Modal"),
    ("replicate", "Replicate"), ("together", "Together AI"), ("anyscale", "Anyscale"),
    ("dbt", "dbt Labs"), ("airbyte", "Airbyte"), ("prefect", "Prefect"),
    ("dagster", "Dagster"), ("weaviate", "Weaviate"), ("pinecone", "Pinecone"),
    ("chroma", "Chroma"), ("qdrant", "Qdrant"), ("langchain", "LangChain"),
    ("Weights & Biases", "Weights & Biases"), ("Scale AI", "Scale AI"),
    ("Snorkel AI", "Snorkel AI"), ("Weights & Biases", "W&B"),
    ("Harmonic", "Harmonic"), ("Cursor", "Cursor"), ("Codeium", "Codeium"),
]


class GreenhouseScraper(BaseScraper):
    name = "Greenhouse"
    base_url = "https://boards-api.greenhouse.io/v1/boards"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:2]
        query = queries[0][0] if queries else build_query(skills, filters)

        all_jobs: List[JobListing] = []
        seen_keys = set()

        import asyncio
        # Search all boards concurrently with semaphore to limit concurrency
        sem = asyncio.Semaphore(_MAX_CONCURRENT)

        # Determine which employment types to fetch based on filters
        job_type_filter = (filters.job_type.lower() if filters and filters.job_type else "both")

        async def _fetch_with_limit(slug, company_name):
            async with sem:
                return await self._fetch_board(slug, company_name, query.lower(), filters)

        tasks = [_fetch_with_limit(slug, name) for slug, name in GREENHOUSE_COMPANIES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                for job in result:
                    # Filter by employment type if specified
                    if job_type_filter == "internship" and job.employment_type != "internship":
                        continue
                    if job_type_filter == "full-time" and job.employment_type == "internship":
                        continue
                    key = job.dedup_key or self._make_dedup_key(job)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)

        all_jobs = self._apply_freshness(all_jobs)
        return all_jobs[:60]  # Return up to 60 jobs from Greenhouse

    async def _fetch_board(self, slug: str, company_name: str, query: str, filters: Optional[SearchFilters] = None) -> List[JobListing]:
        """Fetch jobs from a single Greenhouse board."""
        jobs = []
        url = f"{self.base_url}/{slug}/jobs?content=true"
        data = await fetch_json(url)
        if not data:
            return jobs

        # Greenhouse API v2 returns {"jobs": [...], "meta": {...}}
        # Old format was {"departments": [{"jobs": [...]}]}
        # Handle both formats
        positions = []
        if isinstance(data, dict):
            # New format: flat jobs list at top level
            if "jobs" in data and isinstance(data["jobs"], list):
                positions = data["jobs"]
            # Old format: nested in departments
            elif "departments" in data:
                for dept in data["departments"]:
                    if isinstance(dept, dict):
                        positions.extend(dept.get("jobs", []))

        for position in positions:
            if not isinstance(position, dict):
                continue
            title = position.get("title", "")
            if not title:
                continue

            location = position.get("location", {})
            if isinstance(location, dict):
                loc_name = location.get("name", "Remote")
            elif isinstance(location, str) and location:
                loc_name = location
            else:
                loc_name = "Remote"

            link = position.get("absolute_url", f"https://boards.greenhouse.io/{slug}")

            # Parse date
            updated = position.get("updated_at", position.get("created_at", ""))
            posted_dt = parse_posted_date(updated) if updated else None

            # Check for internship
            title_lower = title.lower()
            emp_type = "full-time"
            if any(k in title_lower for k in ["intern", "internship", "trainee"]):
                emp_type = "internship"

            # Extract department name
            dept_name = "General"
            if "departments" in position and isinstance(position["departments"], list):
                for d in position["departments"]:
                    if isinstance(d, dict) and d.get("name"):
                        dept_name = d["name"]
                        break
            elif "departments" in position and isinstance(position["departments"], str):
                dept_name = position["departments"]

            job = JobListing(
                title=title,
                company=company_name,
                location=loc_name,
                apply_link=link,
                source="Greenhouse",
                remote=self._is_remote(loc_name),
                work_style=self._detect_work_style(loc_name),
                employment_type=emp_type,
                skills_found=self._extract_skills_from_text(f"{title} {dept_name}"),
                description=f"Department: {dept_name}",
                posted_date=updated[:10] if isinstance(updated, str) and len(updated) > 10 else "",
            )

            score, badge, _ = compute_freshness(posted_dt, updated if isinstance(updated, str) else "")
            job.freshness_score = score
            job.freshness_badge = badge
            if posted_dt:
                job.posted_timestamp = posted_dt.timestamp()
            job.dedup_key = self._make_dedup_key(job)

            jobs.append(job)

        return jobs
