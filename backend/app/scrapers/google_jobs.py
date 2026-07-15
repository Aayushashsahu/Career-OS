"""
Google Jobs Scraper.
Uses Google Jobs as a DISCOVERY LAYER only.
Resolves actual job posting URLs (Greenhouse, Lever, Workday, etc.).
NEVER generates Google search links as apply URLs.
"""
import urllib.parse
import re
import json
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, build_query, build_location, BS4_AVAILABLE,
    parse_posted_date, compute_freshness
)
from app.models.schemas import JobListing, SearchFilters

# Known ATS domains that Google Jobs may link to
ATS_DOMAINS = {
    "lever.co": "Lever",
    "greenhouse.io": "Greenhouse",
    "boards.greenhouse.io": "Greenhouse",
    "ashbyhq.com": "Ashby",
    "jobs.ashbyhq.com": "Ashby",
    "workday.com": "Workday",
    "myworkdayjobs.com": "Workday",
    "smartrecruiters.com": "SmartRecruiters",
    "bamboohr.com": "BambooHR",
    "icims.com": "iCIMS",
    "jobvite.com": "Jobvite",
    "linkedin.com": "LinkedIn",
    "indeed.com": "Indeed",
    "glassdoor.com": "Glassdoor",
    "wellfound.com": "Wellfound",
    "builtin.com": "BuiltIn",
    "workatastartup.com": "YC Jobs",
}


def _classify_ats_source(url: str) -> Optional[str]:
    """Identify the ATS from a URL. Returns ATS name or None."""
    url_lower = url.lower()
    for domain, ats_name in ATS_DOMAINS.items():
        if domain in url_lower:
            return ats_name
    return None


