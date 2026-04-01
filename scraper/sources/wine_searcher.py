"""Wine-Searcher Jobs scraper."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.wine-searcher.com"


class WineSearcherScraper(BaseScraper):
    source_name = "wine_searcher"
    use_proxy = True

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        """Wine-Searcher has a small jobs section, no pagination needed."""
        jobs: list[ScrapedJob] = []

        url = f"{BASE_URL}/jobs.lml?q={quote_plus(query)}"

        try:
            resp = await client.get(url, headers=self._random_headers())
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Wine-Searcher returned %d", exc.response.status_code)
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("div.job-listing, article.job-card, tr.job-row")

        for card in cards:
            try:
                job = self._parse_card(card, category)
                if job:
                    jobs.append(job)
            except Exception as exc:
                logger.debug("Wine-Searcher card parse error: %s", exc)

        return jobs

    def _parse_card(self, card: BeautifulSoup, category: str) -> ScrapedJob | None:
        title_el = card.select_one("a.job-title, h3 a, td a")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job_url = urljoin(BASE_URL, href) if href else ""
        if not job_url:
            return None

        company_el = card.select_one(".company, .employer, td:nth-of-type(2)")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        location_el = card.select_one(".location, td:nth-of-type(3)")
        location = location_el.get_text(strip=True) if location_el else ""

        return ScrapedJob(
            source=self.source_name,
            source_url=job_url,
            title=title,
            company=company,
            location=location,
            category=category,
            application_url=job_url,
            application_type="external",
        )
