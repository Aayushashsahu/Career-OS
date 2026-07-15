"""
Base scraper class for all job platforms.
All scrapers inherit from this and implement search().
Includes freshness scoring, date parsing, and recency-aware fetching.
"""
import asyncio
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from app.models.schemas import JobListing, SearchFilters

try:
    import httpx
    HTTP_CLIENT = "httpx"
except ImportError:
    HTTP_CLIENT = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


_MAX_CONCURRENT = int(os.getenv("CAREEROS_MAX_CONCURRENT", "10"))  # concurrent scrapers

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Rate limiting state
_last_request_times: Dict[str, float] = {}
_MIN_REQUEST_INTERVAL = 0.5  # 500ms between requests to same domain


async def fetch_url(url: str, headers: dict = None, timeout: float = 15.0) -> str:
    """Fetch a URL using httpx with rate limiting and retries."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc

    # Rate limiting
    now = time.time()
    last = _last_request_times.get(domain, 0)
    wait = _MIN_REQUEST_INTERVAL - (now - last)
    if wait > 0:
        await asyncio.sleep(wait)

    h = {**DEFAULT_HEADERS, **(headers or {})}

    if HTTP_CLIENT == "httpx":
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                    resp = await client.get(url, headers=h)
                    _last_request_times[domain] = time.time()
                    if resp.status_code == 200:
                        return resp.text
                    elif resp.status_code == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        return resp.text
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(1)
                continue
        return ""
    else:
        return ""


async def fetch_json(url: str, headers: dict = None, timeout: float = 15.0) -> Optional[dict]:
    """Fetch a URL and parse as JSON."""
    h = {"Accept": "application/json", **(headers or {})}
    text = await fetch_url(url, headers=h, timeout=timeout)
    if not text:
        return None
    try:
        import json
        return json.loads(text)
    except Exception:
        return None


# ─────────────────── Freshness System ───────────────────

def parse_posted_date(date_str: str) -> Optional[datetime]:
    """
    Parse various date formats from job postings.
    Returns a datetime object or None if unparseable.
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    now = datetime.utcnow()

    # Handle relative dates
    lower = date_str.lower()

    # "X minutes/hours/days/weeks/months ago"
    m = re.search(r'(\d+)\s*(minute|min|hour|hr|day|d|week|wk|month|mon|year|yr)s?\s*ago', lower)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if unit.startswith('min'):
            return now - timedelta(minutes=num)
        elif unit.startswith('hour') or unit.startswith('hr'):
            return now - timedelta(hours=num)
        elif unit.startswith('day') or unit == 'd':
            return now - timedelta(days=num)
        elif unit.startswith('week') or unit.startswith('wk'):
            return now - timedelta(weeks=num)
        elif unit.startswith('month') or unit.startswith('mon'):
            return now - timedelta(days=num * 30)
        elif unit.startswith('year') or unit.startswith('yr'):
            return now - timedelta(days=num * 365)

    # "just now", "just posted", "new"
    if any(k in lower for k in ['just now', 'just posted', 'new', 'fresh', 'latest']):
        return now

    # "today"
    if 'today' in lower:
        return now

    # "yesterday"
    if 'yesterday' in lower:
        return now - timedelta(days=1)

    # "Xh ago", "Xd ago" (compact format)
    m = re.search(r'(\d+)(h|d|w|m)\b', lower)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if unit == 'h':
            return now - timedelta(hours=num)
        elif unit == 'd':
            return now - timedelta(days=num)
        elif unit == 'w':
            return now - timedelta(weeks=num)
        elif unit == 'm':
            return now - timedelta(days=num * 30)

    # Try ISO format
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Strip timezone info to avoid naive/aware datetime conflicts
        return dt.replace(tzinfo=None)
    except Exception:
        pass

    # Try common formats
    for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%B %d, %Y', '%b %d, %Y',
                '%d %B %Y', '%d %b %Y', '%m/%d/%Y', '%d/%m/%Y']:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def compute_freshness(posted_date: Optional[datetime] = None, date_str: str = "") -> Tuple[float, str, str]:
    """
    Compute freshness score (0-100), badge text, and badge color.
    Returns (freshness_score, badge_text, badge_color).
    """
    now = datetime.utcnow()

    if posted_date is None and date_str:
        posted_date = parse_posted_date(date_str)

    if posted_date is None:
        # Unknown date - assume it might be somewhat fresh
        return 50.0, "", ""

    # Safety: strip any timezone info to avoid naive/aware conflicts
    if posted_date.tzinfo is not None:
        posted_date = posted_date.replace(tzinfo=None)

    delta = now - posted_date
    hours = delta.total_seconds() / 3600
    days = delta.days

    if hours < 1:
        return 100.0, "Just posted", "green"
    elif hours < 24:
        return 95.0, f"{int(hours)}h ago", "green"
    elif days == 1:
        return 90.0, "Yesterday", "green"
    elif days <= 3:
        score = 85.0 - (days * 5)
        return score, f"{days} days ago", "yellow"
    elif days <= 7:
        score = 70.0 - ((days - 3) * 5)
        return score, f"{days} days ago", "yellow"
    elif days <= 14:
        score = 50.0 - ((days - 7) * 5)
        return score, f"{days} days ago", "orange"
    elif days <= 30:
        score = 20.0 - ((days - 14) * 1.0)
        return max(score, 5.0), f"{days} days ago", "gray"
    else:
        return 2.0, f"{days}d ago", "gray"


