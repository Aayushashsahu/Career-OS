"""
Indeed Scraper.
Scrapes indeed.com with recency sorting and date extraction.
"""
import urllib.parse
import re
from datetime import datetime, timedelta
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, build_query, build_location, BS4_AVAILABLE,
    get_recency_params, parse_posted_date, compute_freshness
)
from app.models.schemas import JobListing, SearchFilters


class IndeedScraper(BaseScraper):
    name = "Indeed"
    base_url = "https://in.indeed.com/jobs"
    alt_base = "https://www.indeed.com/jobs"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:4]
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

        if not all_jobs:
            # Fallback with single query
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
        recency_param = get_recency_params("indeed", recency)

        # Try both IN and US Indeed
        base_urls = [self.base_url, self.alt_base]

        # Paginate: Indeed uses start= param (0, 10, 20...)
        # Fetch up to 3 pages per base URL (30 results per query)
        MAX_PAGES = 3
        PAGE_SIZE = 10

        for base_url in base_urls:
            all_jobs: List[JobListing] = []
            seen_keys = set()

            for page in range(MAX_PAGES):
                start = page * PAGE_SIZE
                url = (
                    f"{base_url}?q={encoded_q}&l={encoded_loc}"
                    f"&fromage={recency_param}&sort=date&start={start}"
                )

                page_jobs = await self._parse_indeed_page(url, query, location, filters)

                if not page_jobs:
                    break  # No more results

                for job in page_jobs:
                    key = job.dedup_key or self._make_dedup_key(job)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)

            if all_jobs:
                return all_jobs

        return []

    async def _parse_indeed_page(self, url: str, query: str, location: str, filters: Optional[SearchFilters] = None) -> List[JobListing]:
        jobs = []
        html = await fetch_url(url)
        if not html:
            return jobs

        if BS4_AVAILABLE:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Indeed uses various card selectors
            cards = soup.select(
                ".job_seen_beacon, .jobsearch-SerpJobCard, .result, [data-jk], "
                "td.resultContent, .mosaic-provider-jobcards .result, "
                ".jobsearch-ResultsList > div > div"
            )

            for card in cards[:20]:
                try:
                    title_el = card.select_one(
                        "h2 a, .jobTitle a, [class*='title'] a, a.jcs-JobTitle, "
                        "a[data-jk], span.jobTitle"
                    )
                    company_el = card.select_one(
                        ".companyName, .company, [class*='company'], span[data-testid='company-name']"
                    )
                    location_el = card.select_one(
                        ".companyLocation, [class*='location'], div[data-testid='text-location']"
                    )
                    salary_el = card.select_one(
                        ".salary-snippet, [class*='salary'], div[data-testid='attribute_snippet_testid']"
                    )
                    snippet_el = card.select_one(
                        ".job-snippet, [class*='snippet'], .jobCardShelfContainer"
                    )
                    # Date element
                    date_el = card.select_one(
                        ".date, [class*='date'], span[data-testid='myJobsStateDate']"
                    )

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    if not title:
                        continue

                    loc = location_el.get_text(strip=True) if location_el else location
                    salary = salary_el.get_text(strip=True) if salary_el else ""
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    date_text = date_el.get_text(strip=True) if date_el else ""

                    # Get link
                    link = ""
                    if title_el and title_el.name == "a":
                        link = title_el.get("href", "")
                    elif title_el:
                        parent_a = title_el.find_parent("a")
                        if parent_a:
                            link = parent_a.get("href", "")
                    if link.startswith("/"):
                        link = f"https://in.indeed.com{link}"

                    # Parse date
                    posted_dt = parse_posted_date(date_text) if date_text else None

                    # Extract skills
                    desc_text = f"{title} {company} {snippet}"

                    job = JobListing(
                        title=title,
                        company=company,
                        location=loc,
                        apply_link=link or url,
                        source="Indeed",
                        remote=self._is_remote(loc) or self._is_remote(snippet),
                        work_style=self._detect_work_style(loc),
                        salary=salary,
                        employment_type=filters.job_type if filters else "internship",
                        skills_found=self._extract_skills_from_text(desc_text),
                        posted_date=date_text,
                        description=snippet[:300] if snippet else "",
                    )

                    # Apply freshness
                    score, badge, _ = compute_freshness(posted_dt, date_text)
                    job.freshness_score = score
                    job.freshness_badge = badge
                    if posted_dt:
                        job.posted_timestamp = posted_dt.timestamp()
                    job.dedup_key = self._make_dedup_key(job)

                    jobs.append(job)
                except Exception:
                    continue

        return jobs
