"""Tests for the Adzuna scraper — parsing and salary cleaning."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from scraper.sources.adzuna import AdzunaScraper


@pytest.fixture
def scraper():
    """Create an AdzunaScraper with a mocked DB client."""
    db = MagicMock()
    return AdzunaScraper(db)


# ── HTML fixtures ────────────────────────────────────────────────────

SINGLE_JOB_HTML = """
<div class="ui-search-results w-full md:w-3/4">
  <div>
    <a class="text-base text-adzuna-green-500"
       data-js="jobLink"
       href="https://www.adzuna.co.uk/jobs/details/5676136311"
       rel="nofollow" target="_blank">
      <strong>Sommelier</strong>
    </a>
    <div class="ui-job-card-info">
      <div class="ui-company">RAFFLES</div>
      <div class="ui-location text-adzuna-gray-900">LONDON, UK</div>
      <div class="ui-salary">£35,000</div>
    </div>
  </div>
</div>
"""

MULTI_WORD_TITLE_HTML = """
<div>
  <div>
    <a data-js="jobLink" href="/jobs/details/5683617024" rel="nofollow">
      <strong>Junior</strong> <strong>Sommelier</strong>
    </a>
    <div class="ui-job-card-info">
      <div class="ui-company">THE ROOF GARDENS</div>
      <div class="ui-location">CENTRAL LONDON</div>
      <div class="ui-salary">UP TO £16.55 PER HOUR</div>
    </div>
  </div>
</div>
"""

MULTIPLE_JOBS_HTML = """
<div class="ui-search-results">
  <div>
    <a data-js="jobLink" href="/jobs/details/111111" rel="nofollow">
      <strong>Head</strong> <strong>Sommelier</strong>
    </a>
    <a href="/jobs/details/111111">More details ❯</a>
    <div class="ui-job-card-info">
      <div class="ui-company">NOBLE ROT</div>
      <div class="ui-location">LONDON, WC1N 3NB</div>
      <div class="ui-salary">£46,000 - £48,000CLOSING SOON</div>
    </div>
  </div>
  <div>
    <a data-js="jobLink" href="https://www.adzuna.co.uk/jobs/land/ad/222222?se=abc" rel="nofollow">
      <strong>Restaurant</strong> <strong>Manager</strong>
    </a>
    <a href="https://www.adzuna.co.uk/jobs/land/ad/222222?se=abc">More details ❯</a>
    <div class="ui-job-card-info">
      <div class="ui-company">13TH STREET HOSPITALITY</div>
      <div class="ui-location">CITY OF LONDON, EC2M 2QS</div>
      <div class="ui-salary">£40,000</div>
    </div>
  </div>
</div>
"""

NO_SALARY_HTML = """
<div>
  <div>
    <a data-js="jobLink" href="/jobs/details/333333" rel="nofollow">
      <strong>Bar</strong> <strong>Manager</strong>
    </a>
    <div class="ui-job-card-info">
      <div class="ui-company">SOHO HOUSE</div>
      <div class="ui-location">SOHO, LONDON</div>
    </div>
  </div>
</div>
"""

NO_COMPANY_HTML = """
<div>
  <a data-js="jobLink" href="/jobs/details/444444" rel="nofollow">
    <strong>Sommelier</strong>
  </a>
</div>
"""

EMPTY_PAGE_HTML = """
<div class="ui-search-results">
  <p>No results found for your search.</p>
</div>
"""

DUPLICATE_URL_HTML = """
<div class="ui-search-results">
  <div>
    <a data-js="jobLink" href="/jobs/details/555555" rel="nofollow">
      <strong>Sommelier</strong>
    </a>
    <div class="ui-job-card-info">
      <div class="ui-company">ROKA</div>
      <div class="ui-location">LONDON</div>
      <div class="ui-salary">£35,000</div>
    </div>
  </div>
  <div>
    <a data-js="jobLink" href="/jobs/details/555555" rel="nofollow">
      <strong>Sommelier</strong>
    </a>
    <div class="ui-job-card-info">
      <div class="ui-company">ROKA</div>
      <div class="ui-location">LONDON</div>
      <div class="ui-salary">£35,000</div>
    </div>
  </div>
