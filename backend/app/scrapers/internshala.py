"""
Internshala Scraper.
Scrapes internshala.com for internship and job listings with newest-first sorting.
"""
import urllib.parse
import re
from datetime import datetime, timedelta
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, build_query, build_location, BS4_AVAILABLE,
    parse_posted_date, compute_freshness
)
from app.models.schemas import JobListing, SearchFilters


class InternshalaScraper(BaseScraper):
    name = "Internshala"
    base_url = "https://internshala.com/internships"
    jobs_url = "https://internshala.com/jobs"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:3]

        all_jobs: List[JobListing] = []
        seen_keys = set()

        # Search both internships and jobs
        search_urls = []
        job_type = (filters.job_type if filters else "both").lower()

        for query_text, query_loc in queries:
            encoded = urllib.parse.quote_plus(query_text)
            if job_type in ("internship", "both"):
                search_urls.append((f"{self.base_url}/keywords-{encoded}?sort=newest", query_text, "internship"))
            if job_type in ("full-time", "both"):
                search_urls.append((f"{self.jobs_url}/keywords-{encoded}?sort=newest", query_text, "full-time"))

        if not search_urls:
            encoded = urllib.parse.quote_plus(build_query(skills, filters))
            search_urls.append((f"{self.base_url}/keywords-{encoded}?sort=newest", encoded, "internship"))

        for url, query, emp_type in search_urls:
            try:
                jobs = await self._parse_internshala_page(url, query, emp_type, filters)
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

    async def _parse_internshala_page(self, url: str, query: str, emp_type: str, filters: Optional[SearchFilters] = None) -> List[JobListing]:
        jobs = []
        html = await fetch_url(url)
        if not html:
            return jobs

        if BS4_AVAILABLE:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Internshala uses various card selectors
            cards = soup.select(
                ".individual_internship, .internship-card, "
                "[class*='internship_card'], [class*='individual_internship'], "
                "a[href*='/internship/detail/'], a[href*='/job/detail/']"
            )

            if not cards:
                cards = soup.select(".container-fluid .individual_internship_details")

            seen = set()
            for card in cards[:20]:
                try:
                    # Find the link element
                    link_el = card if card.name == "a" else card.select_one("a[href*='/internship/'], a[href*='/job/']")
                    if not link_el:
                        continue

                    title_el = card.select_one(
                        "h3, .job-title, [class*='title'], .profile, "
                        "span[data-testid='job-title'], div.course_name"
                    )
                    company_el = card.select_one(
                        ".company-name, .company, [class*='company'], "
                        "span[data-testid='company-name'], p.company_name"
                    )
                    location_el = card.select_one(
                        ".location, [class*='location'], span[data-testid='location']"
                    )
                    stipend_el = card.select_one(
                        ".stipend, [class*='stipend'], span[data-testid='stipend']"
                    )
                    duration_el = card.select_one(
                        ".duration, [class*='duration']"
                    )
                    # Date element
                    date_el = card.select_one(
                        "[class*='date'], .posted, [class*='posted'], "
                        "span[data-testid='posted-date']"
                    )

                    title = title_el.get_text(strip=True) if title_el else "Internship"
                    company = company_el.get_text(strip=True) if company_el else "Company"
                    if not title or title == "Internship":
                        # Try to extract from link text
                        link_text = link_el.get_text(strip=True)
                        if link_text and len(link_text) > 3:
                            title = link_text[:100]

                    loc = location_el.get_text(strip=True) if location_el else "India"
                    stipend = stipend_el.get_text(strip=True) if stipend_el else ""
                    duration = duration_el.get_text(strip=True) if duration_el else ""
                    date_text = date_el.get_text(strip=True) if date_el else ""

                    link = link_el.get("href", url)
                    if link.startswith("/"):
                        link = f"https://internshala.com{link}"

                    key = f"{title.lower()}-{company.lower()}"
                    if key in seen:
                        continue
                    seen.add(key)

                    # Parse date
                    posted_dt = parse_posted_date(date_text) if date_text else None

                    # Extract skills from title and company
                    desc_parts = [p for p in [title, company, duration, stipend] if p]

                    is_remote = self._is_remote(loc) or self._is_remote(title)
                    work_style = self._detect_work_style(loc)

                    job = JobListing(
                        title=title,
                        company=company,
                        location=loc,
                        apply_link=link,
                        source="Internshala",
                        remote=is_remote,
                        work_style=work_style,
                        stipend=stipend,
                        employment_type=emp_type,
                        skills_found=self._extract_skills_from_text(f"{title} {company}"),
                        posted_date=date_text,
                        description=f"Duration: {duration} | Stipend: {stipend}" if duration else "",
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

        # Sort by freshness
        jobs.sort(key=lambda j: j.freshness_score, reverse=True)
        return jobs
