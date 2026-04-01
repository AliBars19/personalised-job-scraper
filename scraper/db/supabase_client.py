"""Supabase database client for CorkBoard."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client, create_client

from scraper.config import SupabaseConfig

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Thin wrapper around the Supabase Python client."""

    def __init__(self, config: SupabaseConfig) -> None:
        if not config.url or not config.service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
        self._client: Client = create_client(config.url, config.service_key)

    # ── Jobs ──────────────────────────────────────────────────────────

    def job_url_exists(self, source_url: str) -> bool:
        result = (
            self._client.table("jobs")
            .select("id")
            .eq("source_url", source_url)
            .limit(1)
            .execute()
        )
        return len(result.data) > 0

    def insert_job(self, job: dict[str, Any]) -> dict[str, Any]:
        result = self._client.table("jobs").insert(job).execute()
        return result.data[0] if result.data else {}

    def get_active_jobs(self, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        result = (
            self._client.table("jobs")
            .select(
                "id, source_url, application_url, source, "
                "title, company, location, salary_text, description, category"
            )
            .eq("is_active", True)
            .is_("duplicate_of", "null")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data

    def mark_job_inactive(self, job_id: str) -> None:
        self._client.table("jobs").update(
            {"is_active": False}
        ).eq("id", job_id).execute()

    def update_last_verified(self, job_id: str) -> None:
        self._client.table("jobs").update(
            {"last_verified": datetime.now(timezone.utc).isoformat()}
        ).eq("id", job_id).execute()

    def archive_old_inactive(self, days: int = 14) -> int:
        """Soft-archive jobs inactive for N+ days by keeping is_active=false."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = (
            self._client.table("jobs")
            .select("id")
            .eq("is_active", False)
            .lt("last_verified", cutoff)
            .execute()
        )
        return len(result.data)

    def get_all_active_for_dedup(self) -> list[dict[str, Any]]:
        """Fetch all active non-duplicate jobs for deduplication (single query)."""
        result = (
            self._client.table("jobs")
            .select("id, title, company, location, description, salary_text")
            .eq("is_active", True)
            .is_("duplicate_of", "null")
            .execute()
        )
        return result.data

    def mark_duplicate(self, job_id: str, canonical_id: str) -> None:
        self._client.table("jobs").update(
            {"duplicate_of": canonical_id}
        ).eq("id", job_id).execute()

    # ── Scrape Logs ───────────────────────────────────────────────────

    def create_scrape_log(self, source: str) -> str:
        result = (
            self._client.table("scrape_logs")
            .insert(
                {
                    "source": source,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "status": "running",
                }
            )
            .execute()
        )
        return result.data[0]["id"]

    def update_scrape_log(self, log_id: str, data: dict[str, Any]) -> None:
        self._client.table("scrape_logs").update(data).eq("id", log_id).execute()

    def complete_scrape_log(
        self,
        log_id: str,
        *,
        jobs_found: int = 0,
        jobs_new: int = 0,
        jobs_duplicate: int = 0,
        errors: list[str] | None = None,
        status: str = "completed",
    ) -> None:
        self.update_scrape_log(
            log_id,
            {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "jobs_found": jobs_found,
                "jobs_new": jobs_new,
                "jobs_duplicate": jobs_duplicate,
                "errors": errors or [],
                "status": status,
            },
        )

    def complete_verification_log(
        self,
        log_id: str,
        *,
        jobs_verified: int = 0,
        jobs_expired: int = 0,
        errors: list[str] | None = None,
    ) -> None:
        self.update_scrape_log(
            log_id,
            {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "jobs_verified": jobs_verified,
                "jobs_expired": jobs_expired,
                "errors": errors or [],
                "status": "completed",
            },
        )
