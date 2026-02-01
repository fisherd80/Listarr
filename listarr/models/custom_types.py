"""
Custom SQLAlchemy column types for the Listarr application.
"""
from datetime import timezone
from sqlalchemy.types import TypeDecorator, DateTime as SQLAlchemyDateTime


class TZDateTime(TypeDecorator):
    """
    A DateTime type that ensures timezone-aware datetime objects.

    SQLite doesn't properly support timezone-aware datetimes even with
    DateTime(timezone=True). This TypeDecorator ensures that all datetime
    values are stored as UTC and retrieved as timezone-aware datetime objects.
    """
    impl = SQLAlchemyDateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """
        Convert incoming datetime to UTC before storing.
        """
        if value is not None:
            if value.tzinfo is None:
                # If naive datetime, assume it's UTC
                value = value.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        """
        Ensure retrieved datetime is timezone-aware (UTC).
        """
        if value is not None and value.tzinfo is None:
            # SQLite returns naive datetimes, so we add UTC timezone
            value = value.replace(tzinfo=timezone.utc)
        return value
