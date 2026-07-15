"""
WeWorkRemotely Scraper.
Scrapes remote job listings from WeWorkRemotely.
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


class WeWorkRemotelyScraper(BaseScraper):
    """Scrapes WeWorkRemotely for remote job listings."""

    name = "WeWorkRemotely"
    base_url = "https://weworkremotely.com/remote-jobs"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        jobs: List[JobListing] = []
        try:
            # WeWorkRemotely doesn't have a search/recency API - just fetch the main page
            text = await fetch_url(self.base_url)
            if not text:
                return jobs

            if BS4_AVAILABLE:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(text, "html.parser")

                # WeWorkRemotely uses section.job-list > li for job listings
                sections = soup.select("section.job-list li, section.features li")
                for item in sections:
                    try:
                        title_el = item.select_one("h2, h3, .company_and_title a")
                        company_el = item.select_one("span.company-name, .company")
                        link_el = item.select_one("a[href]")

                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        company = company_el.get_text(strip=True) if company_el else ""
                        apply_url = link_el.get("href", "") if link_el else ""
                        if apply_url and not apply_url.startswith("http"):
                            apply_url = f"https://weworkremotely.com{apply_url}"

                        if not title:
                            continue

                        # Check skill match
                        query_words = [s.lower() for s in skills] if skills else []
                        text_to_check = f"{title} {company}".lower()
                        if query_words and not any(w in text_to_check for w in query_words):
                            continue

                        job = JobListing(
                            title=title,
                            company=company,
                            location="Remote",
                            description=f"Remote position at {company}",
                            apply_link=apply_url,
                            source=self.name,
                            remote=True,
                            employment_type="full-time",
                            skills_found=self._extract_skills_from_text(text_to_check),
                        )

                        score, badge, _ = compute_freshness(None, "")
                        job.freshness_score = score
                        job.freshness_badge = badge
                        job.work_style = "remote"
                        job.dedup_key = self._make_dedup_key(job)
                        jobs.append(job)
                    except Exception as e:
                        logger.debug(f"WeWorkRemotely item error: {e}")
                        continue

            logger.info(f"WeWorkRemotely: found {len(jobs)} jobs")

        except Exception as e:
            logger.warning(f"WeWorkRemotely scraper failed: {e}")

        return jobs
