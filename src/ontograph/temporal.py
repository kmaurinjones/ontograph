"""Temporal normalization: convert relative time references to ISO dates.

Handles expressions like "next quarter", "by July 2026", "Q3 2026", "this week"
and normalizes them to ISO date strings given a reference date. Any consumer
of ontograph benefits from consistent temporal representation.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

# Month name → number mapping
_MONTH_MAP: dict[str, int] = {
    name.lower(): num for num, name in enumerate(calendar.month_name) if num
}
# Also add abbreviations
_MONTH_MAP.update(
    {name.lower(): num for num, name in enumerate(calendar.month_abbr) if num}
)

# Quarter → first month mapping
_QUARTER_START: dict[int, int] = {1: 1, 2: 4, 3: 7, 4: 10}


def _current_quarter(d: date) -> int:
    """Return the quarter number (1-4) for a date."""
    return (d.month - 1) // 3 + 1


def _last_day_of_month(year: int, month: int) -> date:
    """Return the last day of the given month."""
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, last_day)


def normalize_temporal(text: str, reference_date: date | None = None) -> str:
    """Normalize a temporal expression to an ISO date string.

    Args:
        text: The temporal expression to normalize.
        reference_date: Reference date for relative expressions. Defaults to today.

    Returns:
        ISO date string (YYYY-MM-DD) if parseable, otherwise the original string.
    """
    if not text:
        return text

    ref = reference_date or date.today()
    t = text.strip()
    t_lower = t.lower()

    # Already an ISO date — pass through
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        return t

    # Year-Quarter: "2026-Q3" or "Q3 2026"
    m = re.fullmatch(r"(\d{4})-q(\d)", t_lower)
    if m:
        year, q = int(m.group(1)), int(m.group(2))
        return date(year, _QUARTER_START[q], 1).isoformat()

    m = re.fullmatch(r"q(\d)\s+(\d{4})", t_lower)
    if m:
        q, year = int(m.group(1)), int(m.group(2))
        return date(year, _QUARTER_START[q], 1).isoformat()

    # "by <Month> <Year>" → last day of that month
    month_pattern = "|".join(_MONTH_MAP.keys())
    m = re.fullmatch(rf"by\s+({month_pattern})\s+(\d{{4}})", t_lower)
    if m:
        month_num = _MONTH_MAP[m.group(1)]
        year = int(m.group(2))
        return _last_day_of_month(year, month_num).isoformat()

    # "<Month> <Year>" → first day of that month
    m = re.fullmatch(rf"({month_pattern})\s+(\d{{4}})", t_lower)
    if m:
        month_num = _MONTH_MAP[m.group(1)]
        year = int(m.group(2))
        return date(year, month_num, 1).isoformat()

    # "next quarter"
    if t_lower == "next quarter":
        q = _current_quarter(ref)
        if q == 4:
            return date(ref.year + 1, 1, 1).isoformat()
        return date(ref.year, _QUARTER_START[q + 1], 1).isoformat()

    # "this quarter"
    if t_lower == "this quarter":
        q = _current_quarter(ref)
        return date(ref.year, _QUARTER_START[q], 1).isoformat()

    # "this week" → Monday of current week
    if t_lower == "this week":
        monday = ref - timedelta(days=ref.weekday())
        return monday.isoformat()

    # "next week" → Monday of following week
    if t_lower == "next week":
        days_until_next_monday = 7 - ref.weekday()
        return (ref + timedelta(days=days_until_next_monday)).isoformat()

    # "next month"
    if t_lower == "next month":
        if ref.month == 12:
            return date(ref.year + 1, 1, 1).isoformat()
        return date(ref.year, ref.month + 1, 1).isoformat()

    # "this month"
    if t_lower == "this month":
        return ref.replace(day=1).isoformat()

    # Unparseable — return original
    return text