class GoogleJobsScraper(BaseScraper):
    name = "Google Jobs"
    base_url = "https://www.google.com/search"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        from app.services.query_generator import generate_search_queries
        queries = generate_search_queries(skills, filters)[:3]
        location = build_location(filters)

        all_jobs: List[JobListing] = []
        seen_keys = set()

        for query_text, query_loc in queries:
            loc = query_loc or location
            try:
                jobs = await self._search_google_jobs(query_text, loc, filters)
                for job in jobs:
                    key = job.dedup_key or self._make_dedup_key(job)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)
            except Exception:
                continue

        # CRITICAL: Only keep jobs with real apply URLs (not Google redirects)
        real_jobs = []
        for job in all_jobs:
            apply_url = job.apply_link or ""
            # Skip jobs that point to Google search
            if "google.com/search" in apply_url or "google.com/url" in apply_url:
                continue
            # Skip jobs with empty or placeholder URLs
            if not apply_url or apply_url.startswith("https://www.google.com"):
                continue
            real_jobs.append(job)

        # Apply freshness
        real_jobs = self._apply_freshness(real_jobs)
        return real_jobs[:25]

    async def _search_google_jobs(self, query: str, location: str, filters: Optional[SearchFilters] = None) -> List[JobListing]:
        """Search Google Jobs and extract actual job cards with real URLs."""
        search_q = f"{query} jobs"
        if location and location.lower() not in query.lower():
            search_q += f" near {location}"

        encoded_q = urllib.parse.quote_plus(search_q)
        url = f"{self.base_url}?q={encoded_q}&ibp=htl;jobs"

        jobs = []
        html = await fetch_url(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        })

        if not html:
            return jobs

        if BS4_AVAILABLE:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Method 1: Extract from JSON-LD structured data
            for script in soup.select("script[type='application/ld+json']"):
                try:
                    text = script.get_text()
                    data = json.loads(text)
                    if isinstance(data, list):
                        for item in data:
                            if item.get("@type") == "JobPosting":
                                job = self._parse_structured_job(item, query)
                                if job and self._has_real_apply_url(job):
                                    jobs.append(job)
                    elif isinstance(data, dict) and data.get("@type") == "JobPosting":
                        job = self._parse_structured_job(data, query)
                        if job and self._has_real_apply_url(job):
                            jobs.append(job)
                except Exception:
                    continue

            # Method 2: Extract from inline script data
            for script in soup.select("script"):
                text = script.get_text()
                if not text:
                    continue
                json_matches = re.findall(r'\{[^{}]*"@type"\s*:\s*"JobPosting"[^{}]*\}', text)
                for jm in json_matches[:10]:
                    try:
                        data = json.loads(jm)
                        job = self._parse_structured_job(data, query)
                        if job and self._has_real_apply_url(job):
                            jobs.append(job)
                    except json.JSONDecodeError:
                        continue

            # Method 3: Parse HTML cards
            if not jobs:
                card_selectors = [
                    "[data-ved] [class*='iFjolb']",
                    "[jscontroller] [class*='BjJfJf']",
                    "li[class*='iFjolb']",
                ]
                for selector in card_selectors:
                    cards = soup.select(selector)
                    for card in cards[:20]:
                        job = self._parse_html_card(card, query, location)
                        if job and self._has_real_apply_url(job):
                            jobs.append(job)
                    if jobs:
                        break

            # Method 4: Parse links to known ATS platforms
            if not jobs:
                for a in soup.select("a[href]"):
                    href = a.get("href", "")
                    link_text = a.get_text(strip=True)
                    if not link_text or len(link_text) < 5:
                        continue

                    # Check if this link points to a known ATS
                    ats_source = _classify_ats_source(href)
                    if ats_source:
                        # Extract title and company from link text
                        title_parts = link_text.split(" - ")
                        if len(title_parts) >= 2:
                            title = title_parts[0].strip()
                            company = title_parts[1].strip()
                        else:
                            title = link_text
                            company = "Company"

                        jobs.append(JobListing(
                            title=title[:100],
                            company=company[:100],
                            location=location,
                            apply_link=href,
                            source="Google Jobs",
                            remote=self._is_remote(link_text),
                            skills_found=self._extract_skills_from_text(link_text),
                            description=f"Discovered via Google Jobs, hosted on {ats_source}",
                        ))

        # Apply freshness
        jobs = self._apply_freshness(jobs)
        return jobs

    def _has_real_apply_url(self, job: JobListing) -> bool:
        """Check if a job has a real apply URL (not a Google redirect)."""
        url = job.apply_link or ""
        if not url:
            return False
        if "google.com/search" in url:
            return False
        if "google.com/url" in url:
            return False
        if url.startswith("https://www.google.com/search"):
            return False
        return True

    def _parse_structured_job(self, data: dict, query: str) -> Optional[JobListing]:
        """Parse a job from JSON-LD structured data."""
        title = data.get("title", "")
        if not title:
            return None

        org = data.get("hiringOrganization", {})
        company = org.get("name", "Company") if isinstance(org, dict) else "Company"

        loc_data = data.get("jobLocation", {})
        if isinstance(loc_data, dict):
            addr = loc_data.get("address", {})
            if isinstance(addr, dict):
                location = addr.get("addressLocality", "") or addr.get("addressRegion", "") or "Remote"
            else:
                location = str(loc_data)
        elif isinstance(loc_data, list) and loc_data:
            first = loc_data[0]
            addr = first.get("address", {}) if isinstance(first, dict) else {}
            location = addr.get("addressLocality", "Remote") if isinstance(addr, dict) else "Remote"
        else:
            location = "Remote"

        apply_url = data.get("url", "")
        if not apply_url:
            return None

        description = data.get("description", "")[:500]

        # Parse date
        date_posted = data.get("datePosted", "")
        posted_dt = parse_posted_date(date_posted) if date_posted else None

        # Parse salary
        salary_data = data.get("baseSalary", "")
        salary = ""
        if isinstance(salary_data, dict):
            val = salary_data.get("value", {})
            if isinstance(val, dict):
                salary = f"{val.get('currency', '')} {val.get('minValue', '')}-{val.get('maxValue', '')}"
        elif isinstance(salary_data, str):
            salary = salary_data

        # Employment type
        emp_type_map = {
            "FULL_TIME": "full-time",
            "PART_TIME": "part-time",
            "CONTRACTOR": "contract",
            "TEMPORARY": "contract",
            "INTERN": "internship",
            "VOLUNTEER": "volunteer",
            "PER_DIEM": "part-time",
            "OTHER": "full-time",
        }
        emp_type_raw = data.get("employmentType", "FULL_TIME")
        emp_type = emp_type_map.get(emp_type_raw, "full-time")

        job = JobListing(
            title=title,
            company=company,
            location=location,
            apply_link=apply_url,
            source="Google Jobs",
            remote=self._is_remote(location) or self._is_remote(description),
            work_style=self._detect_work_style(location),
            employment_type=emp_type,
            salary=salary,
            skills_found=self._extract_skills_from_text(f"{title} {description}"),
            posted_date=date_posted[:10] if date_posted else "",
            description=description[:300] if description else f"Discovered via Google Jobs for: {query}",
        )

        # Apply freshness
        score, badge, _ = compute_freshness(posted_dt, date_posted)
        job.freshness_score = score
        job.freshness_badge = badge
        if posted_dt:
            job.posted_timestamp = posted_dt.timestamp()
        job.dedup_key = self._make_dedup_key(job)

        return job

    def _parse_html_card(self, card, query: str, location: str) -> Optional[JobListing]:
        """Parse a job card from Google Jobs HTML."""
        try:
            title_el = card.select_one("[class*='BjJfJf'], [class*='title'], h3")
            company_el = card.select_one("[class*='vNEEBe'], [class*='company']")
            loc_el = card.select_one("[class*='Qk80Jf'], [class*='location']")
            link_el = card.select_one("a[href]")
            time_el = card.select_one("[class*='xRwPPd'], time")

            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            if not title:
                return None

            loc = loc_el.get_text(strip=True) if loc_el else location
            link = link_el["href"] if link_el and link_el.has_attr("href") else ""
            posted = time_el.get_text(strip=True) if time_el else ""

            # CRITICAL: Skip if the link is a Google redirect
            if not link or "google.com/search" in link or "google.com/url" in link:
                return None

            posted_dt = parse_posted_date(posted) if posted else None

            job = JobListing(
                title=title,
                company=company or "Company",
                location=loc,
                apply_link=link,
                source="Google Jobs",
                remote=self._is_remote(loc),
                work_style=self._detect_work_style(loc),
                employment_type=self._classify_employment_type(title),
                skills_found=self._extract_skills_from_text(f"{title} {company}"),
                posted_date=posted,
                description=f"Discovered via Google Jobs for: {query}",
            )

            score, badge, _ = compute_freshness(posted_dt, posted)
            job.freshness_score = score
            job.freshness_badge = badge
            if posted_dt:
                job.posted_timestamp = posted_dt.timestamp()
            job.dedup_key = self._make_dedup_key(job)

            return job
        except Exception:
            return None
