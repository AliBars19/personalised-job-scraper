"""Tests for ScraperAPI proxy integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.config import ScraperApiConfig
from scraper.sources.base import BaseScraper, ScrapedJob, ScrapeResult
from scraper.sources.indeed import IndeedScraper
from scraper.sources.caterer import CatererScraper
from scraper.sources.totaljobs import TotaljobsScraper
from scraper.sources.reed import ReedScraper


# ── ScraperApiConfig tests ──────────────────────────────────────────


class TestScraperApiConfig:
    def test_enabled_with_key(self):
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "test_key_123")
        assert config.enabled is True

    def test_disabled_without_key(self):
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "")
        assert config.enabled is False

    def test_proxy_url(self):
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "mykey123")
        assert config.proxy_url == "http://scraperapi:mykey123@proxy-server.scraperapi.com:8001"

    def test_api_url_basic(self):
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "mykey123")
        url = config.api_url("https://example.com/page?q=test")
        assert "api_key=mykey123" in url
        assert "url=https%3A%2F%2Fexample.com" in url
        assert "render" not in url

    def test_api_url_with_render(self):
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "mykey123")
        url = config.api_url("https://example.com", render=True)
        assert "render=true" in url


# ── use_proxy flag tests ────────────────────────────────────────────


class TestUseProxyFlag:
    def test_reed_no_proxy(self):
        assert ReedScraper.use_proxy is False

    def test_indeed_needs_proxy(self):
        assert IndeedScraper.use_proxy is True

    def test_caterer_needs_proxy(self):
        assert CatererScraper.use_proxy is True

    def test_totaljobs_needs_proxy(self):
        assert TotaljobsScraper.use_proxy is True


# ── _should_proxy logic ─────────────────────────────────────────────


class TestShouldProxy:
    def test_proxy_source_with_key(self):
        db = MagicMock()
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "test_key")
        scraper = IndeedScraper(db, scraper_api=config)
        assert scraper._should_proxy() is True

    def test_proxy_source_without_key(self):
        db = MagicMock()
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "")
        scraper = IndeedScraper(db, scraper_api=config)
        assert scraper._should_proxy() is False

    def test_proxy_source_no_config(self):
        db = MagicMock()
        scraper = IndeedScraper(db, scraper_api=None)
        assert scraper._should_proxy() is False

    def test_direct_source_with_key(self):
        db = MagicMock()
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "test_key")
        scraper = ReedScraper(db, scraper_api=config)
        assert scraper._should_proxy() is False


# ── _build_client_kwargs tests ──────────────────────────────────────


class TestBuildClientKwargs:
    def test_direct_scraper_no_proxy_kwarg(self):
        db = MagicMock()
        scraper = ReedScraper(db)
        kwargs = scraper._build_client_kwargs()
        assert "proxy" not in kwargs
        assert kwargs["timeout"] == 30.0

    def test_proxy_scraper_with_key_adds_proxy(self):
        db = MagicMock()
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "test_key")
        scraper = IndeedScraper(db, scraper_api=config)
        kwargs = scraper._build_client_kwargs()
        assert "proxy" in kwargs
        assert "scraperapi" in kwargs["proxy"]
        assert kwargs["timeout"] == 60.0  # longer for proxy

    def test_proxy_scraper_without_key_no_proxy(self):
        db = MagicMock()
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "")
        scraper = IndeedScraper(db, scraper_api=config)
        kwargs = scraper._build_client_kwargs()
        assert "proxy" not in kwargs


# ── Indeed API URL rewriting ─────────────────────────────────────────


class TestIndeedApiUrlRewrite:
    def test_indeed_uses_api_url_with_render(self):
        """Indeed should rewrite URLs to ScraperAPI API mode with render=true."""
        db = MagicMock()
        config = ScraperApiConfig.__new__(ScraperApiConfig)
        object.__setattr__(config, "api_key", "test_key")
        scraper = IndeedScraper(db, scraper_api=config)

        # The api_url method should produce correct URL
        url = config.api_url("https://uk.indeed.com/jobs?q=sommelier&l=London", render=True)
        assert "api.scraperapi.com" in url
        assert "render=true" in url
        assert "uk.indeed.com" in url


# ── run() skips proxy sources without key ────────────────────────────


class TestRunSkipsWithoutKey:
    @pytest.mark.asyncio
    async def test_proxy_source_skips_without_key(self):
        db = MagicMock()
        db.create_scrape_log = MagicMock(return_value="log-id")
        db.complete_scrape_log = MagicMock()

        scraper = IndeedScraper(db, scraper_api=None)
        result = await scraper.run()

        assert result.jobs_found == 0
        assert result.jobs_new == 0
        db.complete_scrape_log.assert_called_once()
        call_kwargs = db.complete_scrape_log.call_args
        assert call_kwargs[1]["status"] == "failed"
        assert "Proxy required" in call_kwargs[1]["errors"][0]


# ── Indeed BS4 parsing ──────────────────────────────────────────────


INDEED_HTML = """
<div class="job_seen_beacon">
  <h2 class="jobTitle">
    <a href="/viewjob?jk=abc123" data-jk="abc123">
      <span>Restaurant Manager</span>
    </a>
  </h2>
  <span data-testid="company-name">The Ivy</span>
  <div data-testid="text-location">London EC2</div>
  <div data-testid="attribute_snippet_testid">£35,000 - £42,000 a year</div>
</div>
"""


class TestIndeedParsing:
    def test_parse_card(self):
        from bs4 import BeautifulSoup
        db = MagicMock()
        scraper = IndeedScraper(db)
        soup = BeautifulSoup(INDEED_HTML, "lxml")
        card = soup.select_one("div.job_seen_beacon")
        job = scraper._parse_card(card, "hospitality")

        assert job is not None
        assert job.title == "Restaurant Manager"
        assert job.company == "The Ivy"
        assert job.location == "London EC2"
        assert job.salary_text == "£35,000 - £42,000 a year"
        assert job.source == "indeed"
        assert "abc123" in job.source_url


# ── Caterer BS4 parsing ─────────────────────────────────────────────


CATERER_HTML = """
<article class="job-result">
  <h2><a href="/jobs/head-sommelier/12345" class="job-title">Head Sommelier</a></h2>
  <div class="company-name">The Savoy</div>
  <div class="location">London WC2R</div>
  <div class="salary">£38,000 - £45,000</div>
  <div class="description">Prestigious hotel seeking experienced sommelier.</div>
</article>
"""


class TestCatererParsing:
    def test_parse_card(self):
        from bs4 import BeautifulSoup
        db = MagicMock()
        scraper = CatererScraper(db)
        soup = BeautifulSoup(CATERER_HTML, "lxml")
        card = soup.select_one("article")
        job = scraper._parse_card(card, "wine")

        assert job is not None
        assert job.title == "Head Sommelier"
        assert job.company == "The Savoy"
        assert job.location == "London WC2R"
        assert job.salary_text == "£38,000 - £45,000"
        assert job.source == "caterer"
        assert job.description == "Prestigious hotel seeking experienced sommelier."
        assert "caterer.com" in job.source_url
