"""CorkBoard scraper entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from scraper.config import Config
from scraper.db.supabase_client import SupabaseClient
from scraper.processors.deduplicator import deduplicate_job
from scraper.processors.link_verifier import verify_all_links
from scraper.sources.base import ScrapeResult
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

# Ordered by priority
SCRAPER_CLASSES = [
    IndeedScraper,       # P0
    ReedScraper,         # P0
    CatererScraper,      # P0
    TotaljobsScraper,    # P1
    LinkedInScraper,     # P1
    WineSearcherScraper, # P2
    HarpersScraper,      # P2
    HospitalityJobsScraper,  # P2
    DrinksBusinessScraper,   # P2
]


async def run_scrape(config: Config) -> None:
    """Run all scrapers sequentially (staggered by design)."""
    db = SupabaseClient(config.supabase)

    total = ScrapeResult()

    for scraper_cls in SCRAPER_CLASSES:
        scraper = scraper_cls(db)
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
    all_active = db.get_active_jobs(limit=5000)
    # Fetch full data for dedup comparison
    for job in all_active:
        existing = db.get_jobs_for_dedup(
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
        )
        deduplicate_job(job, existing, db)

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
    count = db.archive_old_inactive(days=14)
    logger.info("Archived %d old inactive jobs", count)


async def _send_notifications(config: Config, db: SupabaseClient, count: int) -> None:
    """Send notifications about new jobs found."""
    if config.telegram.enabled:
        from scraper.notifications.telegram import send_new_jobs_summary

        # Get recently scraped jobs for the notification
        recent = db.get_active_jobs(limit=count)
        await send_new_jobs_summary(config.telegram, recent)

    if config.email.enabled:
        from scraper.notifications.email import send_new_jobs_email

        recent = db.get_active_jobs(limit=count)
        await send_new_jobs_email(config.email, recent)


def main() -> None:
    parser = argparse.ArgumentParser(description="CorkBoard Job Scraper")
    parser.add_argument(
        "command",
        choices=["scrape", "verify", "archive"],
        help="Which task to run",
    )
    args = parser.parse_args()

    config = Config()

    commands = {
        "scrape": run_scrape,
        "verify": run_verify,
        "archive": run_archive,
    }

    asyncio.run(commands[args.command](config))


if __name__ == "__main__":
    main()
