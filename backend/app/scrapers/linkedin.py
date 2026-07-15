"""
LinkedIn Jobs Scraper.
Uses LinkedIn's public job search with recency sorting.
"""
import urllib.parse
import re
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, build_query, build_location, BS4_AVAILABLE,
    get_recency_params, parse_posted_date, compute_freshness
)
from app.models.schemas import JobListing, SearchFilters


class LinkedInScraper(BaseScraper):
    name = "LinkedIn"
    base_url = "https://www.linkedin.com/jobs/search/"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:4]  # LinkedIn: up to 4 queries
        location = build_location(filters)
        recency = filters.recency if filters else "week"

        all_jobs: List[JobListing] = []
        seen_keys = set()

        for query_text, query_loc in queries:
            loc = query_loc or location
            try:
                jobs = await self._search_single(query_text, loc, recency, filters)
                for job in jobs:
                    key = job.dedup_key or self._make_dedup_key(job)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)
            except Exception:
                continue

        # If no results from multi-query, try fallback
        if not all_jobs:
            fallback_query = build_query(skills, filters, max_skills=2)
            try:
                all_jobs = await self._search_single(fallback_query, location, recency, filters)
            except Exception:
                pass

        # Do NOT return search link fallbacks.
        # Only return real jobs with actual apply URLs.

        return all_jobs

    async def _search_single(self, query: str, location: str, recency: str, filters: Optional[SearchFilters] = None) -> List[JobListing]:
        encoded_q = urllib.parse.quote_plus(query)
        encoded_loc = urllib.parse.quote_plus(location)

        # Recency filter
        recency_param = get_recency_params("linkedin", recency)

        # Experience level filter
        exp_filter = ""
        if filters and filters.experience_level:
            exp_map = {"0-1": "1%2C2", "1-3": "2%2C3", "3-5": "3%2C4", "5+": "4%2C5"}
            exp_filter = f"&f_E={exp_map.get(filters.experience_level, '1%2C2')}"

        all_jobs: List[JobListing] = []
        seen_keys = set()

        # Paginate: LinkedIn uses start= param (0, 25, 50...)
        # Fetch up to 3 pages (75 results per query)
        MAX_PAGES = 3
        PAGE_SIZE = 25

        for page in range(MAX_PAGES):
            start = page * PAGE_SIZE
            url = (
                f"{self.base_url}?keywords={encoded_q}&location={encoded_loc}"
                f"&f_TPR={recency_param}&start={start}{exp_filter}"
            )

            html = await fetch_url(url)
            if not html:
                break  # No more results or error

            page_jobs = self._parse_linkedin_page(html, query, location, filters)

            # If no jobs found on this page, stop paginating
            if not page_jobs:
                break

            for job in page_jobs:
                key = job.dedup_key or self._make_dedup_key(job)
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_jobs.append(job)

        return all_jobs

    def _parse_linkedin_page(self, html: str, query: str, location: str, filters: Optional[SearchFilters] = None) -> List[JobListing]:
        """Parse a single LinkedIn search results page."""
        jobs = []

        if BS4_AVAILABLE:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            cards = soup.select(".base-card, .base-search-card, .job-search-card")
            if not cards:
                cards = soup.select("[data-tracking-control-name*='job']")

            for card in cards[:25]:
                try:
                    title_el = card.select_one(".base-search-card__title, h3, [class*='title']")
                    company_el = card.select_one(".base-search-card__subtitle, h4, [class*='company']")
                    location_el = card.select_one(".job-search-card__location, [class*='location']")
                    link_el = card.select_one("a.base-card__full-link, a[href*='linkedin.com/jobs']")
                    time_el = card.select_one("time")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    if not title or not company:
                        continue

                    loc = location_el.get_text(strip=True) if location_el else location
                    link = link_el["href"] if link_el and link_el.has_attr("href") else ""
                    if not link or "linkedin.com/search" in link:
                        continue  # Skip search redirect links
                    posted = time_el.get("datetime", "") if time_el else ""

                    # Parse posted date
                    posted_dt = None
                    if posted:
                        try:
                            from datetime import datetime
                            posted_dt = datetime.fromisoformat(posted.replace('Z', '+00:00').replace('+00:00', ''))
                        except Exception:
                            posted_dt = parse_posted_date(posted)

                    # Build job
                    job = JobListing(
                        title=title,
                        company=company,
                        location=loc,
                        apply_link=link,
                        source="LinkedIn",
                        remote=self._is_remote(loc),
                        work_style=self._detect_work_style(loc),
                        employment_type=filters.job_type if filters else "internship",
                        skills_found=self._extract_skills_from_text(f"{title} {company} {loc}"),
                        posted_date=posted[:10] if posted else "",
                        description=f"Found on LinkedIn matching: {query}",
                    )

                    # Apply freshness
                    score, badge, _ = compute_freshness(posted_dt, posted)
                    job.freshness_score = score
                    job.freshness_badge = badge
                    if posted_dt:
                        job.posted_timestamp = posted_dt.timestamp()
                    job.dedup_key = self._make_dedup_key(job)

                    jobs.append(job)
                except Exception:
                    continue

        return jobs
