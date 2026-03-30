"""Indeed UK scraper."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.config import MAX_PAGES_PER_QUERY
from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://uk.indeed.com"


class IndeedScraper(BaseScraper):
    source_name = "indeed"

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []

        for page in range(MAX_PAGES_PER_QUERY):
            start = page * 10
            url = (
                f"{BASE_URL}/jobs?q={quote_plus(query)}"
                f"&l=London&start={start}"
            )

            try:
                resp = await client.get(url, headers=self._random_headers())
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning("Indeed page %d returned %d", page, exc.response.status_code)
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select('div.job_seen_beacon, div[data-jk]')

            if not cards:
                break

            for card in cards:
                try:
                    job = self._parse_card(card, category)
                    if job:
                        jobs.append(job)
                except Exception as exc:
                    logger.debug("Indeed card parse error: %s", exc)

            await self._delay()

        return jobs

    def _parse_card(self, card: BeautifulSoup, category: str) -> ScrapedJob | None:
        title_el = card.select_one('h2.jobTitle a, a[data-jk]')
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job_url = urljoin(BASE_URL, href) if href else ""
        if not job_url:
            return None

        company_el = card.select_one('[data-testid="company-name"], span.companyName')
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        location_el = card.select_one('[data-testid="text-location"], div.companyLocation')
        location = location_el.get_text(strip=True) if location_el else ""

        salary_el = card.select_one(
            'div[data-testid="attribute_snippet_testid"], '
            'div.salary-snippet-container, '
            'div.metadata.salary-snippet-container'
        )
        salary_text = salary_el.get_text(strip=True) if salary_el else None

        snippet_el = card.select_one('div.job-snippet, td.resultContent div.job-snippet')
        description = snippet_el.get_text(strip=True) if snippet_el else ""

        date_el = card.select_one('span.date, span[data-testid="myJobsStateDate"]')
        posted_date = None  # Indeed uses relative dates, hard to parse precisely

        # Indeed Easy Apply detection
        easy_apply_el = card.select_one('span.ialbl, span[data-testid="indeed-apply-badge"]')
        app_type = "easy_apply" if easy_apply_el else "external"

        return ScrapedJob(
            source=self.source_name,
            source_url=job_url,
            title=title,
            company=company,
            location=location,
            salary_text=salary_text,
            description=description,
            posted_date=posted_date,
            category=category,
            application_url=job_url,
            application_type=app_type,
        )
