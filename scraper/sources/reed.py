"""Reed.co.uk scraper."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.config import MAX_PAGES_PER_QUERY
from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.reed.co.uk"


class ReedScraper(BaseScraper):
    source_name = "reed"

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []

        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            url = (
                f"{BASE_URL}/jobs/{quote_plus(query.replace(' ', '-'))}"
                f"-jobs-in-london?pageno={page}"
            )

            try:
                resp = await client.get(url, headers=self._random_headers(), timeout=30.0)
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                logger.warning("Reed page %d error: %s", page, exc)
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("article")

            if not cards:
                break

            for card in cards:
                try:
                    job = self._parse_card(card, category)
                    if job:
                        jobs.append(job)
                except Exception as exc:
                    logger.debug("Reed card parse error: %s", exc)

            await self._delay()

        return jobs

    def _parse_card(self, card: BeautifulSoup, category: str) -> ScrapedJob | None:
        title_el = card.select_one("h2 a, a[class*=jobTitle]")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job_url = urljoin(BASE_URL, href) if href else ""
        if not job_url:
            return None

        company_el = card.select_one("a.gtmJobListingPostedBy, a[class*=profileUrl]")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        # Reed uses <li> items inside a <ul> for metadata: salary, location, type
        metadata_items = card.select("li.list-group-item, li[class*=jobMetadata__item]")
        salary_text = None
        location = ""

        for item in metadata_items:
            text = item.get_text(strip=True)
            if not text:
                continue
            # Salary indicators
            if any(kw in text.lower() for kw in ("£", "salary", "competitive", "per annum", "per hour")):
                salary_text = text
            # Location — contains London or known area names
            elif any(kw in text.lower() for kw in ("london", "ec", "wc", "sw", "se", "nw")):
                location = text
            # If no salary or location yet, first item is often salary, second is location
            elif salary_text is None and not text.lower().startswith(("full", "part", "temp", "perm", "contract")):
                salary_text = text
            elif not location and not text.lower().startswith(("full", "part", "temp", "perm", "contract")):
                location = text

        # Easy apply detection
        easy_apply_el = card.select_one("[class*=easyApply], button[class*=easyApply]")
        app_type = "easy_apply" if easy_apply_el else "external"

        return ScrapedJob(
            source=self.source_name,
            source_url=job_url,
            title=title,
            company=company,
            location=location,
            salary_text=salary_text,
            category=category,
            application_url=job_url,
            application_type=app_type,
        )
