"""Unit tests for listarr/utils/time_utils.py — format_past_time()."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from listarr.utils.time_utils import format_past_time

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utc_now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# format_past_time() — None input
# ---------------------------------------------------------------------------


class TestFormatPastTimeNone:
    """format_past_time(None) returns None."""

    def test_none_returns_none(self):
        assert format_past_time(None) is None


# ---------------------------------------------------------------------------
# format_past_time() — "Today" (0 days ago)
# ---------------------------------------------------------------------------


class TestFormatPastTimeToday:
    """format_past_time returns 'Today' for datetimes within the same calendar day."""

    def test_30_seconds_ago_returns_today(self):
        dt = utc_now() - timedelta(seconds=30)
        assert format_past_time(dt) == "Today"

    def test_5_minutes_ago_returns_today(self):
        dt = utc_now() - timedelta(minutes=5)
        assert format_past_time(dt) == "Today"

    def test_23_hours_ago_returns_today(self):
        dt = utc_now() - timedelta(hours=23, minutes=59)
        assert format_past_time(dt) == "Today"


# ---------------------------------------------------------------------------
# format_past_time() — "Yesterday" (exactly 1 day ago)
# ---------------------------------------------------------------------------


class TestFormatPastTimeYesterday:
    """format_past_time returns 'Yesterday' for datetimes 24–47 hours ago."""

    def test_25_hours_ago_returns_yesterday(self):
        dt = utc_now() - timedelta(hours=25)
        assert format_past_time(dt) == "Yesterday"

    def test_exactly_1_day_ago_returns_yesterday(self):
        dt = utc_now() - timedelta(days=1)
        assert format_past_time(dt) == "Yesterday"

    def test_47_hours_ago_returns_yesterday(self):
        dt = utc_now() - timedelta(hours=47, minutes=59)
        assert format_past_time(dt) == "Yesterday"


# ---------------------------------------------------------------------------
# format_past_time() — "N days ago"
# ---------------------------------------------------------------------------


class TestFormatPastTimeDaysAgo:
    """format_past_time returns 'N days ago' for datetimes 2+ days ago."""

    def test_3_days_ago_returns_3_days_ago(self):
        dt = utc_now() - timedelta(days=3)
        assert format_past_time(dt) == "3 days ago"

    def test_7_days_ago_returns_7_days_ago(self):
        dt = utc_now() - timedelta(days=7)
        assert format_past_time(dt) == "7 days ago"

    def test_30_days_ago_returns_30_days_ago(self):
        dt = utc_now() - timedelta(days=30)
        assert format_past_time(dt) == "30 days ago"


# ---------------------------------------------------------------------------
# format_past_time() — future datetime returns "unknown"
# ---------------------------------------------------------------------------


class TestFormatPastTimeFuture:
    """format_past_time returns 'unknown' for future datetimes."""

    def test_future_datetime_returns_unknown(self):
        dt = utc_now() + timedelta(hours=1)
        assert format_past_time(dt) == "unknown"

    def test_far_future_datetime_returns_unknown(self):
        dt = utc_now() + timedelta(days=365)
        assert format_past_time(dt) == "unknown"


# ---------------------------------------------------------------------------
# format_past_time() — naive datetime treated as UTC
# ---------------------------------------------------------------------------


class TestFormatPastTimeNaive:
    """format_past_time treats naive datetimes as UTC."""

    def test_naive_datetime_30_seconds_ago_returns_today(self):
        dt = datetime.utcnow() - timedelta(seconds=30)
        assert dt.tzinfo is None  # confirm it's naive
        assert format_past_time(dt) == "Today"

    def test_naive_datetime_2_days_ago_returns_2_days_ago(self):
        dt = datetime.utcnow() - timedelta(days=2)
        assert dt.tzinfo is None
        assert format_past_time(dt) == "2 days ago"
