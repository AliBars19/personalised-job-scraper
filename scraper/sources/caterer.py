"""Caterer.com scraper (JS-heavy, uses Playwright)."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from playwright.async_api import async_playwright

from scraper.config import MAX_PAGES_PER_QUERY, SEARCH_QUERIES
from scraper.processors.location_filter import is_london_based
from scraper.processors.relevance_filter import is_relevant_job
from scraper.processors.salary_parser import parse_salary
from scraper.sources.base import BaseScraper, ScrapeResult, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.caterer.com"


class CatererScraper(BaseScraper):
    source_name = "caterer"

    async def run(self) -> ScrapeResult:
        """Override run() to share a single browser across all queries."""
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
                                jobs = await self._fetch_with_page(
                                    page, query, category
                                )
                                for job in jobs:
                                    result.jobs_found += 1

                                    if not is_london_based(job.location):
                                        continue

                                    if not is_relevant_job(job.title, job.company):
                                        continue

                                    if self._db.job_url_exists(job.source_url):
                                        result.jobs_duplicate += 1
                                        continue

                                    salary_min, salary_max = parse_salary(
                                        job.salary_text
                                    )
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
        """Not used directly — see run() override. Kept for interface compliance."""
        return []

    async def _fetch_with_page(
        self, page, query: str, category: str
    ) -> list[ScrapedJob]:
        """Fetch listings using a shared Playwright page."""
        jobs: list[ScrapedJob] = []

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
