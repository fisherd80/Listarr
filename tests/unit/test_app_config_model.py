from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from listarr import _ensure_app_config_row, db
from listarr.models.app_config_model import AppConfig, get_app_config, read_app_config

pytestmark = pytest.mark.unit


def _clear_app_config():
    db.session.query(AppConfig).delete()
    db.session.commit()


def test_get_app_config_creates_singleton_row(app):
    with app.app_context():
        _clear_app_config()

        cfg = get_app_config()

        assert cfg.id == 1
        assert cfg.timezone is None

        _clear_app_config()


def test_get_app_config_is_idempotent(app):
    with app.app_context():
        _clear_app_config()

        first = get_app_config()
        first.timezone = "Europe/London"
        db.session.commit()

        second = get_app_config()

        assert first.id == 1
        assert second.id == 1
        assert second.timezone == "Europe/London"
        assert AppConfig.query.count() == 1

        _clear_app_config()


def test_ensure_app_config_row_degrades_to_warning_on_operational_error(app):
    with app.app_context():
        boom = OperationalError("stmt", {}, Exception("database is locked"))
        with (
            patch.object(db.session, "get", side_effect=boom),
            patch.object(app.logger, "warning") as mock_warning,
        ):
            result = _ensure_app_config_row(app)

        assert result is None
        mock_warning.assert_called_once()


def test_read_app_config_returns_none_without_creating_a_row(app):
    """WR-01: the read-only accessor must not insert or commit when the row is absent."""
    with app.app_context():
        _clear_app_config()

        assert read_app_config() is None
        assert AppConfig.query.count() == 0


def test_read_app_config_does_not_commit_pending_session_state(app):
    """WR-01: resolving the timezone from a request/render path must not flush unrelated
    pending ORM state, which get_app_config()'s unconditional commit would do."""
    with app.app_context():
        _clear_app_config()
        db.session.add(AppConfig(id=1, timezone="Europe/London"))
        db.session.commit()

        cfg = read_app_config()
        cfg.timezone = "Asia/Tokyo"  # pending, uncommitted

        assert read_app_config().timezone == "Asia/Tokyo"
        db.session.rollback()
        assert read_app_config().timezone == "Europe/London", "the read path committed"

        _clear_app_config()


def test_read_app_config_does_not_autoflush_unrelated_pending_state(app):
    """WR-01: Session.get() autoflushes before the SELECT it emits when the row is not in
    the identity map. Unguarded, a function documented as never writing would push a
    route's half-finished ORM mutation to the DB simply by rendering a template."""
    from listarr.models.lists_model import List

    with app.app_context():
        _clear_app_config()
        db.session.add(AppConfig(id=1, timezone="Europe/London"))
        lst = List(
            name="before",
            target_service="RADARR",
            tmdb_list_type="popular_movies",
            filters_json={},
            is_active=True,
        )
        db.session.add(lst)
        db.session.commit()

        # Force the SELECT path: an identity-map hit would not autoflush at all. Done
        # before the mutation below, because this get() would autoflush it too.
        db.session.expunge(db.session.get(AppConfig, 1))

        lst.name = "half-finished"  # an unrelated, deliberately unflushed mutation
        assert read_app_config().timezone == "Europe/London"

        assert lst in db.session.dirty, "read_app_config() flushed unrelated pending state"

        db.session.rollback()
        db.session.delete(db.session.get(List, lst.id))
        db.session.commit()
        _clear_app_config()


def test_resolver_uses_the_read_only_accessor(app):
    """WR-01: _read_db_timezone_string must not go through the create-on-miss variant."""
    from listarr.utils import time_utils

    with app.app_context():
        _clear_app_config()

        assert time_utils._read_db_timezone_string() is None
        assert AppConfig.query.count() == 0
