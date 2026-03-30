"""Filter jobs to London-based locations only."""

from __future__ import annotations

import re

from scraper.config import LONDON_POSTCODE_PREFIXES

# Match London postcodes like EC1A, WC2H, SW1A, SE1, N1, E14, W1
_POSTCODE_RE = re.compile(
    r"\b(" + "|".join(LONDON_POSTCODE_PREFIXES) + r")\d{1,2}[A-Z]?\b",
    re.IGNORECASE,
)


def is_london_based(location: str) -> bool:
    """Return True if the location string indicates London."""
    if not location:
        return False

    text = location.lower()

    if "london" in text:
        return True

    if _POSTCODE_RE.search(location):
        return True

    return False
