"""Idempotency + failure-posture coverage for the startup DDL helper.

`_ensure_sonarr_monitor_mode_columns` adds `sonarr_monitor_mode` to the `lists` and
`media_import_settings` tables of pre-v2.2 databases. SQLite `ALTER TABLE ADD COLUMN`
has no `IF NOT EXISTS`, so the helper guards each `ALTER` with `PRAGMA table_info`.
"""

from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from listarr import _ensure_sonarr_monitor_mode_columns, db

pytestmark = pytest.mark.database


def _column_names(table):
    rows = db.session.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return [row[1] for row in rows]


def _make_columnless():
    """Return both tables to their pre-v2.2 (column-less) shape."""
    for table in ("lists", "media_import_settings"):
        if "sonarr_monitor_mode" in _column_names(table):
            db.session.execute(text(f"ALTER TABLE {table} DROP COLUMN sonarr_monitor_mode"))
    db.session.commit()


@pytest.fixture
def columnless_db(app):
    """A database whose `lists` / `media_import_settings` tables lack
    `sonarr_monitor_mode`, each carrying one pre-existing row."""
    with app.app_context():
        _make_columnless()
        db.session.execute(
            text(
                "INSERT INTO lists (name, target_service, tmdb_list_type, filters_json) "
                "VALUES ('pre-upgrade', 'sonarr', 'popular', '{}')"
            )
        )
        db.session.execute(
            text(
                "INSERT INTO media_import_settings (service, root_folder, quality_profile_id) "
                "VALUES ('SONARR', '/tv', 1)"
            )
        )
        db.session.commit()
        try:
            yield app
        finally:
            # Restore the schema for subsequent tests regardless of outcome.
            _ensure_sonarr_monitor_mode_columns(app)


def test_helper_adds_column_to_both_tables(columnless_db):
    app = columnless_db
    with app.app_context():
        assert "sonarr_monitor_mode" not in _column_names("lists")
        assert "sonarr_monitor_mode" not in _column_names("media_import_settings")

        _ensure_sonarr_monitor_mode_columns(app)

        assert "sonarr_monitor_mode" in _column_names("lists")
        assert "sonarr_monitor_mode" in _column_names("media_import_settings")


def test_second_call_is_a_noop(columnless_db):
    app = columnless_db
    with app.app_context():
        _ensure_sonarr_monitor_mode_columns(app)
        db.session.execute(text("UPDATE lists SET sonarr_monitor_mode = 'pilot'"))
        db.session.commit()

        # Second boot: no exception, no duplicate column, value untouched.
        _ensure_sonarr_monitor_mode_columns(app)

        assert _column_names("lists").count("sonarr_monitor_mode") == 1
        assert _column_names("media_import_settings").count("sonarr_monitor_mode") == 1
        value = db.session.execute(text("SELECT sonarr_monitor_mode FROM lists")).scalar()
        assert value == "pilot"


def test_existing_import_settings_row_backfills_to_all(columnless_db):
    app = columnless_db
    with app.app_context():
        _ensure_sonarr_monitor_mode_columns(app)
        value = db.session.execute(text("SELECT sonarr_monitor_mode FROM media_import_settings")).scalar()
        assert value == "all"


def test_existing_lists_row_reads_null(columnless_db):
    app = columnless_db
    with app.app_context():
        _ensure_sonarr_monitor_mode_columns(app)
        value = db.session.execute(text("SELECT sonarr_monitor_mode FROM lists")).scalar()
        assert value is None


def test_operational_error_degrades_to_warning(app):
    with app.app_context():
        boom = OperationalError("stmt", {}, Exception("database is locked"))
        with (
            patch.object(db.session, "execute", side_effect=boom),
            patch.object(app.logger, "warning") as mock_warning,
        ):
            result = _ensure_sonarr_monitor_mode_columns(app)

        assert result is None
        mock_warning.assert_called_once()
