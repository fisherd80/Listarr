from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from listarr import db
from listarr.models.custom_types import TZDateTime


class AppConfig(db.Model):
    """Single-row global app config table pinned to id=1.

    The table is created by db.create_all(); there is no Alembic migration and
    no ALTER/PRAGMA startup helper for it. A NULL timezone means "System default".
    """

    __tablename__ = "app_config"

    id = db.Column(db.Integer, primary_key=True)
    timezone = db.Column(db.String(64), nullable=True)
    created_at = db.Column(TZDateTime, default=lambda: datetime.now(timezone.utc))


def read_app_config():
    """Return the singleton app config row without ever writing.

    Read-only paths (the timezone resolver, which runs on every template render and
    on the scheduler poll) must use this. get_app_config() commits when the row is
    absent, which would also flush unrelated pending ORM state on the request session.
    """
    # WR-01: Session.get() emits a SELECT whenever the row is not already in the
    # identity map, and SQLAlchemy autoflushes before that SELECT. Without this guard a
    # function documented as never writing would flush a route's half-finished ORM
    # mutations the moment it rendered a template.
    with db.session.no_autoflush:
        return db.session.get(AppConfig, 1)


def get_app_config():
    """Return the singleton app config row, creating it if absent.

    IntegrityError is handled for first-boot races between workers. OperationalError
    is intentionally left to callers so startup and resolver paths can apply their
    own fallback posture.

    WR-03: never returns None. Only a concurrent insert of id=1 makes the IntegrityError
    recoverable; any other constraint violation is re-raised so callers see an error they
    already handle, rather than an AttributeError on a None they were never told to expect.
    """
    cfg = db.session.get(AppConfig, 1)
    if cfg is not None:
        return cfg

    cfg = AppConfig(id=1, timezone=None)
    db.session.add(cfg)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        cfg = db.session.get(AppConfig, 1)
        if cfg is None:
            raise
    return cfg
