"""
Scraper registry - manages all platform scrapers with advanced dedup, caching,
error tracking, and freshness-based filtering.
"""
import asyncio
import hashlib
import logging
import os
import re
import time
from typing import List, Optional, Dict, Tuple, Any
from app.scrapers.base import BaseScraper
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.google_jobs import GoogleJobsScraper
from app.scrapers.internshala import InternshalaScraper
from app.scrapers.indeed import IndeedScraper
from app.scrapers.unstop import UnstopScraper
from app.scrapers.wellfound import WellfoundScraper
from app.scrapers.yc_jobs import YCJobsScraper
from app.scrapers.greenhouse import GreenhouseScraper
from app.scrapers.smartrecruiters import SmartRecruitersScraper
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.weremote import WeWorkRemotelyScraper
from app.scrapers.huggingface import HuggingFaceScraper
from app.models.schemas import JobListing, SearchFilters


# Registry of all available scrapers
# NOTE: Lever, Ashby, BambooHR disabled — APIs deprecated/empty or companies unverified
SCRAPERS: Dict[str, BaseScraper] = {
    "LinkedIn": LinkedInScraper(),
    "Google Jobs": GoogleJobsScraper(),
    "Internshala": InternshalaScraper(),
    "Indeed": IndeedScraper(),
    "Unstop": UnstopScraper(),
    "Wellfound": WellfoundScraper(),
    "YC Jobs": YCJobsScraper(),
    "Greenhouse": GreenhouseScraper(),
    # "Lever": LeverScraper(),       # Disabled: API deprecated, HTML is JS-rendered
    # "Ashby": AshbyScraper(),        # Disabled: API returns empty jobs for all companies
    "SmartRecruiters": SmartRecruitersScraper(),
    # "BambooHR": BambooHRScraper(),  # Disabled: unverified company list
    "RemoteOK": RemoteOKScraper(),
    "WeWorkRemotely": WeWorkRemotelyScraper(),
    "HuggingFace": HuggingFaceScraper(),
}

# ─────────────────── Configuration (from env vars) ───────────────────

_CACHE_TTL = int(os.getenv("CAREEROS_CACHE_TTL", "600"))  # seconds
# Global default timeout (overridden per-scraper below)
_SCRAPER_TIMEOUT = float(os.getenv("CAREEROS_SCRAPER_TIMEOUT", "30"))  # seconds

# Per-scraper timeouts: scrapers that do pagination or many concurrent requests get more time
_SCRAPER_TIMEOUTS: Dict[str, float] = {
    "LinkedIn": 45.0,      # 3 pages of HTML scraping
    "Indeed": 40.0,        # 3 pages × 2 domains
    "Greenhouse": 50.0,    # 50+ company boards concurrently
    "SmartRecruiters": 40.0,  # 50+ company boards
    "Google Jobs": 25.0,   # Single search
    "Internshala": 25.0,   # Single search
    "Unstop": 25.0,        # Single search
    "Wellfound": 25.0,     # Single search
    "YC Jobs": 25.0,       # Single search
    "RemoteOK": 20.0,      # Single API call
    "WeWorkRemotely": 20.0, # Single page
    "HuggingFace": 20.0,   # Single API call
}
_MAX_AGE_DAYS = int(os.getenv("CAREEROS_MAX_AGE_DAYS", "14"))  # days
logger = logging.getLogger(__name__)

# Source priority for dedup merge (lower = higher priority)
_SOURCE_PRIORITY = {
    "company_career_page": 1,
    "Greenhouse": 2, "Lever": 2, "Ashby": 2,  # Official ATS
    "SmartRecruiters": 2, "BambooHR": 2,
    "LinkedIn": 3,
    "Wellfound": 4, "YC Jobs": 4, "Internshala": 4, "Unstop": 4,
    "Indeed": 5,
    "Google Jobs": 6,
    "RemoteOK": 4, "WeWorkRemotely": 4, "HuggingFace": 3,
}

# ─────────────────── Simple In-Memory Cache ───────────────────

_cache: Dict[str, Tuple[float, List[JobListing], List[str]]] = {}


def _cache_key(skills: List[str], filters: Optional[SearchFilters]) -> str:
    """Generate a deterministic cache key."""
    filter_str = ""
    if filters:
        filter_dict = filters.model_dump()
        filter_str = str(sorted(filter_dict.items()))
    raw = f"{'|'.join(sorted(s.lower() for s in skills))}|{filter_str}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached(key: str) -> Optional[Tuple[List[JobListing], List[str]]]:
    """Get cached results if still valid."""
    if key in _cache:
        ts, jobs, sources = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return jobs, sources
        else:
            del _cache[key]
    return None


def _set_cache(key: str, jobs: List[JobListing], sources: List[str]):
    """Store results in cache."""
    _cache[key] = (time.time(), jobs, sources)
    # Evict old entries if cache is too large
    if len(_cache) > 50:
        oldest_key = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest_key]


