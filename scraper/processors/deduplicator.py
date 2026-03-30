"""Fuzzy deduplication of jobs across sources."""

from __future__ import annotations

import logging
import re
from typing import Any

from rapidfuzz import fuzz

from scraper.db.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

_STRIP_SUFFIXES = re.compile(
    r"\b(ltd|limited|inc|plc|llp|group|holdings)\b",
    re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9\s]")

TITLE_THRESHOLD = 85
COMPANY_THRESHOLD = 80


def _normalise(text: str) -> str:
    text = _STRIP_SUFFIXES.sub("", text.lower())
    text = _NON_ALNUM.sub("", text)
    return " ".join(text.split())


def _pick_canonical(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str]:
    """Return (canonical_id, duplicate_id). Prefer the record with more info."""
    score_a = len(a.get("description") or "") + (1000 if a.get("salary_text") else 0)
    score_b = len(b.get("description") or "") + (1000 if b.get("salary_text") else 0)
    if score_a >= score_b:
        return a["id"], b["id"]
    return b["id"], a["id"]


def deduplicate_job(
    job_row: dict[str, Any],
    existing_jobs: list[dict[str, Any]],
    db: SupabaseClient,
) -> bool:
    """Check if *job_row* is a duplicate of any existing job.

    If a match is found, marks the lesser record as a duplicate and returns True.
    """
    norm_title = _normalise(job_row.get("title", ""))
    norm_company = _normalise(job_row.get("company", ""))
    norm_location = _normalise(job_row.get("location", ""))

    for existing in existing_jobs:
        if existing["id"] == job_row.get("id"):
            continue

        ex_title = _normalise(existing.get("title", ""))
        ex_company = _normalise(existing.get("company", ""))
        ex_location = _normalise(existing.get("location", ""))

        title_score = fuzz.ratio(norm_title, ex_title)
        company_score = fuzz.ratio(norm_company, ex_company)
        location_match = (
            "london" in norm_location and "london" in ex_location
        ) or fuzz.ratio(norm_location, ex_location) > 80

        if (
            title_score >= TITLE_THRESHOLD
            and company_score >= COMPANY_THRESHOLD
            and location_match
        ):
            canonical_id, dup_id = _pick_canonical(existing, job_row)
            db.mark_duplicate(dup_id, canonical_id)
            logger.info(
                "Duplicate detected: %s is duplicate of %s (title=%d%%, company=%d%%)",
                dup_id,
                canonical_id,
                title_score,
                company_score,
            )
            return True

    return False
