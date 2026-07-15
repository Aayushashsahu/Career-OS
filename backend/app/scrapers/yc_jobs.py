"""
YC Work at a Startup Scraper.
Scrapes Y Combinator's job board for startup listings.
"""
import urllib.parse
import json
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, build_query, BS4_AVAILABLE,
    parse_posted_date, compute_freshness
)
from app.models.schemas import JobListing, SearchFilters


class YCJobsScraper(BaseScraper):
    name = "YC Jobs"
    base_url = "https://www.workatastartup.com/jobs"

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

        # Try multiple YC endpoints
        api_urls = [
            f"https://www.workatastartup.com/api/v1/jobs?query={encoded}&limit=30&sort=newest",
            f"https://www.workatastartup.com/api/v1/jobs?role={encoded}&limit=30&sort=newest",
        ]

        jobs = []
        for api_url in api_urls:
            data = await fetch_json(api_url) if hasattr(self, '_fetch_json') else None
            if not data:
                text = await fetch_url(api_url, headers={"Accept": "application/json"})
                if text:
                    try:
                        data = json.loads(text)
                    except Exception:
                        data = None

            if data and isinstance(data, list):
                for item in data[:20]:
                    job = self._parse_job(item)
                    if job:
                        jobs.append(job)
                break
            elif data and isinstance(data, dict):
                job_list = data.get("jobs", data.get("results", []))
                if isinstance(job_list, list):
                    for item in job_list[:20]:
                        job = self._parse_job(item)
                        if job:
                            jobs.append(job)
                    break

        # HTML fallback
        if not jobs:
            alt_url = f"{self.base_url}?query={encoded}"
            html = await fetch_url(alt_url)
            if html and BS4_AVAILABLE:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select("[class*='job'], [class*='listing'], a[href*='/jobs/']")
                for card in cards[:15]:
                    title_el = card.select_one("h3, h4, [class*='title']")
                    company_el = card.select_one("[class*='company'], [class*='startup']")
                    link_el = card if card.name == "a" else card.select_one("a[href]")

                    title = title_el.get_text(strip=True) if title_el else "Role"
                    company = company_el.get_text(strip=True) if company_el else "YC Startup"
                    link = link_el.get("href", alt_url) if link_el else alt_url
                    if link.startswith("/"):
                        link = f"https://www.workatastartup.com{link}"

                    job = JobListing(
                        title=title,
                        company=company,
                        location="Remote",
                        apply_link=link,
                        source="YC Jobs",
                        remote=True,
                        work_style="remote",
                        skills_found=self._extract_skills_from_text(title),
                    )
                    job.dedup_key = self._make_dedup_key(job)
                    jobs.append(job)

        return jobs

    def _parse_job(self, item: dict) -> Optional[JobListing]:
        """Parse a single job from API response."""
        title = item.get("title", "")
        if not title:
            return None

        company = item.get("company_name", item.get("startup_name", "YC Startup"))
        location = item.get("location", "Remote")
        url = item.get("url", "")
        if not url and item.get("id"):
            url = f"{self.base_url}#job-{item['id']}"

        posted = item.get("posted_at", item.get("created_at", ""))

        job = JobListing(
            title=title,
            company=company or "YC Startup",
            location=location,
            apply_link=url or f"{self.base_url}?query={urllib.parse.quote_plus(title)}",
            source="YC Jobs",
            remote=self._is_remote(location),
            work_style=self._detect_work_style(location),
            salary=item.get("salary", ""),
            description=item.get("description", "")[:300] if item.get("description") else "",
            skills_found=self._extract_skills_from_text(f"{title} {item.get('description', '')}"),
            posted_date=posted[:10] if isinstance(posted, str) and len(posted) > 10 else str(posted) if posted else "",
        )

        posted_dt = parse_posted_date(posted) if posted else None
        score, badge, _ = compute_freshness(posted_dt, str(posted) if posted else "")
        job.freshness_score = score
        job.freshness_badge = badge
        if posted_dt:
            job.posted_timestamp = posted_dt.timestamp()
        job.dedup_key = self._make_dedup_key(job)
        return job