def clear_cache():
    """Clear all cached search results."""
    _cache.clear()


# ─────────────────── Platform Status Tracking ───────────────────

platform_status: Dict[str, str] = {}  # platform -> "ok" | "error" | "timeout"


def get_scraper(name: str) -> Optional[BaseScraper]:
    """Get a scraper by name."""
    return SCRAPERS.get(name)


def list_scrapers() -> List[str]:
    """List all available scraper names."""
    return list(SCRAPERS.keys())


async def search_all_platforms(
    skills: List[str],
    filters: Optional[SearchFilters] = None,
    platforms: Optional[List[str]] = None,
) -> Tuple[List[JobListing], List[str], Dict[str, str]]:
    """
    Search all (or selected) platforms concurrently.
    Returns (all_jobs, sources_searched, platform_status_map).

    Features:
    - Concurrent execution with per-platform timeout
    - Error tracking per platform
    - In-memory caching (10min TTL)
    - Advanced deduplication with freshness priority
    - Recency-based default sorting
    """
    # Check cache first
    cache_key = _cache_key(skills, filters)
    cached = _get_cached(cache_key)
    if cached:
        return cached[0], cached[1], {s: "ok" for s in cached[1]}

    targets = platforms or list(SCRAPERS.keys())
    scrapers = [(name, SCRAPERS[name]) for name in targets if name in SCRAPERS]

    # Track per-platform status
    status: Dict[str, str] = {}

    async def _run_with_timeout(name: str, scraper: BaseScraper):
        """Run a scraper with timeout and error tracking."""
        try:
            timeout = _SCRAPER_TIMEOUTS.get(name, _SCRAPER_TIMEOUT)
            jobs = await asyncio.wait_for(scraper.search(skills, filters), timeout=timeout)
            status[name] = "ok"
            platform_status[name] = "ok"
            return name, jobs
        except asyncio.TimeoutError:
            status[name] = "timeout"
            platform_status[name] = "timeout"
            logger.warning(f"{name} scraper timed out after {_SCRAPER_TIMEOUTS.get(name, _SCRAPER_TIMEOUT)}s")
            return name, []
        except Exception as e:
            status[name] = "error"
            platform_status[name] = "error"
            logger.warning(f"{name} scraper failed: {e}")
            return name, []

    # Run all scrapers concurrently
    tasks = [_run_with_timeout(name, scraper) for name, scraper in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs: List[JobListing] = []
    sources_searched: List[str] = []

    for result in results:
        if isinstance(result, tuple):
            name, jobs = result
            if jobs:
                # Validate: filter out jobs with invalid/missing apply URLs
                valid_jobs = [j for j in jobs if _is_valid_job(j)]
                if valid_jobs:
                    all_jobs.extend(valid_jobs)
                    sources_searched.append(name)

    # Advanced deduplication
    deduped = _advanced_dedup(all_jobs)

    # Sort by freshness (newest first), then by match
    recency = filters.recency if filters else "week"
    deduped = _filter_and_sort_by_recency(deduped, recency, filters)

    # Cache results
    _set_cache(cache_key, deduped, sources_searched)

    return deduped, sources_searched, status


def _advanced_dedup(jobs: List[JobListing]) -> List[JobListing]:
    """
    Advanced deduplication:
    - Normalizes title + company for matching
    - When duplicates exist, keeps the one with:
      1. More recent posting date
      2. More apply URLs (more sources)
      3. Better data (has description, skills, etc.)
    """
    seen: Dict[str, JobListing] = {}

    for job in jobs:
        key = job.dedup_key or _normalize_key(job.title, job.company)

        if key not in seen:
            seen[key] = job
        else:
            existing = seen[key]
            # Merge: prefer newer, richer data
            merged = _merge_jobs(existing, job)
            seen[key] = merged

    return list(seen.values())


def _is_valid_job(job: JobListing) -> bool:
    """
    Validate a job listing. Discard clearly invalid jobs:
    - Title is empty
    - Apply URL is missing or not http(s)
    - Apply URL is a Google search redirect
    - Apply URL is a placeholder (javascript:, mailto:, anchor-only)
    """
    url = (job.apply_link or "").strip()
    title = (job.title or "").strip()

    # Must have a title
    if not title:
        return False

    # Must have a real apply URL
    if not url or not url.startswith("http"):
        return False

    url_lower = url.lower()

    # Never allow Google search redirects
    if "google.com/search" in url_lower or "google.com/url" in url_lower:
        return False

    # Reject obviously broken URL patterns
    # "#section" alone is invalid, but "https://example.com/jobs#123" is valid
    if url_lower.startswith("javascript:") or url_lower.startswith("mailto:") or url_lower.startswith("tel:"):
        return False
    if "void(0)" in url_lower:
        return False
    if url_lower.startswith("#") and "://" not in url_lower:
        return False
    if "click to view" in url_lower or "click here" in url_lower:
        return False

    return True


def _normalize_key(title: str, company: str) -> str:
    """Create a normalized dedup key from title and company."""
    title_norm = re.sub(r'\s+', ' ', title.lower().strip())
    company_norm = re.sub(r'\s+', ' ', company.lower().strip())
    # Remove common noise words
    for word in ['remote', 'hybrid', 'onsite', 'on-site', 'full-time', 'part-time', 'internship', 'intern']:
        title_norm = title_norm.replace(word, '').strip()
    return f"{title_norm}|{company_norm}"


def _merge_jobs(existing: JobListing, new: JobListing) -> JobListing:
    """
    Merge two duplicate jobs, keeping the best data from each.
    Priority: 1) Newer posting, 2) Direct company career page,
    3) Official ATS (Greenhouse/Lever/Ashby), 4) LinkedIn, 5) Indeed.
    """
    # Merge apply URLs and sources
    apply_urls = {**existing.apply_urls, **new.apply_urls}
    if existing.source not in apply_urls:
        apply_urls[existing.source] = existing.apply_link
    if new.source not in apply_urls:
        apply_urls[new.source] = new.apply_link
    sources = list(set(existing.sources + [existing.source] + [new.source]))

    # Prefer newer posted_date
    posted_date = existing.posted_date
    posted_timestamp = existing.posted_timestamp
    freshness_score = existing.freshness_score
    freshness_badge = existing.freshness_badge

    if new.posted_timestamp and (not posted_timestamp or new.posted_timestamp > posted_timestamp):
        posted_date = new.posted_date
        posted_timestamp = new.posted_timestamp
        freshness_score = new.freshness_score
        freshness_badge = new.freshness_badge

    # Pick primary source by priority (lower = better)
    existing_prio = _SOURCE_PRIORITY.get(existing.source, 10)
    new_prio = _SOURCE_PRIORITY.get(new.source, 10)
    # Also prefer newer posting date as tiebreaker
    if new.posted_timestamp and posted_timestamp and new.posted_timestamp > posted_timestamp:
        primary_source = new.source
    elif new_prio < existing_prio:
        primary_source = new.source
    else:
        primary_source = existing.source

    # Prefer richer description
    description = existing.description if len(existing.description) > len(new.description) else new.description

    return JobListing(
        id=existing.id,
        title=existing.title if existing.title else new.title,
        company=existing.company if existing.company else new.company,
        location=existing.location if existing.location != "Remote" else new.location,
        description=description,
        apply_link=existing.apply_link if existing.apply_link else new.apply_link,
        source=primary_source,
        stipend=existing.stipend or new.stipend,
        salary=existing.salary or new.salary,
        remote=existing.remote or new.remote,
        employment_type=existing.employment_type if existing.employment_type != "full-time" else new.employment_type,
        experience_required=existing.experience_required or new.experience_required,
        skills_required=existing.skills_required or new.skills_required,
        skills_found=list(set(existing.skills_found + new.skills_found)),
        skills_missing=existing.skills_missing or new.skills_missing,
        posted_date=posted_date,
        company_logo=existing.company_logo or new.company_logo,
        posted_timestamp=posted_timestamp,
        freshness_score=freshness_score,
        freshness_badge=freshness_badge,
        dedup_key=existing.dedup_key or new.dedup_key,
        work_style=existing.work_style if existing.work_style != "on-site" else new.work_style,
        company_url=existing.company_url or new.company_url,
        sources=sources,
        apply_urls=apply_urls,
    )


def _filter_and_sort_by_recency(
    jobs: List[JobListing],
    recency: str,
    filters: Optional[SearchFilters] = None,
) -> List[JobListing]:
    """
    Filter jobs by recency and sort newest-first.
    Unless include_old is True, exclude jobs older than MAX_AGE_DAYS.
    If recency=month or all, automatically enable include_old.
    """
    now = time.time()

    # Recency thresholds (seconds)
    thresholds = {
        "today": 86400,
        "24h": 86400,
        "3days": 86400 * 3,
        "week": 86400 * 7,
        "month": 86400 * 30,
        "all": float('inf'),
    }
    max_age = thresholds.get(recency, thresholds["week"])

    # Auto-enable include_old for month/all recency
    include_old = (filters.include_old if filters else False) or recency in ("month", "all")
    max_age_absolute = _MAX_AGE_DAYS * 86400 if not include_old else float('inf')

    filtered = []
    for job in jobs:
        if job.posted_timestamp:
            age = now - job.posted_timestamp
            if age > max_age_absolute:
                continue
        filtered.append(job)

    # Sort by freshness score (descending = newest first)
    filtered.sort(key=lambda j: j.freshness_score, reverse=True)

    return filtered
