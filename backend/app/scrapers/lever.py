"""
Lever Job Board Scraper.
Scrapes Lever-powered career pages for job listings.
Expanded to 50+ popular companies.
"""
import urllib.parse
from datetime import datetime
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, fetch_json, build_query, BS4_AVAILABLE,
    parse_posted_date, compute_freshness, _MAX_CONCURRENT
)
from app.models.schemas import JobListing, SearchFilters


# Popular companies using Lever (50+)
LEVER_COMPANIES = [
    ("netlify", "Netlify"), ("gitlab", "GitLab"), ("betterup", "BetterUp"),
    ("coda", "Coda"), ("robinhood", "Robinhood"), ("console", "Console"),
    ("lattice", "Lattice"), ("lever", "Lever"), ("upstart", "Upstart"),
    ("nerdwallet", "NerdWallet"), ("figma", "Figma"), ("notion", "Notion"),
    ("todoist", "Todoist"), ("cashapp", "Cash App"), ("brex", "Brex"),
    ("zapier", "Zapier"), ("deel", "Deel"), ("remote.com", "Remote"),
    ("gusto", "Gusto"), ("rippling", "Rippling"), ("remitly", "Remitly"),
    ("databricks", "Databricks"), ("figma", "Figma"), ("postman", "Postman"),
    ("segment", "Segment"), ("amplitude", "Amplitude"), ("mixpanel", "Mixpanel"),
    ("heap", "Heap"), ("fullstory", "FullStory"), ("hotjar", "Hotjar"),
    ("vercel", "Vercel"), ("cloudflare", "Cloudflare"), ("fastly", "Fastly"),
    ("elastic", "Elastic"), ("mongodb", "MongoDB"), ("redis", "Redis"),
    ("confluent", "Confluent"), ("hashicorp", "HashiCorp"), ("pulumi", "Pulumi"),
    ("spacelift", "Spacelift"), ("env0", "env0"), ("firehydrant", "FireHydrant"),
    ("opsgenie", "Opsgenie"), ("pagerduty", "PagerDuty"), ("datadog", "Datadog"),
    ("newrelic", "New Relic"), ("sentry", "Sentry"), ("launchdarkly", "LaunchDarkly"),
    ("circleci", "CircleCI"), ("jfrog", "JFrog"), ("sonar", "SonarSource"),
]


class LeverScraper(BaseScraper):
    name = "Lever"
    base_url = "https://jobs.lever.co"
    api_url = "https://api.lever.co/v0/postings"

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

        tasks = [_fetch_with_limit(slug, name) for slug, name in LEVER_COMPANIES]
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
        return all_jobs[:60]  # Return up to 60 jobs from Lever

    async def _fetch_board(self, slug: str, company_name: str, query: str) -> List[JobListing]:
        """Fetch jobs from a single Lever board.
        Tries JSON API first, falls back to HTML scraping."""
        jobs = []

        # Try JSON API first
        api_url = f"{self.api_url}/{slug}?mode=json"
        data = await fetch_json(api_url)

        if data and isinstance(data, list) and len(data) > 0:
            # API works - parse JSON response
            for posting in data:
                title = posting.get("text", "")
                if not title:
                    continue

                categories = posting.get("categories", {})
                location = ""
                if isinstance(categories, dict):
                    location = (categories.get("location", "") or
                               categories.get("team", "") or
                               categories.get("department", "") or "Remote")
                commitment = categories.get("commitment", "") if isinstance(categories, dict) else ""

                link = posting.get("hostedUrl", f"https://jobs.lever.co/{slug}")

                title_lower = title.lower()

                # Parse date
                created = posting.get("createdAt", posting.get("createdAtUnix", ""))
                posted_dt = None
                if created:
                    if isinstance(created, (int, float)):
                        posted_dt = datetime.fromtimestamp(created / 1000 if created > 1e12 else created)
                    else:
                        posted_dt = parse_posted_date(str(created))

                emp_type = "full-time"
                if commitment:
                    emp_type = commitment.lower()
                if any(k in title_lower for k in ["intern", "internship"]):
                    emp_type = "internship"

                job = JobListing(
                    title=title,
                    company=company_name,
                    location=location,
                    apply_link=link,
                    source="Lever",
                    remote=self._is_remote(location),
                    work_style=self._detect_work_style(location),
                    employment_type=emp_type,
                    skills_found=self._extract_skills_from_text(f"{title} {categories.get('team', '')}"),
                    description=f"Team: {categories.get('team', 'General')}",
                    posted_date=str(created)[:10] if created else "",
                )

                score, badge, _ = compute_freshness(posted_dt, str(created) if created else "")
                job.freshness_score = score
                job.freshness_badge = badge
                if posted_dt:
                    job.posted_timestamp = posted_dt.timestamp()
                job.dedup_key = self._make_dedup_key(job)

                jobs.append(job)

            return jobs
