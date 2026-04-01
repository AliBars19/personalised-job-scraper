"""Indeed UK scraper — routes through ScraperAPI to bypass Cloudflare."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.config import MAX_PAGES_PER_QUERY, MAX_PAGES_PROXY
from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://uk.indeed.com"


class IndeedScraper(BaseScraper):
    source_name = "indeed"
    use_proxy = True

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []

        max_pages = MAX_PAGES_PROXY if self._should_proxy() else MAX_PAGES_PER_QUERY
        for pg in range(max_pages):
            start = pg * 10
            url = f"{BASE_URL}/jobs?q={quote_plus(query)}&l=London&start={start}"

            try:
                # For API mode with render=true, use a separate non-proxied client
                # since BaseScraper already sets proxy mode on the main client
                if self._scraper_api and self._scraper_api.enabled:
                    api_url = self._scraper_api.api_url(url, render=True)
                    async with httpx.AsyncClient(timeout=90.0) as api_client:
                        resp = await api_client.get(api_url)
                else:
                    resp = await client.get(url, headers=self._random_headers(), timeout=60.0)
                if resp.status_code in (403, 429, 999):
                    logger.warning(
                        "Indeed rate limited (status %d), stopping", resp.status_code
                    )
                    break
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                logger.warning("Indeed page %d error: %s", pg, exc)
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select(
                "div.job_seen_beacon, div[data-jk], div.cardOutline, "
                "div.result, td.resultContent"
            )

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
        title_el = card.select_one(
            "h2.jobTitle a, h2 a, a[data-jk], "
            "h2.jobTitle span, a.jcs-JobTitle"
        )
        if not title_el:
            return None

        title = title_el.get_text(strip=True)

        # Get the job URL
        link_el = card.select_one("h2 a, a[data-jk], a.jcs-JobTitle")
        href = link_el.get("href", "") if link_el else ""
        job_url = urljoin(BASE_URL, href) if href else ""
        if not job_url:
            return None

        company_el = card.select_one(
            "[data-testid='company-name'], span.companyName, "
            "span[data-testid='company-name'], span.css-1h7lukg"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        location_el = card.select_one(
            "[data-testid='text-location'], div.companyLocation, "
            "div.css-1restlb"
        )
        location = location_el.get_text(strip=True) if location_el else ""

        salary_el = card.select_one(
            "div[data-testid='attribute_snippet_testid'], "
            "div.salary-snippet-container, "
            "div.metadata.salary-snippet-container, "
            "div.css-1cvvo1b"
        )
        salary_text = salary_el.get_text(strip=True) if salary_el else None

        easy_apply_el = card.select_one(
            "span.ialbl, span[data-testid='indeed-apply-badge']"
        )
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
