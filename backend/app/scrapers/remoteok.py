"""
RemoteOK Scraper.
Scrapes remote job listings from RemoteOK's JSON API.
"""
import logging
from typing import List, Optional
from app.scrapers.base import (
    BaseScraper, fetch_json, parse_posted_date, compute_freshness,
    build_query, BS4_AVAILABLE,
)
from app.models.schemas import JobListing, SearchFilters

logger = logging.getLogger(__name__)


class RemoteOKScraper(BaseScraper):
    """Scrapes RemoteOK for remote job listings."""

    name = "RemoteOK"
    base_url = "https://remoteok.com/api"

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        jobs: List[JobListing] = []
        try:
            # RemoteOK provides a JSON API
            data = await fetch_json(self.base_url)
            if not data or not isinstance(data, list):
                return jobs

            # First item is metadata, skip it
            for item in data[1:]:
                if not isinstance(item, dict):
                    continue
                try:
                    title = item.get("position", "")
                    company = item.get("company", "")
                    location = item.get("location", "Remote")
                    description = item.get("description", "")
                    tags = item.get("tags", []) or []
                    date_str = item.get("date", "")
                    slug = item.get("slug", "")
                    logo = item.get("company_logo", "")

                    if not title or not company:
                        continue

                    # Filter by query (match any skill word)
                    query_words = [s.lower() for s in skills] if skills else []
                    tags_lower = [t.lower() for t in tags]
                    title_lower = title.lower()
                    desc_lower = description.lower()

                    if query_words:
                        matches = any(
                            w in title_lower or w in desc_lower or w in " ".join(tags_lower)
                            for w in query_words
                        )
                        if not matches:
                            continue

                    # Apply recency filter
                    posted_dt = parse_posted_date(date_str) if date_str else None
                    score, badge, _ = compute_freshness(posted_dt, date_str)

                    apply_url = f"https://remoteok.com/remote-jobs/{slug}" if slug else item.get("url", "")

                    job = JobListing(
                        title=title,
                        company=company,
                        location=location or "Remote",
                        description=description[:500],
                        apply_link=apply_url,
                        source=self.name,
                        salary=item.get("salary", ""),
                        remote=True,
                        employment_type="full-time",
                        skills_required=tags[:10],
                        skills_found=self._extract_skills_from_text(f"{title} {description}", tags),
                        posted_date=date_str or "",
                        company_logo=logo or "",
                        posted_timestamp=posted_dt.timestamp() if posted_dt else None,
                        freshness_score=score,
                        freshness_badge=badge,
                        work_style="remote",
                    )
                    job.dedup_key = self._make_dedup_key(job)
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"RemoteOK item parse error: {e}")
                    continue

            logger.info(f"RemoteOK: found {len(jobs)} jobs")

        except Exception as e:
            logger.warning(f"RemoteOK scraper failed: {e}")

        return jobs
