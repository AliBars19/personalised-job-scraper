"""Indeed UK scraper — uses Playwright due to anti-bot measures."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from playwright.async_api import async_playwright

from scraper.config import MAX_PAGES_PER_QUERY, SEARCH_QUERIES
from scraper.processors.location_filter import is_london_based
from scraper.processors.salary_parser import parse_salary
from scraper.sources.base import BaseScraper, ScrapeResult, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://uk.indeed.com"


class IndeedScraper(BaseScraper):
    source_name = "indeed"

    async def run(self) -> ScrapeResult:
        """Override run() to use a single Playwright browser for all queries."""
        result = ScrapeResult()
        log_id = self._db.create_scrape_log(self.source_name)

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self._random_headers()["User-Agent"],
                    viewport={"width": 1920, "height": 1080},
                )

                try:
                    page = await context.new_page()

                    for category, queries in SEARCH_QUERIES.items():
                        for query in queries:
                            try:
                                jobs = await self._fetch_with_page(page, query, category)
                                for job in jobs:
                                    result.jobs_found += 1

                                    if not is_london_based(job.location):
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
                                msg = f"[{self.source_name}] query={query!r}: {exc}"
                                logger.error(msg)
                                result.errors.append(msg)
                finally:
                    await browser.close()

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

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        """Not used directly — see run() override."""
        return []

    async def _fetch_with_page(
        self, page, query: str, category: str
    ) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []

        for pg in range(MAX_PAGES_PER_QUERY):
            start = pg * 10
            url = f"{BASE_URL}/jobs?q={quote_plus(query)}&l=London&start={start}"

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector(
                    "div.job_seen_beacon, div[data-jk], a[data-jk], div.cardOutline, div.slider_container",
                    timeout=10000,
                )
            except Exception as exc:
                logger.warning("Indeed page %d load failed: %s", pg, exc)
                break

            cards = await page.query_selector_all(
                "div.job_seen_beacon, div[data-jk], div.cardOutline"
            )

            if not cards:
                break

            for card in cards:
                try:
                    job = await self._parse_card(card, category)
                    if job:
                        jobs.append(job)
                except Exception as exc:
                    logger.debug("Indeed card parse error: %s", exc)

            await self._delay()

        return jobs

    async def _parse_card(self, card, category: str) -> ScrapedJob | None:
        title_el = await card.query_selector("h2 a, a[data-jk], h2.jobTitle span")
        if not title_el:
            return None

        title = (await title_el.inner_text()).strip()

        link_el = await card.query_selector("h2 a, a[data-jk]")
        href = (await link_el.get_attribute("href")) if link_el else ""
        job_url = urljoin(BASE_URL, href) if href else ""
        if not job_url:
            return None

        company_el = await card.query_selector(
            "[data-testid='company-name'], span.companyName, span[data-testid='company-name']"
        )
        company = (await company_el.inner_text()).strip() if company_el else "Unknown"

        location_el = await card.query_selector(
            "[data-testid='text-location'], div.companyLocation"
        )
        location = (await location_el.inner_text()).strip() if location_el else ""

        salary_el = await card.query_selector(
            "div[data-testid='attribute_snippet_testid'], div.salary-snippet-container, "
            "div.metadata.salary-snippet-container"
        )
        salary_text = (await salary_el.inner_text()).strip() if salary_el else None

        easy_apply_el = await card.query_selector(
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
