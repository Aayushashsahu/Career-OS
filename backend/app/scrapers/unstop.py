"""
Unstop (Dare2Compete) Scraper.
Scrapes unstop.com for competitions, hackathons, and job listings.
"""
import urllib.parse
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, build_query, BS4_AVAILABLE,
    parse_posted_date, compute_freshness
)
from app.models.schemas import JobListing, SearchFilters


class UnstopScraper(BaseScraper):
    name = "Unstop"
    base_url = "https://unstop.com"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:2]

        all_jobs: List[JobListing] = []
        seen_keys = set()

        for query_text, _ in queries:
            try:
                jobs = await self._search_single(query_text, filters)
                for job in jobs:
                    key = job.dedup_key or self._make_dedup_key(job)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)
            except Exception:
                continue

        # Do NOT return search link fallbacks.
        # Only return real jobs with actual apply URLs.

        return all_jobs

    async def _search_single(self, query: str, filters: Optional[SearchFilters] = None) -> List[JobListing]:
        encoded = urllib.parse.quote_plus(query)

        # Search multiple categories
        urls = [
            (f"{self.base_url}/jobs?query={encoded}&sort=newest", "internship"),
            (f"{self.base_url}/hackathons?query={encoded}&sort=newest", "hackathon"),
            (f"{self.base_url}/competitions?query={encoded}&sort=newest", "competition"),
        ]

        jobs = []
        seen = set()

        for url, opp_type in urls:
            html = await fetch_url(url)
            if not html:
                continue

            if BS4_AVAILABLE:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")

                cards = soup.select(
                    ".card-container, .job-card, [class*='card'], "
                    "[class*='opportunity'], [class*='listing']"
                )

                for card in cards[:15]:
                    try:
                        link_el = card.select_one("a[href]")
                        if not link_el:
                            continue

                        title_el = card.select_one(
                            "h3, h4, .title, [class*='title'], [class*='name']"
                        )
                        company_el = card.select_one(
                            ".company, [class*='company'], [class*='organization'], "
                            "[class*='organizer']"
                        )
                        location_el = card.select_one(
                            ".location, [class*='location']"
                        )
                        deadline_el = card.select_one(
                            "[class*='deadline'], [class*='date']"
                        )

                        title = title_el.get_text(strip=True) if title_el else "Opportunity"
                        company = company_el.get_text(strip=True) if company_el else "Unstop"
                        loc = location_el.get_text(strip=True) if location_el else "Online/India"
                        deadline = deadline_el.get_text(strip=True) if deadline_el else ""

                        link = link_el.get("href", url)
                        if link.startswith("/"):
                            link = f"{self.base_url}{link}"

                        key = f"{title.lower()}-{company.lower()}"
                        if key in seen:
                            continue
                        seen.add(key)

                        is_remote = self._is_remote(loc) or "online" in loc.lower()

                        desc = f"Found on Unstop"
                        if deadline:
                            desc += f" | Deadline: {deadline}"

                        job = JobListing(
                            title=title,
                            company=company,
                            location=loc,
                            apply_link=link,
                            source="Unstop",
                            remote=is_remote,
                            work_style=self._detect_work_style(loc),
                            employment_type=opp_type,
                            skills_found=self._extract_skills_from_text(f"{title} {company}"),
                            description=desc,
                        )
                        job.dedup_key = self._make_dedup_key(job)
                        jobs.append(job)
                    except Exception:
                        continue

        return jobs
