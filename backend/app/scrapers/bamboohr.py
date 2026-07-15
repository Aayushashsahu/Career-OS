import logging
"""
BambooHR Job Board Scraper.
Scrapes BambooHR-powered career pages for job listings.
"""
import urllib.parse
import json
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, build_query, BS4_AVAILABLE,
    parse_posted_date, compute_freshness, _MAX_CONCURRENT
)
import logging
logger = logging.getLogger(__name__)

from app.models.schemas import JobListing, SearchFilters


# Popular companies known to use BambooHR for their job boards
# These are verified BambooHR-powered career pages
BAMBOOHR_COMPANIES = [
    ("trinitycore", "TrinityCore"), ("hopper", "Hopper"), ("lulus", "Lulus"),
    ("shipt", "Shipt"), ("betterup", "BetterUp"), ("loom", "Loom"),
    ("superhuman", "Superhuman"), ("retool", "Retool"), ("plaid", "Plaid"),
    ("mercury", "Mercury"), ("ramp", "Ramp"), ("rappi", "Rappi"),
    ("dooly", "Dooly"), ("lemonade", "Lemonade"), ("codecademy", "Codecademy"),
    ("artsy", "Artsy"), ("triplebyte", "Triplebyte"), ("gusto", "Gusto"),
]


class BambooHRScraper(BaseScraper):
    name = "BambooHR"
    base_url = "https://api.bamboohr.com/api/gateboards"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:2]
        query = queries[0][0] if queries else build_query(skills, filters)

        all_jobs: List[JobListing] = []
        job_type_filter = (filters.job_type.lower() if filters and filters.job_type else "both")
        seen_keys = set()

        import asyncio
        sem = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _fetch_with_limit(slug, company_name):
            async with sem:
                return await self._fetch_board(slug, company_name, query.lower())

        tasks = [_fetch_with_limit(slug, name) for slug, name in BAMBOOHR_COMPANIES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                for job in result:
                    key = job.dedup_key or self._make_dedup_key(job)
                    if job_type_filter == "internship" and job.employment_type != "internship":
                        continue
                    if job_type_filter == "full-time" and job.employment_type == "internship":
                        continue
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)

        all_jobs = self._apply_freshness(all_jobs)
        return all_jobs[:40]  # Return up to 40 jobs from BambooHR

    async def _fetch_board(self, slug: str, company_name: str, query: str) -> List[JobListing]:
        """Fetch jobs from a single BambooHR board."""
        jobs = []
        url = f"{self.base_url}/{slug}/jobs"
        text = await fetch_url(url, headers={"Accept": "application/json"})
        if not text:
            return jobs

        try:
            data = json.loads(text)
        except Exception:
            return jobs

        job_list = data.get("jobs", [])
        if not isinstance(job_list, list):
            return jobs

        for posting in job_list:
            title = posting.get("title", posting.get("jobTitle", ""))
            if not title:
                continue

            location = posting.get("location", posting.get("city", "Remote"))
            if isinstance(location, dict):
                city = location.get("city", "")
                state = location.get("state", "")
                country = location.get("country", "")
                location = f"{city}, {state}, {country}" if city else country or "Remote"

            department = posting.get("department", posting.get("team", ""))

            # NOTE: Do NOT filter by query words here.
            # BambooHR boards are curated company career pages.
            # Return ALL jobs and let the registry/user filter later.
            title_lower = title.lower()

            link = posting.get("url", posting.get("applyUrl", ""))
            if not link:
                link = f"https://jobs.bamboohr.com/{slug}"

            emp_type = "full-time"
            if any(k in title_lower for k in ["intern", "internship"]):
                emp_type = "internship"

            # Parse date
            created = posting.get("createdAt", posting.get("postedAt", ""))
            posted_dt = parse_posted_date(str(created)) if created else None

            job = JobListing(
                title=title,
                company=company_name,
                location=str(location),
                apply_link=link,
                source="BambooHR",
                remote=self._is_remote(str(location)),
                work_style=self._detect_work_style(str(location)),
                employment_type=emp_type,
                skills_found=self._extract_skills_from_text(f"{title} {department}"),
                description=f"Department: {department}" if department else "",
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
