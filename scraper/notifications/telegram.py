"""Telegram notification sender for new job alerts."""

from __future__ import annotations

import logging
from typing import Any

from telegram import Bot

from scraper.config import TelegramConfig

logger = logging.getLogger(__name__)


async def send_new_jobs_summary(
    config: TelegramConfig, jobs: list[dict[str, Any]]
) -> None:
    """Send a Telegram message with new job listings."""
    if not config.enabled:
        logger.debug("Telegram not configured, skipping notification")
        return

    if not jobs:
        return

    bot = Bot(token=config.bot_token)

    header = f"🔔 *{len(jobs)} new job(s) found!*\n\n"
    lines: list[str] = []

    for job in jobs[:20]:  # Cap at 20 to avoid message length limits
        emoji = "🏨" if job.get("category") == "hospitality" else "🍷"
        salary = job.get("salary_text") or "Salary not listed"
        source = job.get("source", "unknown")
        title = _escape_md(job.get("title", "Unknown"))
        company = _escape_md(job.get("company", "Unknown"))

        lines.append(
            f"{emoji} *{title}*\n"
            f"   {company} · {salary}\n"
            f"   via {source} · [View]({job.get('source_url', '')})\n"
        )

    body = header + "\n".join(lines)

    if len(jobs) > 20:
        body += f"\n_\\.\\.\\. and {len(jobs) - 20} more on the dashboard_"

    try:
        await bot.send_message(
            chat_id=config.chat_id,
            text=body,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )
        logger.info("Sent Telegram notification for %d jobs", len(jobs))
    except Exception as exc:
        logger.error("Failed to send Telegram notification: %s", exc)


def _escape_md(text: str) -> str:
    """Escape MarkdownV2 special characters."""
    special = r"_*[]()~`>#+-=|{}.!"
    for char in special:
        text = text.replace(char, f"\\{char}")
    return text
