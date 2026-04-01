"""Harpers Wine & Spirit Trade publication jobs scraper."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.harpers.co.uk"


class HarpersScraper(BaseScraper):
    source_name = "harpers"
    use_proxy = True

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []

        url = f"{BASE_URL}/jobs?q={quote_plus(query)}&location=London"

        try:
            resp = await client.get(url, headers=self._random_headers())
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Harpers returned %d", exc.response.status_code)
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("div.job-listing, article.job, li.job-item")

        for card in cards:
            try:
                job = self._parse_card(card, category)
                if job:
                    jobs.append(job)
            except Exception as exc:
                logger.debug("Harpers card parse error: %s", exc)

        return jobs

    def _parse_card(self, card: BeautifulSoup, category: str) -> ScrapedJob | None:
        title_el = card.select_one("a.job-title, h3 a, h2 a")
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

        return ScrapedJob(
            source=self.source_name,
            source_url=job_url,
            title=title,
            company=company,
            location=location,
            salary_text=salary_text,
            category=category,
            application_url=job_url,
            application_type="external",
        )
