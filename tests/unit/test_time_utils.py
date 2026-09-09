"""Unit tests for listarr/utils/time_utils.py - format_past_time()."""

import zoneinfo
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from listarr.utils.time_utils import format_past_time

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# 2026-01-15 15:00 UTC == 10:00 in America/New_York (UTC-5 in January).
FROZEN_NOW = datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc)
NEW_YORK = zoneinfo.ZoneInfo("America/New_York")


def utc_now():
    return datetime.now(timezone.utc)


class _FrozenClock:
    """Stand-in for the module's ``datetime`` symbol; only ``now()`` is used here."""

    def __init__(self, now):
        self._now = now

    def now(self, tz=None):
        return self._now.astimezone(tz) if tz else self._now


def past(now=FROZEN_NOW, app_tz=timezone.utc):
    """Patch the module clock and the resolved application timezone together."""
    return (
        patch("listarr.utils.time_utils.datetime", _FrozenClock(now)),
        patch("listarr.utils.time_utils.get_app_timezone", return_value=app_tz),
    )


# ---------------------------------------------------------------------------
# format_past_time() - None input
# ---------------------------------------------------------------------------


class TestFormatPastTimeNone:
    """format_past_time(None) returns None."""

    def test_none_returns_none(self):
        assert format_past_time(None) is None


# ---------------------------------------------------------------------------
# format_past_time() - "Today" (same calendar day in the app timezone)
# ---------------------------------------------------------------------------


class TestFormatPastTimeToday:
    """format_past_time returns 'Today' for the same calendar day in the app timezone."""

    def test_30_seconds_ago_returns_today(self):
        clock, tz = past()
        with clock, tz:
            assert format_past_time(FROZEN_NOW - timedelta(seconds=30)) == "Today"

    def test_5_minutes_ago_returns_today(self):
        clock, tz = past()
        with clock, tz:
            assert format_past_time(FROZEN_NOW - timedelta(minutes=5)) == "Today"

    def test_earlier_same_calendar_day_returns_today(self):
        clock, tz = past()
        with clock, tz:
            assert format_past_time(datetime(2026, 1, 15, 0, 1, tzinfo=timezone.utc)) == "Today"

    def test_same_calendar_day_in_app_timezone_returns_today(self):
        """20 hours elapsed but still the same NY calendar date."""
        clock, tz = past(app_tz=NEW_YORK)
        with clock, tz:
            # 2026-01-15 05:30 UTC == 2026-01-15 00:30 in New York (same NY day as now).
            assert format_past_time(datetime(2026, 1, 15, 5, 30, tzinfo=timezone.utc)) == "Today"


# ---------------------------------------------------------------------------
# format_past_time() - "Yesterday" (previous calendar day)
# ---------------------------------------------------------------------------


class TestFormatPastTimeYesterday:
    """format_past_time returns 'Yesterday' for the previous calendar day."""

    def test_exactly_1_day_ago_returns_yesterday(self):
        clock, tz = past()
        with clock, tz:
            assert format_past_time(FROZEN_NOW - timedelta(days=1)) == "Yesterday"

    def test_previous_calendar_day_returns_yesterday(self):
        clock, tz = past()
        with clock, tz:
            assert format_past_time(datetime(2026, 1, 14, 23, 59, tzinfo=timezone.utc)) == "Yesterday"

    def test_under_24h_but_previous_app_timezone_day_returns_yesterday(self):
        """WR-05 regression: 14 hours elapsed, but yesterday's date in New York.

        The elapsed-seconds implementation rendered this as 'Today' while the
        app-timezone tooltip beside it showed yesterday's date.
        """
        clock, tz = past(app_tz=NEW_YORK)
        with clock, tz:
            # 2026-01-15 01:00 UTC == 2026-01-14 20:00 in New York.
            assert format_past_time(datetime(2026, 1, 15, 1, 0, tzinfo=timezone.utc)) == "Yesterday"


# ---------------------------------------------------------------------------
# format_past_time() - "N days ago"
# ---------------------------------------------------------------------------


class TestFormatPastTimeDaysAgo:
    """format_past_time returns 'N days ago' for 2+ calendar days."""

    @pytest.mark.parametrize("days", [2, 3, 7, 30])
    def test_n_days_ago(self, days):
        clock, tz = past()
        with clock, tz:
            assert format_past_time(FROZEN_NOW - timedelta(days=days)) == f"{days} days ago"

    def test_calendar_boundary_counts_days_not_elapsed_hours(self):
        clock, tz = past(app_tz=NEW_YORK)
        with clock, tz:
            # 2026-01-14 02:00 UTC == 2026-01-13 21:00 New York -> 2 NY days back.
            assert format_past_time(datetime(2026, 1, 14, 2, 0, tzinfo=timezone.utc)) == "2 days ago"


# ---------------------------------------------------------------------------
# format_past_time() - future datetime returns "unknown"
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
# format_past_time() - naive datetime treated as UTC
# ---------------------------------------------------------------------------


class TestFormatPastTimeNaive:
    """format_past_time treats naive datetimes as UTC."""

    def test_naive_datetime_30_seconds_ago_returns_today(self):
        clock, tz = past()
        with clock, tz:
            dt = (FROZEN_NOW - timedelta(seconds=30)).replace(tzinfo=None)
            assert dt.tzinfo is None  # confirm it's naive
            assert format_past_time(dt) == "Today"

    def test_naive_datetime_2_days_ago_returns_2_days_ago(self):
        clock, tz = past()
        with clock, tz:
            dt = (FROZEN_NOW - timedelta(days=2)).replace(tzinfo=None)
            assert dt.tzinfo is None
            assert format_past_time(dt) == "2 days ago"


# ---------------------------------------------------------------------------
# format_past_time() - degrades without raising
# ---------------------------------------------------------------------------


class TestFormatPastTimeErrors:
    def test_unresolvable_timezone_does_not_raise(self):
        clock, _ = past()
        with clock, patch("listarr.utils.time_utils.get_app_timezone", side_effect=ValueError("boom")):
            assert format_past_time(FROZEN_NOW - timedelta(days=1)) == "unknown"
