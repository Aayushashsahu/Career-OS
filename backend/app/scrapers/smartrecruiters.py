import logging
"""
SmartRecruiters Job Board Scraper.
Scrapes SmartRecruiters-powered career pages for job listings.
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


# Popular companies using SmartRecruiters
SMARTRECRUITERS_COMPANIES = [
    ("adobe", "Adobe"), ("uber", "Uber"), ("twitter", "Twitter/X"),
    ("slack", "Slack"), ("dropbox", "Dropbox"), ("zoom", "Zoom"),
    ("snap", "Snap"), ("pinterest", "Pinterest"), ("linkedin", "LinkedIn"),
    ("spotify", "Spotify"), ("shopify", "Shopify"), ("paypal", "PayPal"),
    ("visa", "Visa"), ("Mastercard", "Mastercard"), ("oracle", "Oracle"),
    ("samsung", "Samsung"), ("nokia", "Nokia"), ("vmware", "VMware"),
    ("dell", "Dell"), ("cisco", "Cisco"), ("salesforce", "Salesforce"),
    ("servicenow", "ServiceNow"), ("palantir", "Palantir"),
]


class SmartRecruitersScraper(BaseScraper):
    name = "SmartRecruiters"
    base_url = "https://api.smartrecruiters.com/v1/companies"

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

        tasks = [_fetch_with_limit(slug, name) for slug, name in SMARTRECRUITERS_COMPANIES]
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
        return all_jobs[:50]  # Return up to 50 jobs from SmartRecruiters

    async def _fetch_board(self, slug: str, company_name: str, query: str) -> List[JobListing]:
        """Fetch jobs from a single SmartRecruiters board."""
        jobs = []
        url = f"{self.base_url}/{slug}/postings?q={urllib.parse.quote(query)}&limit=20&sort=date"
        text = await fetch_url(url, headers={"Accept": "application/json"})
        if not text:
            return jobs

        try:
            data = json.loads(text)
        except Exception:
            return jobs

        content = data.get("content", [])
        if not isinstance(content, list):
            return jobs

        for posting in content:
            title = posting.get("name", "")
            if not title:
                continue

            ref = posting.get("ref", "")
            location_data = posting.get("location", {})
            location = ""
            if isinstance(location_data, dict):
                city = location_data.get("city", "")
                country = location_data.get("country", "")
                location = f"{city}, {country}" if city else country or "Remote"
            else:
                location = str(location_data) or "Remote"

            department = posting.get("department", "")
            if isinstance(department, dict):
                department = department.get("name", "")

            employment_type = posting.get("type", "FULL_TIME")
            if isinstance(employment_type, str):
                emp_map = {"FULL_TIME": "full-time", "PART_TIME": "part-time",
                          "CONTRACT": "contract", "INTERN": "internship"}
                employment_type = emp_map.get(employment_type, "full-time")

            # Check for internship in title
            title_lower = title.lower()
            if any(k in title_lower for k in ["intern", "internship", "trainee"]):
                employment_type = "internship"

            # NOTE: Do NOT filter by query words here.
            # SmartRecruiters boards are curated company career pages.
            # Return ALL jobs and let the registry/user filter later.

            link = posting.get("applyUrl", posting.get("url", ""))
            if not link and ref:
                link = f"https://careers.smartrecruiters.com/{slug}/{ref}"
            if not link:
                link = f"https://careers.smartrecruiters.com/{slug}"

            # Parse date
            released_date = posting.get("releasedDate", "")
            posted_dt = parse_posted_date(released_date) if released_date else None

            job = JobListing(
                title=title,
                company=company_name,
                location=location,
                apply_link=link,
                source="SmartRecruiters",
                remote=self._is_remote(location),
                work_style=self._detect_work_style(location),
                employment_type=employment_type,
                skills_found=self._extract_skills_from_text(f"{title} {department}"),
                description=f"Department: {department}" if department else "",
                posted_date=released_date[:10] if isinstance(released_date, str) and len(released_date) > 10 else "",
            )

            score, badge, _ = compute_freshness(posted_dt, released_date if isinstance(released_date, str) else "")
            job.freshness_score = score
            job.freshness_badge = badge
            if posted_dt:
                job.posted_timestamp = posted_dt.timestamp()
            job.dedup_key = self._make_dedup_key(job)

            jobs.append(job)

        return jobs
