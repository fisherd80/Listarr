"""Time formatting and application timezone utilities."""

import logging
import os
import threading
import time
import zoneinfo
from datetime import datetime, timezone

from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)

_TZ_MEMO_TTL = 5.0
_UNSET = object()
_tz_memo_lock = threading.Lock()
# "gen" is bumped by every invalidation so a reader that was already mid-DB-read
# cannot store its pre-save record back over a fresh invalidation (WR-08).
_tz_memo = {"record": _UNSET, "expires": 0.0, "gen": 0}


def tz_key(tz) -> str:
    """Return a stable string key for a timezone or timezone name."""
    if tz is timezone.utc or str(tz) == "UTC":
        return "UTC"
    return str(tz)


def coerce_zone(name):
    """Resolve a timezone name to tzinfo, returning None for invalid or unknown keys.

    This is the single security-relevant timezone validation point: ZoneInfo itself
    rejects absolute paths, ".." traversal and embedded null bytes. Callers that only
    need a yes/no answer (the settings route) must go through here rather than keep a
    second copy of the same try/except (IN-01).
    """
    if not isinstance(name, str):
        return None
    if name == "UTC":
        return timezone.utc
    try:
        return zoneinfo.ZoneInfo(name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError):
        return None


# Backwards-compatible private alias for existing internal callers.
_coerce_zone = coerce_zone


def _read_db_timezone_string():
    """Read AppConfig.timezone without raising; None means use the system fallback."""
    try:
        # read_app_config never writes: this resolver runs inside the request session
        # (context processor) and on the scheduler poll thread.
        from listarr.models.app_config_model import read_app_config

        cfg = read_app_config()
        return cfg.timezone if cfg else None
    except (RuntimeError, OperationalError, SQLAlchemyError):
        return None


def _build_timezone_record(raw, warn=True):
    zone = coerce_zone(raw) if raw else None
    warned = False
    if warn and raw and zone is None:
        logger.warning("Configured timezone %r could not be loaded; falling back", raw)
        warned = True
    return {"raw": raw, "zone": zone, "warned": warned}


def _get_timezone_record(use_cache=True):
    """Return the memoized DB timezone record, caching resolved and failed outcomes."""
    if not use_cache:
        return _build_timezone_record(_read_db_timezone_string(), warn=False)

    now = time.monotonic()
    with _tz_memo_lock:
        record = _tz_memo["record"]
        if record is not _UNSET and now < _tz_memo["expires"]:
            return record
        gen = _tz_memo["gen"]

    record = _build_timezone_record(_read_db_timezone_string())
    with _tz_memo_lock:
        if _tz_memo["gen"] == gen:
            # Nobody invalidated while the DB read was in flight.
            _tz_memo["record"] = record
            _tz_memo["expires"] = time.monotonic() + _TZ_MEMO_TTL
    return record


def resolve_db_timezone_string(use_cache=True):
    """Return the stored DB timezone string or None, using the short-TTL memo by default."""
    return _get_timezone_record(use_cache)["raw"]


def invalidate_app_timezone_memo() -> None:
    """Clear the in-process application timezone memo after a local settings save."""
    with _tz_memo_lock:
        _tz_memo["record"] = _UNSET
        _tz_memo["expires"] = 0.0
        _tz_memo["gen"] += 1


def get_app_timezone_fallback_name() -> str:
    """Return the resolvable TZ environment fallback name, or UTC."""
    tz_name = os.environ.get("TZ", "UTC")
    return tz_name if coerce_zone(tz_name) is not None else "UTC"


def _zone_from_record(record):
    """Apply the DB -> TZ env -> UTC fallback chain to an already-read record."""
    if record["zone"] is not None:
        return record["zone"]

    fallback = coerce_zone(os.environ.get("TZ", "UTC"))
    if fallback is not None:
        return fallback

    return timezone.utc


def get_app_timezone():
    """Resolve the application timezone as DB AppConfig.timezone -> TZ env -> UTC."""
    return _zone_from_record(_get_timezone_record())


def get_app_timezone_name() -> str:
    """Return the canonical string name for the resolved application timezone."""
    return tz_key(get_app_timezone())


def get_app_timezone_state() -> dict:
    """Return stored, resolved, fallback and unresolvable state for the General tab."""
    # WR-08: every field is derived from one record, so the tab can never render a
    # self-contradicting pair when the memo expires mid-call.
    record = _get_timezone_record()
    return {
        "configured": record["raw"],
        "resolved": tz_key(_zone_from_record(record)),
        "fallback": get_app_timezone_fallback_name(),
        "unresolvable": bool(record["raw"] and record["zone"] is None),
    }


def format_relative_time(dt):
    """
    Format a datetime as a relative time string.

    Args:
        dt: datetime object (timezone-aware)

    Returns:
        str: Relative time string (e.g., "in 2 hours", "in 5 minutes")
    """
    if not dt:
        return "unknown"

    try:
        now = datetime.now(timezone.utc)
        # Ensure dt is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        diff = dt - now
        total_seconds = diff.total_seconds()

        if total_seconds < 0:
            return "overdue"

        # Convert to appropriate unit
        if total_seconds < 60:
            return "in less than a minute"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = int(total_seconds / 60)
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        elif total_seconds < 86400:  # Less than 1 day
            hours = int(total_seconds / 3600)
            return f"in {hours} hour{'s' if hours != 1 else ''}"
        else:  # 1 day or more
            days = int(total_seconds / 86400)
            return f"in {days} day{'s' if days != 1 else ''}"

    except (ValueError, TypeError, OverflowError):
        return "unknown"


def format_past_time(dt):
    """
    Format a datetime as a backward-looking relative time string.

    Day labels are calendar-based in the application timezone: "Today" means the same
    calendar date as now in that zone, not "less than 24 hours ago" (WR-05). This keeps
    the label consistent with the app-timezone tooltip rendered beside it.

    Args:
        dt: datetime object (timezone-aware or naive; naive treated as UTC)

    Returns:
        str or None: "Today", "Yesterday", "N days ago", "unknown", or None if dt is None
    """
    if dt is None:
        return None

    try:
        now = datetime.now(timezone.utc)
        # Ensure dt is timezone-aware; treat naive as UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        if (now - dt).total_seconds() < 0:
            # Future timestamp
            return "unknown"

        app_tz = get_app_timezone()
        days = (now.astimezone(app_tz).date() - dt.astimezone(app_tz).date()).days

        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        else:
            return f"{days} days ago"

    except (ValueError, TypeError, OverflowError):
        return "unknown"
