"""
HuggingFace Careers Scraper.
Scrapes job listings from HuggingFace's careers page.
"""
import logging
import re
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_url, parse_posted_date, compute_freshness,
    BS4_AVAILABLE,
)
from app.models.schemas import JobListing, SearchFilters

logger = logging.getLogger(__name__)


class HuggingFaceScraper(BaseScraper):
    """Scrapes HuggingFace careers page for AI/ML job listings."""

    name = "HuggingFace"
    base_url = "https://huggingface.co/jobs"

    # HuggingFace has a public careers API
    API_URL = "https://apply.workable.com/api/v3/widget/accounts/huggingface"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        jobs: List[JobListing] = []
        try:
            text = await fetch_url(self.API_URL, headers={"Accept": "application/json"})
            if not text:
                # Fallback to careers page
                text = await fetch_url(self.base_url)

            if not text:
                return jobs

            import json
            try:
                data = json.loads(text)
            except Exception:
                data = None

            if data and isinstance(data, dict) and "jobs" in data:
                # Workable API format
                for item in data["jobs"]:
                    try:
                        title = item.get("title", "")
                        department = item.get("department", "")
                        city = item.get("city", "")
                        country = item.get("country", "")
                        url = item.get("url", "")
                        description_short = item.get("description_short", "")

                        location = ", ".join(filter(None, [city, country])) or "Remote"

                        query_words = [s.lower() for s in skills] if skills else []
                        text_to_check = f"{title} {department} {description_short}".lower()
                        if query_words and not any(w in text_to_check for w in query_words):
                            continue

                        score, badge, _ = compute_freshness(None, "")

                        job = JobListing(
                            title=title,
                            company="HuggingFace",
                            location=location,
                            description=description_short[:500],
                            apply_link=url,
                            source=self.name,
                            remote=True,
                            employment_type="full-time",
                            skills_found=self._extract_skills_from_text(text_to_check),
                            company_logo="https://huggingface.co/hubfs/huggingface_logo.svg",
                            posted_date=item.get("created_at", ""),
                        )
                        job.freshness_score = score
                        job.freshness_badge = badge
                        job.work_style = "remote" if "remote" in location.lower() or "anywhere" in location.lower() else "hybrid"
                        job.dedup_key = self._make_dedup_key(job)
                        jobs.append(job)
                    except Exception as e:
                        logger.debug(f"HuggingFace job parse error: {e}")
                        continue
            elif BS4_AVAILABLE:
                # Fallback: parse HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(text, "html.parser")
                links = soup.select("a[href*='/jobs/'], a[href*='workable']")
                seen_titles = set()
                for link in links:
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5 or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    href = link.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"https://huggingface.co{href}"

                    query_words = [s.lower() for s in skills] if skills else []
                    if query_words and not any(w in title.lower() for w in query_words):
                        continue

                    score, badge, _ = compute_freshness(None, "")
                    job = JobListing(
                        title=title,
                        company="HuggingFace",
                        location="Remote",
                        description="",
                        apply_link=href,
                        source=self.name,
                        remote=True,
                        employment_type="full-time",
                        company_logo="https://huggingface.co/hubfs/huggingface_logo.svg",
                    )
                    job.freshness_score = score
                    job.freshness_badge = badge
                    job.work_style = "remote"
                    job.dedup_key = self._make_dedup_key(job)
                    jobs.append(job)

            logger.info(f"HuggingFace: found {len(jobs)} jobs")

        except Exception as e:
            logger.warning(f"HuggingFace scraper failed: {e}")

        return jobs
