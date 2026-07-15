"""
Ashby Job Board Scraper.
Scrapes Ashby-powered career pages for job listings.
Ashby is used by many modern startups.
"""
import urllib.parse
import json
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, fetch_json, build_query, BS4_AVAILABLE,
    parse_posted_date, compute_freshness, _MAX_CONCURRENT
)
from app.models.schemas import JobListing, SearchFilters


# Popular companies using Ashby
ASHBY_COMPANIES = [
    ("anthropic", "Anthropic"), ("openai", "OpenAI"), ("stripe", "Stripe"),
    ("vercel", "Vercel"), ("linear", "Linear"), ("resend", "Resend"),
    ("cal.com", "Cal.com"), ("posthog", "PostHog"), ("retool", "Retool"),
    ("supabase", "Supabase"), ("planetscale", "PlanetScale"),
    ("neon", "Neon"), ("clerk", "Clerk"), ("workos", "WorkOS"),
    ("mintlify", "Mintlify"), ("midday", "Midday"), ("tugboat", "Tugboat"),
    ("dub", "Dub"), ("documenso", "Documenso"), ("formbricks", "Formbricks"),
    ("infisical", "Infisical"), ("unkey", "Unkey"), ("hoppscotch", "Hoppscotch"),
    ("docmost", "Docmost"), ("twenty", "Twenty"), ("twentyCRM", "Twenty CRM"),
]


class AshbyScraper(BaseScraper):
    name = "Ashby"
    base_url = "https://api.ashbyhq.com/posting-api/job-board"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:2]
        query = queries[0][0] if queries else build_query(skills, filters)

        all_jobs: List[JobListing] = []
        seen_keys = set()

        import asyncio
        sem = asyncio.Semaphore(_MAX_CONCURRENT)

        # Determine which employment types to fetch based on filters
        job_type_filter = (filters.job_type.lower() if filters and filters.job_type else "both")

        async def _fetch_with_limit(slug, company_name):
            async with sem:
                return await self._fetch_board(slug, company_name, query.lower())

        tasks = [_fetch_with_limit(slug, name) for slug, name in ASHBY_COMPANIES]
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
        return all_jobs[:50]  # Return up to 50 jobs from Ashby

    async def _fetch_board(self, slug: str, company_name: str, query: str) -> List[JobListing]:
        """Fetch jobs from a single Ashby board."""
        jobs = []
        url = f"{self.base_url}/{slug}"
        data = await fetch_json(url)
        if not data:
            return jobs

        # Ashby API v2 returns {"jobs": [...]} while v1 used {"jobPostings": [...]}
        # Handle both formats
        job_list = data.get("jobPostings", data.get("jobs", []))
        if not isinstance(job_list, list):
            return jobs

        for posting in job_list:
            title = posting.get("title", "")
            if not title:
                continue

            location = ""
            locations = posting.get("locationName", posting.get("location", ""))
            if isinstance(locations, list):
                location = ", ".join(str(l) for l in locations)
            else:
                location = str(locations) or "Remote"

            team = posting.get("teamName", posting.get("departmentName", ""))
            employment_type = posting.get("employmentType", "full-time")
            if isinstance(employment_type, str):
                employment_type = employment_type.lower()

            # Check for internship
            title_lower = title.lower()
            if any(k in title_lower for k in ["intern", "internship", "trainee"]):
                employment_type = "internship"

            # NOTE: Do NOT filter by query words here.
            # Ashby boards are curated company career pages.
            # Return ALL jobs and let the registry/user filter later.

            link = posting.get("externalUrl", posting.get("url", ""))
            if not link:
                link = f"https://jobs.ashbyhq.com/{slug}"

            # Parse date
            updated = posting.get("updatedAt", posting.get("createdAt", ""))
            posted_dt = parse_posted_date(updated) if updated else None

            job = JobListing(
                title=title,
                company=company_name,
                location=location,
                apply_link=link,
                source="Ashby",
                remote=self._is_remote(location),
                work_style=self._detect_work_style(location),
                employment_type=employment_type,
                skills_found=self._extract_skills_from_text(f"{title} {team}"),
                description=f"Team: {team}" if team else "",
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
