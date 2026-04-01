"""CorkBoard scraper entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from scraper.config import ARCHIVE_AFTER_DAYS, Config
from scraper.db.supabase_client import SupabaseClient
from scraper.processors.deduplicator import deduplicate_job
from scraper.processors.link_verifier import verify_all_links
from scraper.sources.base import ScrapeResult
from scraper.sources.adzuna import AdzunaScraper
from scraper.sources.caterer import CatererScraper
from scraper.sources.drinks_business import DrinksBusinessScraper
from scraper.sources.harpers import HarpersScraper
from scraper.sources.hospitality_jobs import HospitalityJobsScraper
from scraper.sources.indeed import IndeedScraper
from scraper.sources.linkedin import LinkedInScraper
from scraper.sources.reed import ReedScraper
from scraper.sources.totaljobs import TotaljobsScraper
from scraper.sources.wine_searcher import WineSearcherScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Active scrapers — direct HTTP sources
DIRECT_SCRAPERS = [
    ReedScraper,         # P0 — HTTP, ~700 jobs/run
    LinkedInScraper,     # P1 — HTTP, ~600 jobs/run
    AdzunaScraper,       # P1 — HTTP, server-rendered, good wine/hospitality coverage
]

# Proxy scrapers — require SCRAPER_API_KEY (auto-skip if not configured)
PROXY_SCRAPERS = [
    IndeedScraper,         # P0 — Cloudflare, needs ScraperAPI render=true (~460 credits/run)
    # CatererScraper,      # P0 — mostly general hospitality, already covered by Reed/LinkedIn/Adzuna
    # TotaljobsScraper,    # P1 — low unique yield vs credit cost
    # WineSearcherScraper, # P2 — jobs page returns 404 even with proxy
    # HospitalityJobsScraper, # P2 — 403, low volume
    # HarpersScraper,      # P2 — no jobs section exists
    # DrinksBusinessScraper, # P2 — no jobs section exists
]

SCRAPER_CLASSES = DIRECT_SCRAPERS + PROXY_SCRAPERS


async def run_scrape(config: Config, sources: str = "all") -> None:
    """Run scrapers sequentially. sources: 'all', 'direct', or 'proxy'."""
    db = SupabaseClient(config.supabase)

    if sources == "direct":
        scraper_list = DIRECT_SCRAPERS
    elif sources == "proxy":
        scraper_list = PROXY_SCRAPERS
    else:
        scraper_list = SCRAPER_CLASSES

    total = ScrapeResult()

    for scraper_cls in scraper_list:
        scraper = scraper_cls(db, scraper_api=config.scraper_api)
        logger.info("Starting %s scraper...", scraper.source_name)

        try:
            result = await scraper.run()
            total.jobs_found += result.jobs_found
            total.jobs_new += result.jobs_new
            total.jobs_duplicate += result.jobs_duplicate
            total.errors.extend(result.errors)

            logger.info(
                "%s done: found=%d new=%d dup=%d errors=%d",
                scraper.source_name,
                result.jobs_found,
                result.jobs_new,
                result.jobs_duplicate,
                len(result.errors),
            )
        except Exception as exc:
            logger.error("Scraper %s crashed: %s", scraper.source_name, exc)
            total.errors.append(f"{scraper.source_name} crash: {exc}")

        # Stagger between sources
        await asyncio.sleep(5)

    # Run cross-source deduplication on newly scraped jobs
    logger.info("Running cross-source deduplication...")
    all_active = db.get_all_active_for_dedup()
    for job in all_active:
        deduplicate_job(job, all_active, db)

    # Send notifications for new jobs
    if total.jobs_new > 0:
        await _send_notifications(config, db, total.jobs_new)

    logger.info(
        "Scrape complete: found=%d new=%d dup=%d errors=%d",
        total.jobs_found,
        total.jobs_new,
        total.jobs_duplicate,
        len(total.errors),
    )


async def run_verify(config: Config) -> None:
    """Run link verification on all active jobs."""
    db = SupabaseClient(config.supabase)
    logger.info("Starting link verification...")
    stats = await verify_all_links(db)
    logger.info("Verification complete: %s", stats)


async def run_archive(config: Config) -> None:
    """Archive jobs inactive for 14+ days."""
    db = SupabaseClient(config.supabase)
    logger.info("Starting archive of old inactive jobs...")
    count = db.archive_old_inactive(days=ARCHIVE_AFTER_DAYS)
    logger.info("Archived %d old inactive jobs", count)


async def _send_notifications(config: Config, db: SupabaseClient, count: int) -> None:
    """Send notifications about new jobs found."""
    recent = db.get_active_jobs(limit=count)

    if config.telegram.enabled:
        from scraper.notifications.telegram import send_new_jobs_summary
        await send_new_jobs_summary(config.telegram, recent)

    if config.email.enabled:
        from scraper.notifications.email import send_new_jobs_email
        await send_new_jobs_email(config.email, recent)


def main() -> None:
    parser = argparse.ArgumentParser(description="CorkBoard Job Scraper")
    parser.add_argument(
        "command",
        choices=["scrape", "verify", "archive"],
        help="Which task to run",
    )
    parser.add_argument(
        "--sources",
        choices=["all", "direct", "proxy"],
        default="all",
        help="Which sources to scrape: direct (free), proxy (ScraperAPI), or all",
    )
    args = parser.parse_args()

    config = Config()

    if args.command == "scrape":
        asyncio.run(run_scrape(config, sources=args.sources))
    elif args.command == "verify":
        asyncio.run(run_verify(config))
    else:
        asyncio.run(run_archive(config))


if __name__ == "__main__":
    main()
