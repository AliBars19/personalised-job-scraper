"""Abstract base class for all job board scrapers."""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from scraper.config import (
    MAX_PAGES_PER_QUERY,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
    REQUEST_HEADERS,
    SEARCH_QUERIES,
    USER_AGENTS,
    ScraperApiConfig,
)
from scraper.db.supabase_client import SupabaseClient
from scraper.processors.location_filter import is_london_based
from scraper.processors.relevance_filter import is_relevant_job
from scraper.processors.salary_parser import parse_salary

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapedJob:
    source: str
    source_url: str
    title: str
    company: str
    location: str
    salary_text: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    description: str = ""
    posted_date: str | None = None
    category: str = "hospitality"
    application_url: str | None = None
    application_type: str = "unknown"

    @property
    def application_domain(self) -> str | None:
        url = self.application_url or self.source_url
        try:
            return urlparse(url).netloc
        except Exception:
            return None

    def to_db_row(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_url": _safe_http_url(self.source_url),
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary_text": self.salary_text,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "description": (self.description or "")[:10_000],
            "posted_date": self.posted_date,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "category": self.category,
            "application_url": _safe_http_url(self.application_url),
            "application_type": self.application_type,
            "application_domain": self.application_domain,
            "is_active": True,
            "last_verified": datetime.now(timezone.utc).isoformat(),
        }


def _safe_http_url(url: str | None) -> str | None:
    """Only allow http/https URLs to be stored."""
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    return None


@dataclass
class ScrapeResult:
    jobs_found: int = 0
    jobs_new: int = 0
    jobs_duplicate: int = 0
    errors: list[str] = field(default_factory=list)


class BaseScraper(ABC):
    """Every source scraper inherits from this."""

    source_name: str = ""
    use_proxy: bool = False  # Override to True for sources blocked from DO IP

    def __init__(self, db: SupabaseClient, scraper_api: ScraperApiConfig | None = None) -> None:
        self._db = db
        self._scraper_api = scraper_api

    # ── Abstract methods each source must implement ───────────────────

    @abstractmethod
    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        """Return scraped jobs for a single query."""
        ...

    # ── Shared logic ──────────────────────────────────────────────────

    def _random_headers(self) -> dict[str, str]:
        headers = dict(REQUEST_HEADERS)
        headers["User-Agent"] = random.choice(USER_AGENTS)
        return headers

    async def _delay(self) -> None:
        await asyncio.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    def _should_proxy(self) -> bool:
        """Check if this scraper should route through ScraperAPI."""
        return self.use_proxy and self._scraper_api is not None and self._scraper_api.enabled

    def _build_client_kwargs(self) -> dict[str, Any]:
        """Build httpx.AsyncClient kwargs, adding proxy if needed."""
        kwargs: dict[str, Any] = {
            "headers": self._random_headers(),
            "follow_redirects": True,
            "timeout": 60.0 if self._should_proxy() else 30.0,
        }
        if self._should_proxy():
            kwargs["proxy"] = self._scraper_api.proxy_url
        return kwargs

    async def run(self) -> ScrapeResult:
        result = ScrapeResult()
        log_id = self._db.create_scrape_log(self.source_name)

        if self.use_proxy and not self._should_proxy():
            logger.warning(
                "%s requires proxy but SCRAPER_API_KEY not configured — skipping",
                self.source_name,
            )
            self._db.complete_scrape_log(
                log_id, errors=["Proxy required but not configured"], status="failed",
            )
            return result

        try:
            async with httpx.AsyncClient(**self._build_client_kwargs()) as client:
                for category, queries in SEARCH_QUERIES.items():
                    for query in queries:
                        try:
                            jobs = await self.fetch_listings(query, category, client)
                            for job in jobs:
                                result.jobs_found += 1

                                if not is_london_based(job.location):
                                    continue

                                if not is_relevant_job(job.title, job.company):
                                    continue

                                if self._db.job_url_exists(job.source_url):
                                    result.jobs_duplicate += 1
                                    continue

                                salary_min, salary_max = parse_salary(job.salary_text)
                                enriched = ScrapedJob(
                                    source=job.source,
                                    source_url=job.source_url,
                                    title=job.title,
                                    company=job.company,
                                    location=job.location,
                                    salary_text=job.salary_text,
                                    salary_min=salary_min,
                                    salary_max=salary_max,
                                    description=job.description,
                                    posted_date=job.posted_date,
                                    category=job.category,
                                    application_url=job.application_url,
                                    application_type=job.application_type,
                                )

                                self._db.insert_job(enriched.to_db_row())
                                result.jobs_new += 1

                            await self._delay()
                        except Exception as exc:
                            msg = f"[{self.source_name}] query={query!r}: {str(exc)[:200]}"
                            logger.error(msg)
                            result.errors.append(msg)

            self._db.complete_scrape_log(
                log_id,
                jobs_found=result.jobs_found,
                jobs_new=result.jobs_new,
                jobs_duplicate=result.jobs_duplicate,
                errors=result.errors,
            )
        except Exception as exc:
            msg = f"[{self.source_name}] fatal: {exc}"
            logger.error(msg)
            result.errors.append(msg)
            self._db.complete_scrape_log(
                log_id,
                jobs_found=result.jobs_found,
                jobs_new=result.jobs_new,
                jobs_duplicate=result.jobs_duplicate,
                errors=result.errors,
                status="failed",
            )

        return result
