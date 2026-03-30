"""Email notification sender using Resend."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from scraper.config import EmailConfig

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_new_jobs_email(
    config: EmailConfig, jobs: list[dict[str, Any]]
) -> None:
    """Send an HTML email digest of new job listings via Resend."""
    if not config.enabled:
        logger.debug("Email not configured, skipping notification")
        return

    if not jobs:
        return

    html = _build_html(jobs)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {config.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "CorkBoard <noreply@corkboard.app>",
                    "to": [config.recipient],
                    "subject": f"🔔 {len(jobs)} new job(s) found — CorkBoard",
                    "html": html,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            logger.info("Sent email notification for %d jobs", len(jobs))
        except Exception as exc:
            logger.error("Failed to send email notification: %s", exc)


def _build_html(jobs: list[dict[str, Any]]) -> str:
    cards = ""
    for job in jobs[:30]:
        emoji = "🏨" if job.get("category") == "hospitality" else "🍷"
        salary = job.get("salary_text") or "Salary not listed"
        source = job.get("source", "unknown")
        url = _safe_url(job.get("source_url", "#"))

        cards += f"""
        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:12px;">
            <div style="font-size:16px;font-weight:600;">{emoji} {_esc(job.get('title', 'Unknown'))}</div>
            <div style="color:#6b7280;margin-top:4px;">
                {_esc(job.get('company', 'Unknown'))} &middot; {_esc(job.get('location', ''))}
            </div>
            <div style="margin-top:4px;">{_esc(salary)} &middot; via {_esc(source)}</div>
            <a href="{url}" style="display:inline-block;margin-top:8px;padding:8px 16px;background:#2563eb;color:white;border-radius:6px;text-decoration:none;font-size:14px;">
                View &amp; Apply
            </a>
        </div>
        """

    return f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <h2 style="margin-bottom:4px;">🔔 {len(jobs)} new job(s) found</h2>
        <p style="color:#6b7280;margin-top:0;">Here are the latest listings from CorkBoard</p>
        {cards}
        {"<p style='color:#9ca3af;'>... and " + str(len(jobs) - 30) + " more on the dashboard</p>" if len(jobs) > 30 else ""}
    </div>
    """


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _safe_url(url: str) -> str:
    """Sanitise URL for use in HTML href — only allow http(s) scheme."""
    if url.startswith(("http://", "https://")):
        return _esc(url)
    return "#"
