"""Tests for temporal normalization utility."""

from datetime import date

from ontograph.temporal import normalize_temporal


def test_iso_date_passthrough():
    """Already-ISO dates should pass through unchanged."""
    assert normalize_temporal("2026-07-15") == "2026-07-15"
    assert normalize_temporal("2026-01-01") == "2026-01-01"


def test_year_quarter_to_date():
    """'2026-Q3' or 'Q3 2026' → first day of that quarter."""
    assert normalize_temporal("2026-Q1") == "2026-01-01"
    assert normalize_temporal("2026-Q2") == "2026-04-01"
    assert normalize_temporal("2026-Q3") == "2026-07-01"
    assert normalize_temporal("2026-Q4") == "2026-10-01"
    assert normalize_temporal("Q3 2026") == "2026-07-01"
    assert normalize_temporal("Q1 2027") == "2027-01-01"


def test_by_month_year():
    """'by July 2026' → last day of that month."""
    assert normalize_temporal("by July 2026") == "2026-07-31"
    assert normalize_temporal("by February 2026") == "2026-02-28"
    assert normalize_temporal("by May 2026") == "2026-05-31"
    assert normalize_temporal("by December 2026") == "2026-12-31"


def test_month_year_without_by():
    """'July 2026' → first day of that month."""
    assert normalize_temporal("July 2026") == "2026-07-01"
    assert normalize_temporal("January 2027") == "2027-01-01"
    assert normalize_temporal("March 2026") == "2026-03-01"


def test_next_quarter_with_reference():
    """'next quarter' relative to a reference date."""
    ref = date(2026, 3, 19)  # Q1 → next is Q2
    assert normalize_temporal("next quarter", reference_date=ref) == "2026-04-01"

    ref_q3 = date(2026, 8, 1)  # Q3 → next is Q4
    assert normalize_temporal("next quarter", reference_date=ref_q3) == "2026-10-01"

    ref_q4 = date(2026, 11, 15)  # Q4 → next is Q1 of next year
    assert normalize_temporal("next quarter", reference_date=ref_q4) == "2027-01-01"


def test_this_quarter_with_reference():
    """'this quarter' relative to a reference date."""
    ref = date(2026, 3, 19)  # Q1
    assert normalize_temporal("this quarter", reference_date=ref) == "2026-01-01"

    ref_q2 = date(2026, 5, 10)  # Q2
    assert normalize_temporal("this quarter", reference_date=ref_q2) == "2026-04-01"


def test_this_week_with_reference():
    """'this week' → Monday of current week."""
    ref = date(2026, 3, 19)  # Thursday
    assert normalize_temporal("this week", reference_date=ref) == "2026-03-16"


def test_next_week_with_reference():
    """'next week' → Monday of following week."""
    ref = date(2026, 3, 19)  # Thursday
    assert normalize_temporal("next week", reference_date=ref) == "2026-03-23"


def test_next_month_with_reference():
    """'next month' → first day of following month."""
    ref = date(2026, 3, 19)
    assert normalize_temporal("next month", reference_date=ref) == "2026-04-01"

    ref_dec = date(2026, 12, 15)
    assert normalize_temporal("next month", reference_date=ref_dec) == "2027-01-01"


def test_this_month_with_reference():
    """'this month' → first day of current month."""
    ref = date(2026, 3, 19)
    assert normalize_temporal("this month", reference_date=ref) == "2026-03-01"


def test_unparseable_returns_original():
    """Strings that can't be parsed return the original string."""
    assert normalize_temporal("sometime soon") == "sometime soon"
    assert normalize_temporal("whenever") == "whenever"
    assert normalize_temporal("ASAP") == "ASAP"
    assert normalize_temporal("") == ""


def test_default_reference_date_is_today():
    """When no reference_date is given, relative terms use today."""
    today = date.today()
    # "this month" should always resolve to first of current month
    result = normalize_temporal("this month")
    expected = today.replace(day=1).isoformat()
    assert result == expected


def test_case_insensitive():
    """Temporal parsing should be case-insensitive."""
    assert normalize_temporal("BY JULY 2026") == "2026-07-31"
    assert normalize_temporal("q3 2026") == "2026-07-01"
    assert normalize_temporal("Next Quarter", reference_date=date(2026, 3, 19)) == "2026-04-01"
