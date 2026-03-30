"""Parse UK salary strings into min/max pence values."""

from __future__ import annotations

import re

_HOURLY_TO_ANNUAL = 2080  # 40 hrs/week × 52 weeks


def parse_salary(raw: str | None) -> tuple[int | None, int | None]:
    """Return (salary_min_pence, salary_max_pence) from a raw salary string.

    Examples handled:
      "£35,000 - £42,000"
      "£35k - £42k"
      "£35,000 - £42,000 per annum"
      "£18 - £22 per hour"
      "Up to £50,000"
      "£40,000 + bonus"
      "Competitive" → (None, None)
    """
    if not raw:
        return None, None

    text = raw.strip().lower()

    # Skip non-numeric salary indications
    if any(word in text for word in ("competitive", "negotiable", "dependent", "doe")):
        return None, None

    is_hourly = "hour" in text or "p/h" in text or "ph" in text

    # Find all monetary amounts
    amounts: list[int] = []
    for match in re.finditer(r"£\s*([\d,]+(?:\.\d+)?)\s*(k)?", text):
        num_str = match.group(1).replace(",", "")
        value = float(num_str)
        if match.group(2):  # "k" suffix
            value *= 1_000
        if is_hourly:
            value *= _HOURLY_TO_ANNUAL
        amounts.append(int(value * 100))  # convert to pence

    if not amounts:
        return None, None

    if len(amounts) == 1:
        if "up to" in text or "to" in text.split("£")[0]:
            return None, amounts[0]
        return amounts[0], amounts[0]

    return min(amounts), max(amounts)
