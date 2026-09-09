from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from listarr import _ensure_app_config_row, db
from listarr.models.app_config_model import AppConfig, get_app_config

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
