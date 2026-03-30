"""CorkBoard scraper configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


@dataclass(frozen=True)
class SupabaseConfig:
    url: str = os.environ.get("SUPABASE_URL", "")
    service_key: str = os.environ.get("SUPABASE_SERVICE_KEY", "")


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id: str = os.environ.get("TELEGRAM_CHAT_ID", "")

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)


@dataclass(frozen=True)
class EmailConfig:
    resend_api_key: str = os.environ.get("RESEND_API_KEY", "")
    recipient: str = os.environ.get("NOTIFICATION_EMAIL", "")

    @property
    def enabled(self) -> bool:
        return bool(self.resend_api_key and self.recipient)


HOSPITALITY_QUERIES: list[str] = [
    "hospitality manager london",
    "hotel manager london",
    "restaurant manager london",
    "front of house manager london",
    "food and beverage manager london",
    "events manager hospitality london",
    "general manager hospitality london",
    "assistant manager hospitality london",
]

WINE_QUERIES: list[str] = [
    "wine manager london",
    "sommelier london",
    "wine buyer london",
    "wine sales london",
    "wine merchant london",
    "head sommelier london",
    "wine bar manager london",
    "wine consultant london",
    "cellar manager london",
]

SEARCH_QUERIES: dict[str, list[str]] = {
    "hospitality": HOSPITALITY_QUERIES,
    "wine": WINE_QUERIES,
}

# London postcode prefixes for location filtering
LONDON_POSTCODE_PREFIXES: list[str] = [
    "EC", "WC", "SW", "SE", "NW", "NE", "N", "E", "W",
]

USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

REQUEST_HEADERS: dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

MAX_PAGES_PER_QUERY: int = 5
REQUEST_DELAY_MIN: float = 2.0
REQUEST_DELAY_MAX: float = 3.0
VERIFICATION_DELAY: float = 1.0
SOURCE_STAGGER_MINUTES: int = 5
ARCHIVE_AFTER_DAYS: int = 14
CONSECUTIVE_FAILURES_ALERT: int = 3


@dataclass(frozen=True)
class Config:
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
