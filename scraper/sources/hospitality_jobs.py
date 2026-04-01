"""Hospitality Jobs UK scraper."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.config import MAX_PAGES_PER_QUERY
from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.hospitalityjobsuk.com"


class HospitalityJobsScraper(BaseScraper):
    source_name = "hospitality_jobs_uk"
    use_proxy = True

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []

        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            url = (
                f"{BASE_URL}/jobs?q={quote_plus(query)}"
                f"&location=London&page={page}"
            )

            try:
                resp = await client.get(url, headers=self._random_headers())
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "HospitalityJobsUK page %d returned %d", page, exc.response.status_code
                )
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("div.job-listing, article.job-card, li.job-item")

            if not cards:
                break

            for card in cards:
                try:
                    job = self._parse_card(card, category)
                    if job:
                        jobs.append(job)
                except Exception as exc:
                    logger.debug("HospitalityJobsUK card parse error: %s", exc)

            await self._delay()

        return jobs

    def _parse_card(self, card: BeautifulSoup, category: str) -> ScrapedJob | None:
        title_el = card.select_one("a.job-title, h2 a, h3 a")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job_url = urljoin(BASE_URL, href) if href else ""
        if not job_url:
            return None

        company_el = card.select_one(".company, .employer")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        location_el = card.select_one(".location")
        location = location_el.get_text(strip=True) if location_el else ""

        salary_el = card.select_one(".salary")
        salary_text = salary_el.get_text(strip=True) if salary_el else None

        desc_el = card.select_one(".description, .snippet")
        description = desc_el.get_text(strip=True) if desc_el else ""

        return ScrapedJob(
            source=self.source_name,
            source_url=job_url,
            title=title,
            company=company,
            location=location,
            salary_text=salary_text,
            description=description,
            category=category,
            application_url=job_url,
            application_type="external",
        )
