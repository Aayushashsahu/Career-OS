"""
Wellfound (AngelList) Scraper.
Scrapes wellfound.com for startup job listings with newest-first sorting.
"""
import urllib.parse
import json
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, build_query, build_location, BS4_AVAILABLE,
    parse_posted_date, compute_freshness
)
from app.models.schemas import JobListing, SearchFilters


class WellfoundScraper(BaseScraper):
    name = "Wellfound"
    base_url = "https://wellfound.com"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:3]
        location = build_location(filters)

        all_jobs: List[JobListing] = []
        seen_keys = set()

        for query_text, query_loc in queries:
            try:
                jobs = await self._search_single(query_text, query_loc or location, filters)
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

    async def _search_single(self, query: str, location: str, filters: Optional[SearchFilters] = None) -> List[JobListing]:
        encoded = urllib.parse.quote_plus(query)
        # Wellfound role search with newest first
        url = f"{self.base_url}/role/r/{encoded}?sort=most_recent"

        jobs = []
        html = await fetch_url(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        if not html:
            return jobs

        if BS4_AVAILABLE:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Try to extract from Next.js data or script tags
            for script in soup.select("script[type='application/json'], script[id='__NEXT_DATA__']"):
                try:
                    data = json.loads(script.get_text())
                    # Navigate Next.js data structure
                    if isinstance(data, dict):
                        props = data.get("props", {}).get("pageProps", {})
                        job_list = props.get("jobs", props.get("roles", props.get("results", [])))
                        if isinstance(job_list, list):
                            for item in job_list[:20]:
                                job = self._parse_json_job(item)
                                if job:
                                    jobs.append(job)
                except Exception:
                    continue

            # HTML fallback parsing
            if not jobs:
                card_selectors = [
                    "[class*='styles_job'], [class*='StartupJob']",
                    "div[class*='job'], div[class*='role']",
                    "a[href*='/role/'], a[href*='/startups/']",
                    "[data-test='StartupResult']",
                ]
                for selector in card_selectors:
                    cards = soup.select(selector)
                    for card in cards[:20]:
                        job = self._parse_html_card(card, query, location)
                        if job:
                            jobs.append(job)
                    if jobs:
                        break

        jobs = self._apply_freshness(jobs)
        return jobs

    def _parse_json_job(self, data: dict) -> Optional[JobListing]:
        """Parse a job from JSON data."""
        title = data.get("title", data.get("name", ""))
        if not title:
            return None

        company = data.get("startup", {}).get("name", "") if isinstance(data.get("startup"), dict) else data.get("company_name", "Startup")
        location = data.get("location", data.get("office_locations", ["Remote"])[0] if isinstance(data.get("office_locations"), list) else "Remote")
        salary = data.get("salary", "")
        link = data.get("url", "")
        if not link and data.get("id"):
            link = f"{self.base_url}/role/{data['id']}"

        job = JobListing(
            title=title,
            company=company or "Startup",
            location=str(location),
            apply_link=link or f"{self.base_url}/role/r/{urllib.parse.quote_plus(title)}",
            source="Wellfound",
            remote=self._is_remote(str(location)),
            work_style=self._detect_work_style(str(location)),
            salary=str(salary),
            skills_found=self._extract_skills_from_text(f"{title} {data.get('description', '')}"),
            description=data.get("description", "")[:300] if data.get("description") else f"Startup role at {company}",
        )
        job.dedup_key = self._make_dedup_key(job)
        return job

    def _parse_html_card(self, card, query: str, location: str) -> Optional[JobListing]:
        """Parse a job card from HTML."""
        try:
            title_el = card.select_one("h2, h3, [class*='title'], [class*='Title']")
            company_el = card.select_one("[class*='company'], [class*='startup'], [class*='Company']")
            location_el = card.select_one("[class*='location'], [class*='Location']")
            salary_el = card.select_one("[class*='salary'], [class*='compensation']")
            link_el = card if card.name == "a" else card.select_one("a[href]")

            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                return None

            company = company_el.get_text(strip=True) if company_el else "Startup"
            loc = location_el.get_text(strip=True) if location_el else location
            salary = salary_el.get_text(strip=True) if salary_el else ""
            link = link_el.get("href", "") if link_el else ""
            if link.startswith("/"):
                link = f"{self.base_url}{link}"

            job = JobListing(
                title=title,
                company=company,
                location=loc,
                apply_link=link or f"{self.base_url}/role/r/{urllib.parse.quote_plus(title)}",
                source="Wellfound",
                remote=self._is_remote(loc),
                work_style=self._detect_work_style(loc),
                salary=salary,
                skills_found=self._extract_skills_from_text(f"{title} {company}"),
                description=f"Startup role at {company}",
            )
            job.dedup_key = self._make_dedup_key(job)
            return job
        except Exception:
            return None
