"""
SSE (Server-Sent Events) streaming for live search progress.
Provides real-time updates as each platform is scraped.
"""
import asyncio
import json
import time
from typing import List, Optional, AsyncGenerator
from app.models.schemas import SearchFilters
from app.scrapers.registry import SCRAPERS, _advanced_dedup, _filter_and_sort_by_recency, _SCRAPER_TIMEOUT


def _sse_event(event: str, data: dict) -> str:
    """Format an SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_search_progress(
    skills: List[str],
    filters: Optional[SearchFilters] = None,
    platforms: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    SSE generator that yields real-time progress events as each platform is scraped.
    """
    targets = platforms or list(SCRAPERS.keys())
    scrapers = [(name, SCRAPERS[name]) for name in targets if name in SCRAPERS]
    total = len(scrapers)

    yield _sse_event("search_started", {
        "total_platforms": total,
        "platforms": [name for name, _ in scrapers],
        "timestamp": time.time(),
    })

    all_jobs = []
    status_map = {}
    completed = 0
    errors = 0

    # Run all scrapers concurrently using gather
    async def _run_one(name: str, scraper):
        try:
            jobs = await asyncio.wait_for(scraper.search(skills, filters), timeout=_SCRAPER_TIMEOUT)
            # Filter out fallback jobs
            real_jobs = [j for j in jobs if j.company != name and j.company != j.source] if jobs else []
            return name, real_jobs if real_jobs else jobs, "ok"
        except asyncio.TimeoutError:
            return name, [], "timeout"
        except Exception as e:
            return name, [], f"error: {str(e)[:200]}"

    # Yield platform_started for all platforms
    for i, (name, _) in enumerate(scrapers):
        yield _sse_event("platform_started", {
            "platform": name,
            "completed": i,
            "total": total,
            "timestamp": time.time(),
        })

    # Run all scrapers concurrently
    tasks = [_run_one(name, scraper) for name, scraper in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            completed += 1
            errors += 1
            continue

        name, jobs, status = result
        completed += 1

        if status == "ok" and jobs:
            all_jobs.extend(jobs)
            status_map[name] = "ok"
            yield _sse_event("platform_completed", {
                "platform": name,
                "jobs_found": len(jobs),
                "completed": completed,
                "total": total,
                "timestamp": time.time(),
            })
        else:
            status_map[name] = status
            errors += 1
            yield _sse_event("platform_error", {
                "platform": name,
                "error": status,
                "completed": completed,
                "total": total,
                "timestamp": time.time(),
            })

        # Yield partial results every 3 platforms
        if completed % 3 == 0 and all_jobs:
            deduped = _advanced_dedup(all_jobs)
            yield _sse_event("partial_results", {
                "total_so_far": len(deduped),
                "platforms_completed": completed,
                "total_platforms": total,
            })

    # Final dedup and sort
    deduped = _advanced_dedup(all_jobs)
    recency = filters.recency if filters else "week"
    deduped = _filter_and_sort_by_recency(deduped, recency, filters)

    sources_searched = [name for name, st in status_map.items() if st == "ok"]

    yield _sse_event("search_completed", {
        "total_found": len(deduped),
        "sources_searched": sources_searched,
        "platform_status": status_map,
        "errors": errors,
        "timestamp": time.time(),
    })
