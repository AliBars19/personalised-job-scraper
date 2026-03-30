"""LinkedIn job scraper (uses public job search, no auth)."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.config import MAX_PAGES_PER_QUERY
from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

# Public LinkedIn jobs search (no login required)
BASE_URL = "https://www.linkedin.com"


class LinkedInScraper(BaseScraper):
    source_name = "linkedin"

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        """Scrape LinkedIn public job listings. Anti-scrape is aggressive here
        so we limit pagination and add extra delays."""
        jobs: list[ScrapedJob] = []

        # LinkedIn paginates with start= in increments of 25
        max_pages = min(MAX_PAGES_PER_QUERY, 3)  # Be conservative with LinkedIn

        for page in range(max_pages):
            start = page * 25
            url = (
                f"{BASE_URL}/jobs/search?"
                f"keywords={quote_plus(query)}"
                f"&location=London%2C%20United%20Kingdom"
                f"&start={start}"
            )

            try:
                resp = await client.get(url, headers=self._random_headers())
                if resp.status_code in (403, 429, 999):
                    logger.warning(
                        "LinkedIn rate limited (status %d), stopping",
                        resp.status_code,
                    )
                    break
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning("LinkedIn page %d error: %s", page, exc)
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select(
                'div.base-card, '
                'li.result-card, '
                'div.job-search-card'
            )

            if not cards:
                break

            for card in cards:
                try:
                    job = self._parse_card(card, category)
                    if job:
                        jobs.append(job)
                except Exception as exc:
                    logger.debug("LinkedIn card parse error: %s", exc)

            # Extra delay for LinkedIn
            await self._delay()
            await self._delay()

        return jobs

    def _parse_card(self, card: BeautifulSoup, category: str) -> ScrapedJob | None:
        title_el = card.select_one(
            'h3.base-search-card__title, '
            'span.screen-reader-text, '
            'a.base-card__full-link'
        )
        if not title_el:
            return None

        title = title_el.get_text(strip=True)

        link_el = card.select_one('a.base-card__full-link, a[data-tracking-control-name]')
        href = link_el.get("href", "") if link_el else ""
        job_url = href.split("?")[0] if href else ""  # Strip tracking params
        if not job_url:
            return None

        company_el = card.select_one(
            'h4.base-search-card__subtitle a, '
            'a.hidden-nested-link'
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        location_el = card.select_one(
            'span.job-search-card__location'
        )
        location = location_el.get_text(strip=True) if location_el else ""

        # LinkedIn rarely shows salary in search results
        salary_text = None

        return ScrapedJob(
            source=self.source_name,
            source_url=job_url,
            title=title,
            company=company,
            location=location,
            salary_text=salary_text,
            description="",
            category=category,
            application_url=job_url,
            application_type="external",
        )
