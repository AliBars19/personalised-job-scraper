"""Verify that job listing URLs are still active."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from scraper.config import USER_AGENTS, VERIFICATION_DELAY
from scraper.db.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# Per-source expired text patterns
EXPIRED_PATTERNS: dict[str, list[str]] = {
    "indeed": ["this job has expired", "the job you are looking for is no longer available"],
    "reed": ["this job is no longer being advertised", "no longer available"],
    "caterer": [],  # Caterer redirects to search when listing removed
    "totaljobs": ["sorry, this job is no longer available"],
    "linkedin": ["no longer accepting applications"],
}

GENERIC_EXPIRED_PATTERNS: list[str] = [
    "job expired",
    "no longer available",
    "position filled",
    "position has been filled",
    "this vacancy has been closed",
    "this role has been filled",
]

MAX_RETRIES = 3


async def _check_url(
    url: str,
    source: str,
    client: httpx.AsyncClient,
) -> bool:
    """Return True if the URL appears to still be an active listing."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.head(url, follow_redirects=True, timeout=15.0)

            if resp.status_code in (404, 410):
                return False

            if resp.status_code in (403, 429):
                # Rate limited — don't mark inactive, just skip
                return True

            if resp.status_code == 301:
                final = str(resp.headers.get("location", ""))
                # Redirect to homepage or search = listing removed
                if final.rstrip("/") == urlparse_base(url) or "/search" in final:
                    return False

            if resp.status_code == 200:
                # For caterer.com, check redirect chain for search page
                if source == "caterer" and "/search" in str(resp.url):
                    return False

                # Need to GET the body to check for expired text
                get_resp = await client.get(url, follow_redirects=True, timeout=15.0)
                body = get_resp.text.lower()

                source_patterns = EXPIRED_PATTERNS.get(source, [])
                all_patterns = source_patterns + GENERIC_EXPIRED_PATTERNS

                for pattern in all_patterns:
                    if pattern in body:
                        return False

                return True

            return True  # Other status codes — don't mark inactive

        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == MAX_RETRIES - 1:
                return False
            await asyncio.sleep(2 ** attempt)

    return False


def urlparse_base(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def verify_all_links(db: SupabaseClient) -> dict[str, int]:
    """Verify all active job links. Returns stats dict."""
    log_id = db.create_scrape_log("link_verification")
    verified = 0
    expired = 0
    errors: list[str] = []

    headers = {
        "User-Agent": USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        offset = 0
        batch_size = 500

        while True:
            jobs = db.get_active_jobs(limit=batch_size, offset=offset)
            if not jobs:
                break

            for job in jobs:
                try:
                    is_active = await _check_url(
                        job["source_url"], job["source"], client
                    )

                    if is_active and job.get("application_url"):
                        is_active = await _check_url(
                            job["application_url"], job["source"], client
                        )

                    if is_active:
                        db.update_last_verified(job["id"])
                        verified += 1
                    else:
                        db.mark_job_inactive(job["id"])
                        expired += 1

                except Exception as exc:
                    msg = f"Verify error job={job['id']}: {exc}"
                    logger.error(msg)
                    errors.append(msg)

                await asyncio.sleep(VERIFICATION_DELAY)

            offset += batch_size

    db.complete_verification_log(
        log_id,
        jobs_verified=verified,
        jobs_expired=expired,
        errors=errors,
    )

    stats = {"verified": verified, "expired": expired, "errors": len(errors)}
    logger.info("Verification complete: %s", stats)
    return stats