# ─────────────────── Recency Params for Platforms ───────────────────

RECENCY_PARAMS = {
    # LinkedIn: f_TPR = time posted range in seconds
    "linkedin": {
        "today": "r86400",      # 24h
        "24h": "r86400",
        "3days": "r259200",     # 3 days
        "week": "r604800",      # 7 days
        "month": "r2592000",    # 30 days
        "all": "",
    },
    # Indeed: fromage = days ago
    "indeed": {
        "today": "1",
        "24h": "1",
        "3days": "3",
        "week": "7",
        "month": "14",
        "all": "",
    },
    # Internshala: doesn't have explicit recency param, sort by newest
    "internshala": {
        "today": "&sort=newest",
        "24h": "&sort=newest",
        "3days": "&sort=newest",
        "week": "&sort=newest",
        "month": "&sort=newest",
        "all": "",
    },
    # Wellfound: sort by most recent
    "wellfound": {
        "today": "&sort=most_recent",
        "24h": "&sort=most_recent",
        "3days": "&sort=most_recent",
        "week": "&sort=most_recent",
        "month": "&sort=most_recent",
        "all": "",
    },
}


def get_recency_params(platform: str, recency: str) -> str:
    """Get recency filter parameters for a platform."""
    platform_lower = platform.lower()
    params = RECENCY_PARAMS.get(platform_lower, {})
    return params.get(recency, params.get("week", ""))


# ─────────────────── Base Scraper ───────────────────

def build_query(skills: List[str], filters: Optional[SearchFilters] = None, max_skills: int = 3) -> str:
    """Build a search query from skills and filters.
    Uses role-based approach: infers target roles from skills
    and generates role-focused queries instead of raw skill lists."""
    # Try to infer roles from skills
    from app.services.query_generator import infer_target_roles, get_seniority_level
    
    class FakeResume:
        def __init__(self, skills):
            self.skills = skills
    
    resume = FakeResume(skills)
    roles = infer_target_roles(resume)
    seniority = get_seniority_level(filters)
    
    if roles:
        # Use the best role as the query
        role = roles[0]
        if seniority == "internship":
            return f"{role} Intern"
        elif seniority == "entry":
            return f"Junior {role}"
        return role
    
    # Fallback: use first skill
    if skills:
        return f"{skills[0]} Engineer"
    return "Software Engineer"


def build_location(filters: Optional[SearchFilters] = None, default: str = "India") -> str:
    """Build location string from filters."""
    if not filters:
        return default
    parts = []
    if filters.city:
        parts.append(filters.city)
    if filters.country:
        parts.append(filters.country)
    return ", ".join(parts) if parts else default


