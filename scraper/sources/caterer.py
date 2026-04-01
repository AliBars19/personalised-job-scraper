"""Caterer.com scraper — routes through ScraperAPI to bypass Cloudflare."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.config import MAX_PAGES_PER_QUERY, MAX_PAGES_PROXY
from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.caterer.com"


class CatererScraper(BaseScraper):
    source_name = "caterer"
    use_proxy = True

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []

        max_pages = MAX_PAGES_PROXY if self._should_proxy() else MAX_PAGES_PER_QUERY
        for page_num in range(1, max_pages + 1):
            url = (
                f"{BASE_URL}/jobs/{quote_plus(query.replace(' ', '-'))}"
                f"/in-london/?page={page_num}"
            )

            try:
                if self._scraper_api and self._scraper_api.enabled:
                    api_url = self._scraper_api.api_url(url, render=True)
                    async with httpx.AsyncClient(timeout=90.0) as api_client:
                        resp = await api_client.get(api_url)
                else:
                    resp = await client.get(url, headers=self._random_headers(), timeout=60.0)
                if resp.status_code in (403, 429):
                    logger.warning(
                        "Caterer rate limited (status %d), stopping", resp.status_code
                    )
                    break
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                logger.warning("Caterer page %d error: %s", page_num, exc)
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Caterer wraps each job in a container with data-at="job-item-title"
            # Walk up from each title to find the card boundary
            title_els = soup.find_all(attrs={"data-at": "job-item-title"})

            if not title_els:
                break

            # Build cards by walking up from each title to a reasonable container
            cards = []
            for title_el in title_els:
                parent = title_el.parent
                for _ in range(8):
                    if parent is None:
                        break
                    # The card container has company, location, salary siblings
                    if parent.find(attrs={"data-at": "job-item-company-name"}):
                        cards.append(parent)
                        break
                    parent = parent.parent

            for card in cards:
                try:
                    job = self._parse_card(card, category)
                    if job:
                        jobs.append(job)
                except Exception as exc:
                    logger.debug("Caterer card parse error: %s", exc)

            await self._delay()

        return jobs

    def _parse_card(self, card: BeautifulSoup, category: str) -> ScrapedJob | None:
        title_el = card.select_one(
            '[data-testid="job-item-title"], [data-at="job-item-title"], '
            "h2 a, a.job-title"
        )
        if not title_el:
            return None

        title = title_el.get_text(" ", strip=True)
        href = title_el.get("href", "")
        job_url = urljoin(BASE_URL, href) if href else ""
        if not job_url or "/job/" not in job_url:
            return None

        company_el = card.select_one(
            '[data-at="job-item-company-name"], '
            '[data-testid="company-name"], .company-name'
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        location_el = card.select_one(
            '[data-at="job-item-location"], '
            '[data-testid="location"], .location'
        )
        location = location_el.get_text(strip=True) if location_el else ""

        salary_el = card.select_one(
            '[data-at="job-item-salary-info"], '
            '[data-testid="salary"], .salary'
        )
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
