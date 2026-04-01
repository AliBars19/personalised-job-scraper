"""Adzuna UK scraper — server-rendered HTML, no anti-bot from DO IP."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.config import MAX_PAGES_PER_QUERY
from scraper.sources.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.adzuna.co.uk"


class AdzunaScraper(BaseScraper):
    source_name = "adzuna"

    async def fetch_listings(
        self, query: str, category: str, client: httpx.AsyncClient
    ) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []

        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            url = (
                f"{BASE_URL}/jobs/search?q={quote_plus(query)}"
                f"&w=London&p={page}"
            )

            try:
                resp = await client.get(url, headers=self._random_headers(), timeout=30.0)
                if resp.status_code in (403, 429):
                    logger.warning("Adzuna rate limited (status %d), stopping", resp.status_code)
                    break
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                logger.warning("Adzuna page %d error: %s", page, exc)
                break

            soup = BeautifulSoup(resp.text, "lxml")
            parsed = self._parse_page(soup, category)

            if not parsed:
                break

            jobs.extend(parsed)
            await self._delay()

        return jobs

    def _parse_page(self, soup: BeautifulSoup, category: str) -> list[ScrapedJob]:
        """Parse all job cards from an Adzuna search results page."""
        jobs: list[ScrapedJob] = []

        # Find all anchor tags linking to job details or landing pages
        seen_urls: set[str] = set()

        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)

            if not text or "More details" in text:
                continue

            if "/jobs/details/" not in href and "/jobs/land/" not in href:
                continue

            # Re-extract with separator to preserve spaces between <strong> tags
            text = " ".join(a.get_text(" ", strip=True).split())

            full_url = urljoin(BASE_URL, href.split("?")[0]) if href.startswith("/") else href.split("?")[0]
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Walk up to find the card container with company/location/salary
            company = ""
            location = ""
            salary_text = None

            parent = a.parent
            for _ in range(10):
                if parent is None:
                    break

                company_el = parent.find("div", class_="ui-company")
                if company_el:
                    location_el = parent.find("div", class_="ui-location")
                    salary_el = parent.find("div", class_="ui-salary")

                    company = company_el.get_text(strip=True)
                    location = location_el.get_text(strip=True) if location_el else ""
                    raw_salary = salary_el.get_text(strip=True) if salary_el else ""
                    # Clean Adzuna salary formatting (e.g. "£35,000CLOSING SOON" → "£35,000")
                    salary_text = self._clean_salary(raw_salary) if raw_salary else None
                    break

                parent = parent.parent

            if not company:
                continue

            jobs.append(
                ScrapedJob(
                    source=self.source_name,
                    source_url=full_url,
                    title=text,
                    company=company,
                    location=location,
                    salary_text=salary_text,
                    category=category,
                    application_url=full_url,
                    application_type="external",
                )
            )

        return jobs

    @staticmethod
    def _clean_salary(raw: str) -> str | None:
        """Strip Adzuna noise from salary text."""
        import re
        # Remove trailing tags like "CLOSING SOON", "NEW", "TOP MATCH", "EASY APPLY",
        # "ABOVE AVERAGE SALARY", review counts, and "JOBSWORTH:..."
        cleaned = re.sub(
            r"(CLOSING\s*SOON|NEW|TOP\s*MATCH|EASY\s*APPLY|ABOVE\s*AVERAGE\s*SALARY"
            r"|JOBSWORTH:[^£]*|\d+\s*reviews?)",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()
        # Remove leading "JOBSWORTH:" prefix
        cleaned = re.sub(r"^JOBSWORTH:\s*", "", cleaned, flags=re.IGNORECASE).strip()
        # Remove question marks Adzuna inserts
        cleaned = cleaned.replace("&quest;", "").replace("?", "").strip()
        # Normalize "per year" / "per annum" spacing
        cleaned = re.sub(r"(\d)(per\s)", r"\1 \2", cleaned, flags=re.IGNORECASE)
        return cleaned if cleaned else None