class BaseScraper:
    """Base class for all job scrapers."""

    name: str = "Unknown"
    base_url: str = ""

    async def search(self, skills: List[str], filters: Optional[SearchFilters] = None) -> List[JobListing]:
        """Search for jobs. Override in subclasses."""
        raise NotImplementedError

    def _apply_freshness(self, jobs: List[JobListing]) -> List[JobListing]:
        """Apply freshness scores to all jobs. Sorting is done by the registry."""
        for job in jobs:
            posted = parse_posted_date(job.posted_date) if job.posted_date else None
            score, badge, _ = compute_freshness(posted, job.posted_date)
            job.freshness_score = score
            job.freshness_badge = badge
            if posted:
                job.posted_timestamp = posted.timestamp()

            # Set dedup key
            job.dedup_key = self._make_dedup_key(job)

        return jobs

    def _make_dedup_key(self, job: JobListing) -> str:
        """Create a normalized dedup key for a job."""
        title = re.sub(r'\s+', ' ', job.title.lower().strip())
        company = re.sub(r'\s+', ' ', job.company.lower().strip())
        # Remove common suffixes that don't affect identity
        for suffix in [' - ', ' | ', ' at ', ' @ ']:
            title = title.replace(suffix, ' ')
            company = company.replace(suffix, ' ')
        return f"{title}|{company}"

    def _detect_work_style(self, text: str) -> str:
        """Detect remote/hybrid/on-site from text."""
        t = text.lower()
        if any(k in t for k in ["remote", "work from home", "wfh", "anywhere", "distributed", "work remotely"]):
            return "remote"
        elif any(k in t for k in ["hybrid", "flexible", "flex", "mix"]):
            return "hybrid"
        return "on-site"

    def _is_remote(self, text: str) -> bool:
        """Check if the job mentions remote work."""
        return self._detect_work_style(text) == "remote"

    def _parse_salary(self, text: str) -> Optional[str]:
        """Extract salary info from text."""
        patterns = [
            r'[\$₹€£]\s*[\d,.]+\s*[-–to]+\s*[\$₹€£]?\s*[\d,.]+',
            r'[\d,.]+\s*[-–to]+\s*[\d,.]+\s*(?:per|/)\s*(?:month|year|annum|hour)',
            r'[\$₹€£]\s*[\d,.]+',
            r'\d+[kK]\s*[-–to]+\s*\d+[kK]',
            r'\d+[,.]?\d*\s*(?:LPA|lpa|Lakhs|lakhs|per annum|p\.a\.)',
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(0).strip()
        return None

    def _extract_skills_from_text(self, text: str, known_skills: List[str] = None) -> List[str]:
        """Extract mentioned skills from job description."""
        if not known_skills:
            known_skills = [
                "python", "javascript", "typescript", "java", "c++", "react", "angular",
                "vue", "node.js", "express", "django", "flask", "fastapi", "sql", "mongodb",
                "postgresql", "mysql", "aws", "azure", "gcp", "docker", "kubernetes", "git",
                "html", "css", "tailwind", "machine learning", "deep learning", "tensorflow",
                "pytorch", "nlp", "data science", "rust", "go", "ruby", "php", "laravel",
                "spring", "dotnet", "c#", "linux", "bash", "terraform", "ansible",
                "react native", "flutter", "swift", "kotlin", "solidity", "blockchain",
                "figma", "photoshop", "excel", "powerpoint", "jenkins", "ci/cd",
                "graphql", "rest api", "grpc", "kafka", "redis", "elasticsearch",
                "spark", "hadoop", "airflow", "dbt", "snowflake", "tableau", "power bi",
                "scala", "r", "matlab", "sas", "penetration testing", "cybersecurity",
                "ux design", "user research", "wireframing", "prototyping",
            ]
        t = text.lower()
        found = []
        for s in known_skills:
            if s.lower() in t:
                found.append(s.title() if len(s) > 3 else s.upper())
        return list(set(found))

    def _classify_employment_type(self, text: str) -> str:
        """Classify job type from text."""
        t = text.lower()
        if any(k in t for k in ["intern", "internship", "trainee"]):
            return "internship"
        elif any(k in t for k in ["contract", "freelance", "consultant"]):
            return "contract"
        elif any(k in t for k in ["part-time", "part time"]):
            return "part-time"
        return "full-time"