</div>
"""

NOISY_SALARY_HTML = """
<div>
  <div>
    <a data-js="jobLink" href="/jobs/details/666666" rel="nofollow">
      <strong>Sommelier</strong>
    </a>
    <div class="ui-job-card-info">
      <div class="ui-company">HAWKSMOOR</div>
      <div class="ui-location">LONDON</div>
      <div class="ui-salary">JOBSWORTH:£28,528per year&quest;TOP MATCHEASY APPLY</div>
    </div>
  </div>
</div>
"""


# ── _parse_page tests ────────────────────────────────────────────────


class TestParsePage:
    def test_single_job(self, scraper):
        soup = BeautifulSoup(SINGLE_JOB_HTML, "lxml")
        jobs = scraper._parse_page(soup, "wine")

        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Sommelier"
        assert job.company == "RAFFLES"
        assert job.location == "LONDON, UK"
        assert job.salary_text == "£35,000"
        assert job.source == "adzuna"
        assert job.category == "wine"
        assert "5676136311" in job.source_url
        assert job.application_type == "external"

    def test_multi_word_title_preserves_spaces(self, scraper):
        soup = BeautifulSoup(MULTI_WORD_TITLE_HTML, "lxml")
        jobs = scraper._parse_page(soup, "wine")

        assert len(jobs) == 1
        assert jobs[0].title == "Junior Sommelier"

    def test_multiple_jobs(self, scraper):
        soup = BeautifulSoup(MULTIPLE_JOBS_HTML, "lxml")
        jobs = scraper._parse_page(soup, "hospitality")

        assert len(jobs) == 2
        assert jobs[0].title == "Head Sommelier"
        assert jobs[0].company == "NOBLE ROT"
        assert jobs[0].salary_text == "£46,000 - £48,000"
        assert jobs[1].title == "Restaurant Manager"
        assert jobs[1].company == "13TH STREET HOSPITALITY"

    def test_skips_more_details_links(self, scraper):
        soup = BeautifulSoup(MULTIPLE_JOBS_HTML, "lxml")
        jobs = scraper._parse_page(soup, "hospitality")

        # Should have 2 jobs, not 4 (each job has a "More details" link)
        assert len(jobs) == 2

    def test_deduplicates_same_url(self, scraper):
        soup = BeautifulSoup(DUPLICATE_URL_HTML, "lxml")
        jobs = scraper._parse_page(soup, "wine")

        assert len(jobs) == 1

    def test_no_salary_field(self, scraper):
        soup = BeautifulSoup(NO_SALARY_HTML, "lxml")
        jobs = scraper._parse_page(soup, "hospitality")

        assert len(jobs) == 1
        assert jobs[0].salary_text is None
        assert jobs[0].title == "Bar Manager"
        assert jobs[0].company == "SOHO HOUSE"

    def test_skips_jobs_without_company(self, scraper):
        soup = BeautifulSoup(NO_COMPANY_HTML, "lxml")
        jobs = scraper._parse_page(soup, "wine")

        assert len(jobs) == 0

    def test_empty_results_page(self, scraper):
        soup = BeautifulSoup(EMPTY_PAGE_HTML, "lxml")
        jobs = scraper._parse_page(soup, "wine")

        assert len(jobs) == 0

    def test_strips_tracking_params_from_url(self, scraper):
        soup = BeautifulSoup(MULTIPLE_JOBS_HTML, "lxml")
        jobs = scraper._parse_page(soup, "hospitality")

        # The /land/ URL has ?se=abc which should be stripped
        restaurant_mgr = jobs[1]
        assert "?se=" not in restaurant_mgr.source_url
        assert "222222" in restaurant_mgr.source_url

    def test_relative_urls_resolved(self, scraper):
        soup = BeautifulSoup(MULTI_WORD_TITLE_HTML, "lxml")
        jobs = scraper._parse_page(soup, "wine")

        assert jobs[0].source_url.startswith("https://www.adzuna.co.uk/")

    def test_noisy_salary_cleaned(self, scraper):
        soup = BeautifulSoup(NOISY_SALARY_HTML, "lxml")
        jobs = scraper._parse_page(soup, "wine")

        assert len(jobs) == 1
        # Should strip JOBSWORTH:, &quest;, TOP MATCH, EASY APPLY
        assert "JOBSWORTH" not in (jobs[0].salary_text or "")
        assert "TOP MATCH" not in (jobs[0].salary_text or "")
        assert "EASY APPLY" not in (jobs[0].salary_text or "")
        assert "£28,528" in (jobs[0].salary_text or "")


# ── _clean_salary tests ─────────────────────────────────────────────


class TestCleanSalary:
    def test_clean_amount(self):
        assert AdzunaScraper._clean_salary("£35,000") == "£35,000"

    def test_range(self):
        assert AdzunaScraper._clean_salary("£35,000 - £42,000") == "£35,000 - £42,000"

    def test_strips_closing_soon(self):
        assert AdzunaScraper._clean_salary("£46,000 - £48,000CLOSING SOON") == "£46,000 - £48,000"

    def test_strips_new(self):
        assert AdzunaScraper._clean_salary("UP TO £48000.00 PER ANNUMNEW") == "UP TO £48000.00 PER ANNUM"

    def test_strips_top_match(self):
        result = AdzunaScraper._clean_salary("£26,422per yearTOP MATCH")
        assert "TOP MATCH" not in result
        assert "£26,422" in result

    def test_strips_easy_apply(self):
        result = AdzunaScraper._clean_salary("£28,528EASY APPLY")
        assert result == "£28,528"

    def test_strips_above_average_salary(self):
        result = AdzunaScraper._clean_salary("£45,000ABOVE AVERAGE SALARY")
        assert result == "£45,000"

    def test_strips_review_counts(self):
        result = AdzunaScraper._clean_salary("£33,395per year14 reviews")
        assert "reviews" not in result
        assert "£33,395" in result

    def test_strips_jobsworth_prefix(self):
        result = AdzunaScraper._clean_salary("JOBSWORTH:£28,528per year")
        assert result is not None
        assert "JOBSWORTH" not in result
        assert "£28,528" in result

    def test_strips_quest_entities(self):
        result = AdzunaScraper._clean_salary("£28,528per year&quest;")
        assert "&quest;" not in result

    def test_fixes_number_per_spacing(self):
        result = AdzunaScraper._clean_salary("£33,395per year")
        assert result == "£33,395 per year"

    def test_complex_noisy_salary(self):
        result = AdzunaScraper._clean_salary("JOBSWORTH:£28,528per year&quest;TOP MATCHEASY APPLY")
        assert result is not None
        assert "£28,528" in result
        assert "JOBSWORTH" not in result
        assert "TOP MATCH" not in result
        assert "EASY APPLY" not in result
        assert "&quest;" not in result

    def test_empty_string_returns_none(self):
        assert AdzunaScraper._clean_salary("") is None

    def test_only_noise_returns_none(self):
        assert AdzunaScraper._clean_salary("CLOSING SOON") is None

    def test_hourly_rate(self):
        assert AdzunaScraper._clean_salary("UP TO £18.01 PER HOUR") == "UP TO £18.01 PER HOUR"

    def test_per_annum(self):
        result = AdzunaScraper._clean_salary("£44500- £44500 PER YEAR")
        assert result == "£44500- £44500 PER YEAR"

    def test_range_per_hour(self):
        result = AdzunaScraper._clean_salary("FROM £17 TO £18 PER HOUR")
        assert result == "FROM £17 TO £18 PER HOUR"
