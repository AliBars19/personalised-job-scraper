"""Caterer.com scraper (JS-heavy, uses Playwright)."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from playwright.async_api import async_playwright

from scraper.config import MAX_PAGES_PER_QUERY
from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.caterer.com"


class CatererScraper(BaseScraper):
    source_name = "caterer"

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        """Use Playwright for JS-rendered pages."""
        jobs: list[ScrapedJob] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self._random_headers()["User-Agent"],
                viewport={"width": 1920, "height": 1080},
            )

            try:
                page = await context.new_page()

                for page_num in range(1, MAX_PAGES_PER_QUERY + 1):
                    url = (
                        f"{BASE_URL}/jobs/{quote_plus(query.replace(' ', '-'))}"
                        f"/in-london/?page={page_num}"
                    )

                    try:
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        await page.wait_for_selector(
                            'article, [data-testid="job-card"], .job-result',
                            timeout=10000,
                        )
                    except Exception as exc:
                        logger.warning("Caterer page %d load failed: %s", page_num, exc)
                        break

                    cards = await page.query_selector_all(
                        'article, [data-testid="job-card"], .job-result'
                    )

                    if not cards:
                        break

                    for card in cards:
                        try:
                            job = await self._parse_card(card, category)
                            if job:
                                jobs.append(job)
                        except Exception as exc:
                            logger.debug("Caterer card parse error: %s", exc)

                    await self._delay()

            finally:
                await browser.close()

        return jobs

    async def _parse_card(self, card, category: str) -> ScrapedJob | None:
        title_el = await card.query_selector("h2 a, a.job-title, [data-testid='job-title']")
        if not title_el:
            return None

        title = (await title_el.inner_text()).strip()
        href = await title_el.get_attribute("href") or ""
        job_url = urljoin(BASE_URL, href) if href else ""
        if not job_url:
            return None

        company_el = await card.query_selector(
            ".company-name, [data-testid='company-name']"
        )
        company = (await company_el.inner_text()).strip() if company_el else "Unknown"

        location_el = await card.query_selector(
            ".location, [data-testid='location']"
        )
        location = (await location_el.inner_text()).strip() if location_el else ""

        salary_el = await card.query_selector(
            ".salary, [data-testid='salary']"
        )
        salary_text = (await salary_el.inner_text()).strip() if salary_el else None

        desc_el = await card.query_selector(
            ".description, [data-testid='description'], .job-snippet"
        )
        description = (await desc_el.inner_text()).strip() if desc_el else ""

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
