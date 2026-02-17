"""Time formatting utilities."""

from datetime import datetime, timezone


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
