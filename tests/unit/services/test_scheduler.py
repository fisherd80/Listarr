"""
Tests for scheduler service pre-flight health check.

Tests cover:
- _run_scheduled_import() health check before job submission
- Service configuration validation
- API key validation and reachability checks
- Error handling for decrypt and validate operations
- get_next_run_time() fallback for non-scheduler workers
"""

import zoneinfo
from datetime import datetime, timezone, tzinfo
from unittest.mock import MagicMock, patch

import pytest
import requests
from sqlalchemy.exc import OperationalError

from listarr import db
from listarr.models.app_config_model import AppConfig, get_app_config
from listarr.services import scheduler as sched
from listarr.services.scheduler import (
    _get_scheduler_timezone,
    _run_scheduled_import,
    get_next_run_time,
    schedule_list,
    validate_cron_expression,
)
from listarr.utils import time_utils
from listarr.utils.time_utils import tz_key


def _set_app_timezone(value):
    cfg = get_app_config()
    cfg.timezone = value
    db.session.commit()
    time_utils.invalidate_app_timezone_memo()


class TestRunScheduledImportHealthCheck:
    """Tests for pre-flight health check in _run_scheduled_import."""

    @patch("listarr.services.scheduler.is_scheduler_paused")
    @patch("listarr.services.scheduler.submit_job")
    @patch("listarr.services.scheduler.List")
    @patch("listarr.services.scheduler.ServiceConfig")
    @patch("listarr.services.scheduler._app")
    def test_skips_when_service_not_configured(
        self,
        mock_app,
        mock_service_config_class,
        mock_list_class,
        mock_submit_job,
        mock_is_paused,
    ):
        """Scheduled import skips when target service is not configured."""
        # Setup app context
        mock_app.app_context.return_value.__enter__ = MagicMock()
        mock_app.app_context.return_value.__exit__ = MagicMock()

        # Setup scheduler not paused
        mock_is_paused.return_value = False

        # Setup list object with target service
        mock_list_obj = MagicMock()
        mock_list_obj.id = 1
        mock_list_obj.name = "Test List"
        mock_list_obj.target_service = "RADARR"
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        # Setup ServiceConfig.query.filter_by to return None (no config)
        mock_query = MagicMock()
        mock_query.first.return_value = None
        mock_service_config_class.query.filter_by.return_value = mock_query

        # Run scheduled import
        _run_scheduled_import(1)

        # Assert submit_job was NOT called
        mock_submit_job.assert_not_called()


class TestGetNextRunTimeFallback:
    """Tests for get_next_run_time() fallback in non-scheduler workers."""

    @patch("listarr.services.scheduler._scheduler", None)
    @patch("listarr.services.scheduler.List")
    def test_returns_none_when_list_not_found(self, mock_list_class):
        """Returns None when list doesn't exist in database."""
        # Setup List.query.get to return None
        mock_list_class.query.get.return_value = None

        result = get_next_run_time(999)

        assert result is None
        mock_list_class.query.get.assert_called_once_with(999)

    @patch("listarr.services.scheduler._scheduler", None)
    @patch("listarr.services.scheduler.List")
    def test_returns_none_when_no_schedule(self, mock_list_class):
        """Returns None when list has no cron schedule."""
        # Setup list without schedule
        mock_list_obj = MagicMock()
        mock_list_obj.schedule_cron = None
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        result = get_next_run_time(1)

        assert result is None

    @patch("listarr.services.scheduler._scheduler", None)
    @patch("listarr.services.scheduler.List")
    def test_returns_none_when_list_inactive(self, mock_list_class):
        """Returns None when list is inactive."""
        # Setup inactive list with schedule
        mock_list_obj = MagicMock()
        mock_list_obj.schedule_cron = "0 0 * * *"
        mock_list_obj.is_active = False
        mock_list_class.query.get.return_value = mock_list_obj

        result = get_next_run_time(1)

        assert result is None

    @patch("listarr.services.scheduler._scheduler", None)
    @patch("listarr.services.scheduler.List")
    def test_calculates_next_run_from_cron(self, mock_list_class):
        """Calculates next run time from cron expression when scheduler is None."""
        # Setup list with valid cron expression
        mock_list_obj = MagicMock()
        mock_list_obj.schedule_cron = "0 0 * * *"  # Daily at midnight
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        result = get_next_run_time(1)

        # Should return a datetime (not None)
        assert result is not None
        assert isinstance(result, datetime)
        # Should be timezone-aware
        assert result.tzinfo is not None
        # Should be in the future
        assert result > datetime.now(timezone.utc)

    @patch("listarr.services.scheduler._scheduler", None)
    @patch("listarr.services.scheduler.List")
    def test_returns_none_on_invalid_cron(self, mock_list_class):
        """Returns None when cron expression is invalid."""
        # Setup list with invalid cron
        mock_list_obj = MagicMock()
        mock_list_obj.schedule_cron = "invalid cron"
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        result = get_next_run_time(1)

        assert result is None

    @patch("listarr.services.scheduler._scheduler")
    def test_uses_apscheduler_when_available(self, mock_scheduler):
        """Uses APScheduler job when scheduler is initialized."""
        # Setup mock scheduler with job
        mock_job = MagicMock()
        mock_next_run = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_job.next_run_time = mock_next_run
        mock_scheduler.get_job.return_value = mock_job

        result = get_next_run_time(1)

        # Should use APScheduler path (not database fallback)
        assert result == mock_next_run
        mock_scheduler.get_job.assert_called_once_with("list_1")

    @patch("listarr.services.scheduler.is_scheduler_paused")
    @patch("listarr.services.scheduler.submit_job")
    @patch("listarr.services.scheduler.List")
    @patch("listarr.services.scheduler.ServiceConfig")
    @patch("listarr.services.scheduler._app")
    def test_skips_when_service_api_key_missing(
        self,
        mock_app,
        mock_service_config_class,
        mock_list_class,
        mock_submit_job,
        mock_is_paused,
    ):
        """Scheduled import skips when service API key is missing."""
        # Setup app context
        mock_app.app_context.return_value.__enter__ = MagicMock()
        mock_app.app_context.return_value.__exit__ = MagicMock()

        # Setup scheduler not paused
        mock_is_paused.return_value = False

        # Setup list object
        mock_list_obj = MagicMock()
        mock_list_obj.id = 1
        mock_list_obj.name = "Test List"
        mock_list_obj.target_service = "SONARR"
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        # Setup ServiceConfig with no API key
        mock_service_config = MagicMock()
        mock_service_config.api_key_encrypted = None
        mock_query = MagicMock()
        mock_query.first.return_value = mock_service_config
        mock_service_config_class.query.filter_by.return_value = mock_query

        # Run scheduled import
        _run_scheduled_import(1)

        # Assert submit_job was NOT called
        mock_submit_job.assert_not_called()

    @patch("listarr.services.scheduler.is_scheduler_paused")
    @patch("listarr.services.scheduler.is_list_running")
    @patch("listarr.services.scheduler.submit_job")
    @patch("listarr.services.scheduler.validate_api_key")
    @patch("listarr.services.scheduler.decrypt_data")
    @patch("listarr.services.scheduler.List")
    @patch("listarr.services.scheduler.ServiceConfig")
    @patch("listarr.services.scheduler._app")
    def test_skips_when_service_unreachable(
        self,
        mock_app,
        mock_service_config_class,
        mock_list_class,
        mock_decrypt,
        mock_validate,
        mock_submit_job,
        mock_is_running,
        mock_is_paused,
    ):
        """Scheduled import skips when service is unreachable."""
        # Setup app context
        mock_app.app_context.return_value.__enter__ = MagicMock()
        mock_app.app_context.return_value.__exit__ = MagicMock()

        # Setup scheduler not paused
        mock_is_paused.return_value = False

        # Setup list object
        mock_list_obj = MagicMock()
        mock_list_obj.id = 1
        mock_list_obj.name = "Test List"
        mock_list_obj.target_service = "RADARR"
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        # Setup ServiceConfig with valid encrypted key
        mock_service_config = MagicMock()
        mock_service_config.api_key_encrypted = "encrypted_key_data"
        mock_service_config.base_url = "http://radarr:7878"
        mock_query = MagicMock()
        mock_query.first.return_value = mock_service_config
        mock_service_config_class.query.filter_by.return_value = mock_query

        # Mock decrypt_data to return fake key
        mock_decrypt.return_value = "fake_api_key"

        # Mock validate_api_key to return False (unreachable)
        mock_validate.return_value = False

        # Run scheduled import
        _run_scheduled_import(1)

        # Assert decrypt_data was called
        mock_decrypt.assert_called_once_with("encrypted_key_data")

        # Assert validate_api_key was called
        mock_validate.assert_called_once_with("http://radarr:7878", "fake_api_key")

        # Assert submit_job was NOT called
        mock_submit_job.assert_not_called()

    @patch("listarr.services.scheduler.is_scheduler_paused")
    @patch("listarr.services.scheduler.is_list_running")
    @patch("listarr.services.scheduler.submit_job")
    @patch("listarr.services.scheduler.validate_api_key")
    @patch("listarr.services.scheduler.decrypt_data")
    @patch("listarr.services.scheduler.List")
    @patch("listarr.services.scheduler.ServiceConfig")
    @patch("listarr.services.scheduler._app")
    def test_proceeds_when_service_reachable(
        self,
        mock_app,
        mock_service_config_class,
        mock_list_class,
        mock_decrypt,
        mock_validate,
        mock_submit_job,
        mock_is_running,
        mock_is_paused,
    ):
        """Scheduled import proceeds when service is reachable."""
        # Setup app context
        mock_app.app_context.return_value.__enter__ = MagicMock()
        mock_app.app_context.return_value.__exit__ = MagicMock()

        # Setup scheduler not paused
        mock_is_paused.return_value = False

        # Setup list object
        mock_list_obj = MagicMock()
        mock_list_obj.id = 1
        mock_list_obj.name = "Test List"
        mock_list_obj.target_service = "RADARR"
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        # Setup ServiceConfig with valid encrypted key
        mock_service_config = MagicMock()
        mock_service_config.api_key_encrypted = "encrypted_key_data"
        mock_service_config.base_url = "http://radarr:7878"
        mock_query = MagicMock()
        mock_query.first.return_value = mock_service_config
        mock_service_config_class.query.filter_by.return_value = mock_query

        # Mock decrypt_data to return fake key
        mock_decrypt.return_value = "fake_api_key"

        # Mock validate_api_key to return True (reachable)
        mock_validate.return_value = True

        # Mock is_list_running to return False (not running)
        mock_is_running.return_value = False

        # Run scheduled import
        _run_scheduled_import(1)

        # Assert decrypt_data was called
        mock_decrypt.assert_called_once_with("encrypted_key_data")

        # Assert validate_api_key was called
        mock_validate.assert_called_once_with("http://radarr:7878", "fake_api_key")

        # Assert submit_job WAS called
        mock_submit_job.assert_called_once_with(1, "Test List", mock_app, triggered_by="scheduled")

    @patch("listarr.services.scheduler.is_scheduler_paused")
    @patch("listarr.services.scheduler.submit_job")
    @patch("listarr.services.scheduler.decrypt_data")
    @patch("listarr.services.scheduler.List")
    @patch("listarr.services.scheduler.ServiceConfig")
    @patch("listarr.services.scheduler._app")
    def test_skips_when_decrypt_fails(
        self,
        mock_app,
        mock_service_config_class,
        mock_list_class,
        mock_decrypt,
        mock_submit_job,
        mock_is_paused,
    ):
        """Scheduled import skips when decrypt_data raises exception."""
        # Setup app context
        mock_app.app_context.return_value.__enter__ = MagicMock()
        mock_app.app_context.return_value.__exit__ = MagicMock()

        # Setup scheduler not paused
        mock_is_paused.return_value = False

        # Setup list object
        mock_list_obj = MagicMock()
        mock_list_obj.id = 1
        mock_list_obj.name = "Test List"
        mock_list_obj.target_service = "RADARR"
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        # Setup ServiceConfig
        mock_service_config = MagicMock()
        mock_service_config.api_key_encrypted = "invalid_encrypted_data"
        mock_service_config.base_url = "http://radarr:7878"
        mock_query = MagicMock()
        mock_query.first.return_value = mock_service_config
        mock_service_config_class.query.filter_by.return_value = mock_query

        # Mock decrypt_data to raise ValueError
        mock_decrypt.side_effect = ValueError("Invalid token: cannot decrypt")

        # Run scheduled import - should not raise exception
        _run_scheduled_import(1)

        # Assert submit_job was NOT called
        mock_submit_job.assert_not_called()

    @patch("listarr.services.scheduler.is_scheduler_paused")
    @patch("listarr.services.scheduler.submit_job")
    @patch("listarr.services.scheduler.validate_api_key")
    @patch("listarr.services.scheduler.decrypt_data")
    @patch("listarr.services.scheduler.List")
    @patch("listarr.services.scheduler.ServiceConfig")
    @patch("listarr.services.scheduler._app")
    def test_skips_when_validate_raises_exception(
        self,
        mock_app,
        mock_service_config_class,
        mock_list_class,
        mock_decrypt,
        mock_validate,
        mock_submit_job,
        mock_is_paused,
    ):
        """Scheduled import skips when validate_api_key raises exception."""
        # Setup app context
        mock_app.app_context.return_value.__enter__ = MagicMock()
        mock_app.app_context.return_value.__exit__ = MagicMock()

        # Setup scheduler not paused
        mock_is_paused.return_value = False

        # Setup list object
        mock_list_obj = MagicMock()
        mock_list_obj.id = 1
        mock_list_obj.name = "Test List"
        mock_list_obj.target_service = "SONARR"
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        # Setup ServiceConfig
        mock_service_config = MagicMock()
        mock_service_config.api_key_encrypted = "encrypted_key_data"
        mock_service_config.base_url = "http://sonarr:8989"
        mock_query = MagicMock()
        mock_query.first.return_value = mock_service_config
        mock_service_config_class.query.filter_by.return_value = mock_query

        # Mock decrypt_data to return key
        mock_decrypt.return_value = "fake_api_key"

        # Mock validate_api_key to raise ConnectionError
        mock_validate.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # Run scheduled import - should not raise exception
        _run_scheduled_import(1)

        # Assert submit_job was NOT called
        mock_submit_job.assert_not_called()


class TestSchedulerTimezone:
    """Tests for timezone propagation fixes in scheduler.py (BUG-01)."""

    @patch("listarr.services.scheduler._scheduler")
    def test_get_scheduler_timezone_uses_live_scheduler(self, mock_scheduler):
        """_get_scheduler_timezone() returns scheduler timezone when scheduler is live."""
        # Setup mock scheduler timezone
        expected_tz = zoneinfo.ZoneInfo("America/New_York")
        mock_scheduler.timezone = expected_tz

        result = _get_scheduler_timezone()

        assert result == expected_tz

    @patch.dict("os.environ", {"TZ": "America/Chicago"})
    @patch("listarr.services.scheduler._scheduler", None)
    def test_get_scheduler_timezone_falls_back_to_env(self):
        """_get_scheduler_timezone() falls back to TZ env var when scheduler is unavailable."""
        result = _get_scheduler_timezone()

        assert result == zoneinfo.ZoneInfo("America/Chicago")

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.CronTrigger")
    @patch("listarr.services.scheduler._scheduler")
    def test_schedule_list_passes_scheduler_timezone_to_cron_trigger(
        self,
        mock_scheduler,
        mock_cron_trigger,
        mock_validate_expr,
    ):
        """schedule_list() passes scheduler timezone to CronTrigger.from_crontab()."""
        # Setup scheduler with configured timezone
        expected_tz = zoneinfo.ZoneInfo("America/New_York")
        mock_scheduler.timezone = expected_tz
        mock_scheduler.get_job.return_value = None
        mock_scheduler.add_job = MagicMock()
        mock_validate_expr.return_value = {"valid": True}

        schedule_list(1, "0 9 * * 1")

        mock_cron_trigger.from_crontab.assert_called_once_with("0 9 * * mon", timezone=expected_tz)

    @patch.dict("os.environ", {"TZ": "America/New_York"})
    @patch("listarr.services.scheduler._scheduler", None)
    @patch("listarr.services.scheduler.List")
    def test_get_next_run_time_fallback_uses_scheduler_timezone(self, mock_list_class):
        """get_next_run_time() fallback returns a datetime in scheduler timezone."""
        # Setup list with valid cron expression
        mock_list_obj = MagicMock()
        mock_list_obj.schedule_cron = "0 9 * * 1"
        mock_list_obj.is_active = True
        mock_list_class.query.get.return_value = mock_list_obj

        result = get_next_run_time(1)

        assert result is not None
        assert result.tzinfo is not None
        assert result.tzinfo == zoneinfo.ZoneInfo("America/New_York")

    @patch.dict("os.environ", {"TZ": "America/New_York"})
    @patch("listarr.services.scheduler._scheduler", None)
    def test_validate_cron_expression_uses_scheduler_timezone(self):
        """validate_cron_expression() returns next runs with scheduler timezone offsets."""
        result = validate_cron_expression("0 9 * * 1")

        assert result["valid"] is True
        assert len(result["next_runs"]) == 3
        for next_run in result["next_runs"]:
            assert "Z" not in next_run
            assert next_run[-6] in {"+", "-"}

    @patch("listarr.services.scheduler._scheduler", None)
    def test_validate_cron_expression_rejects_cronsim_valid_but_unbuildable(self):
        """A cron cronsim accepts but CronTrigger.from_crontab rejects is invalid here, so
        it can never be stored on a list and reach the reconcile as an unbuildable row."""
        result = validate_cron_expression("0 2 L * *")

        assert result["valid"] is False
        assert result["error"]
        assert result["next_runs"] == []


@pytest.mark.unit
class TestTimezoneResolution:
    """Tests for DB-first application timezone resolution."""

    @pytest.fixture(autouse=True)
    def reset_timezone_memo(self):
        time_utils.invalidate_app_timezone_memo()
        yield
        time_utils.invalidate_app_timezone_memo()

    def test_db_value_wins_over_live_scheduler(self, app, monkeypatch):
        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            monkeypatch.setattr(sched, "_scheduler", MagicMock())
            sched._scheduler.timezone = zoneinfo.ZoneInfo("America/New_York")

            assert tz_key(sched._get_scheduler_timezone()) == "Asia/Tokyo"

    def test_live_scheduler_used_when_db_null(self, app, monkeypatch):
        with app.app_context():
            _set_app_timezone(None)
            monkeypatch.setattr(sched, "_scheduler", MagicMock())
            sched._scheduler.timezone = zoneinfo.ZoneInfo("America/New_York")

            assert tz_key(sched._get_scheduler_timezone()) == "America/New_York"

    def test_tz_env_used_when_db_null_and_no_scheduler(self, app, monkeypatch):
        with app.app_context():
            _set_app_timezone(None)
            monkeypatch.setattr("listarr.services.scheduler._scheduler", None)
            monkeypatch.setenv("TZ", "Europe/London")

            assert tz_key(_get_scheduler_timezone()) == "Europe/London"

    def test_utc_when_nothing_configured(self, app, monkeypatch):
        with app.app_context():
            _set_app_timezone(None)
            monkeypatch.setattr("listarr.services.scheduler._scheduler", None)
            monkeypatch.delenv("TZ", raising=False)

            assert tz_key(_get_scheduler_timezone()) == "UTC"

    def test_operational_error_falls_through_without_raising(self, monkeypatch):
        boom = OperationalError("stmt", {}, Exception("database is locked"))
        monkeypatch.setattr("listarr.models.app_config_model.get_app_config", MagicMock(side_effect=boom))
        monkeypatch.setattr("listarr.services.scheduler._scheduler", None)

        result = _get_scheduler_timezone()

        assert isinstance(result, tzinfo)

    def test_missing_app_config_row_tolerated(self, app, monkeypatch):
        with app.app_context():
            db.session.query(AppConfig).delete()
            db.session.commit()
            time_utils.invalidate_app_timezone_memo()
            monkeypatch.setattr("listarr.models.app_config_model.get_app_config", lambda: None)
            monkeypatch.setattr("listarr.services.scheduler._scheduler", None)
            monkeypatch.setenv("TZ", "Europe/London")

            assert tz_key(_get_scheduler_timezone()) == "Europe/London"

    def test_unresolvable_stored_value_falls_back_and_warns(self, app, monkeypatch, caplog):
        with app.app_context():
            _set_app_timezone("Bogus/Zone")
            monkeypatch.setattr("listarr.services.scheduler._scheduler", None)
            monkeypatch.setenv("TZ", "Europe/London")

            with caplog.at_level("WARNING"):
                result = _get_scheduler_timezone()

            assert tz_key(result) == "Europe/London"
            assert "Bogus/Zone" in caplog.text

    @pytest.mark.parametrize("value", ["foo\x00bar", "../../etc/passwd", "/etc/localtime"])
    def test_null_byte_and_traversal_values_rejected_by_resolver(self, value, app, monkeypatch):
        with app.app_context():
            _set_app_timezone(value)
            monkeypatch.setattr("listarr.services.scheduler._scheduler", None)
            monkeypatch.setenv("TZ", "Europe/London")

            assert tz_key(_get_scheduler_timezone()) == "Europe/London"


@pytest.mark.unit
class TestTimezoneMemo:
    """Tests for the short-TTL application timezone memo."""

    @pytest.fixture(autouse=True)
    def reset_timezone_memo(self):
        time_utils.invalidate_app_timezone_memo()
        yield
        time_utils.invalidate_app_timezone_memo()

    def test_memo_collapses_repeated_reads_to_one_db_hit(self, monkeypatch):
        calls = 0

        def fake_read():
            nonlocal calls
            calls += 1
            return "Asia/Tokyo"

        monkeypatch.setattr(time_utils, "_read_db_timezone_string", fake_read)

        values = [time_utils.resolve_db_timezone_string() for _ in range(20)]

        assert values == ["Asia/Tokyo"] * 20
        assert calls == 1

    def test_memo_bypassed_when_use_cache_false(self, monkeypatch):
        calls = 0

        def fake_read():
            nonlocal calls
            calls += 1
            return "Asia/Tokyo"

        monkeypatch.setattr(time_utils, "_read_db_timezone_string", fake_read)

        values = [time_utils.resolve_db_timezone_string(use_cache=False) for _ in range(3)]

        assert values == ["Asia/Tokyo"] * 3
        assert calls == 3

    def test_invalidate_memo_forces_reread(self, monkeypatch):
        values = iter(["Asia/Tokyo", "Europe/London"])
        calls = 0

        def fake_read():
            nonlocal calls
            calls += 1
            return next(values)

        monkeypatch.setattr(time_utils, "_read_db_timezone_string", fake_read)

        assert time_utils.resolve_db_timezone_string() == "Asia/Tokyo"
        time_utils.invalidate_app_timezone_memo()
        assert time_utils.resolve_db_timezone_string() == "Europe/London"
        assert calls == 2

    def test_invalidation_during_an_in_flight_read_is_not_undone(self, monkeypatch):
        """WR-08: a reader that was already querying the DB when a save invalidated the
        memo must not write its pre-save record back with a fresh TTL."""
        reads = []

        def fake_read():
            reads.append(len(reads))
            if len(reads) == 1:
                # A save lands while this read is in flight.
                time_utils.invalidate_app_timezone_memo()
                return "Europe/London"
            return "Asia/Tokyo"

        monkeypatch.setattr(time_utils, "_read_db_timezone_string", fake_read)

        assert time_utils.resolve_db_timezone_string() == "Europe/London"
        # The stale value must not have been memoized over the invalidation.
        assert time_utils.resolve_db_timezone_string() == "Asia/Tokyo"
        assert len(reads) == 2

    def test_state_is_built_from_a_single_record(self, monkeypatch):
        """WR-08: get_app_timezone_state must not re-read the record for 'resolved'."""
        monkeypatch.setattr(time_utils, "_TZ_MEMO_TTL", 0.0)
        values = iter(["Asia/Tokyo", "Europe/London"])
        reads = []

        def fake_read():
            reads.append(1)
            return next(values)

        monkeypatch.setattr(time_utils, "_read_db_timezone_string", fake_read)

        state = time_utils.get_app_timezone_state()

        assert len(reads) == 1, "state re-read the DB and can report an inconsistent pair"
        assert state["configured"] == "Asia/Tokyo"
        assert state["resolved"] == "Asia/Tokyo"
        assert state["unresolvable"] is False

    def test_state_stays_consistent_for_an_unresolvable_value(self, monkeypatch):
        monkeypatch.setattr(time_utils, "_TZ_MEMO_TTL", 0.0)
        monkeypatch.setenv("TZ", "America/New_York")
        monkeypatch.setattr(time_utils, "_read_db_timezone_string", lambda: "Bogus/Zone")

        state = time_utils.get_app_timezone_state()

        assert state["configured"] == "Bogus/Zone"
        assert state["unresolvable"] is True
        assert state["resolved"] == "America/New_York"
        assert state["fallback"] == "America/New_York"

    def test_memo_caches_none_value(self, monkeypatch):
        calls = 0

        def fake_read():
            nonlocal calls
            calls += 1
            return None

        monkeypatch.setattr(time_utils, "_read_db_timezone_string", fake_read)

        assert time_utils.resolve_db_timezone_string() is None
        assert time_utils.resolve_db_timezone_string() is None
        assert calls == 1

    def test_unresolvable_stored_value_warn_once_per_ttl(self, app, monkeypatch, caplog):
        with app.app_context():
            _set_app_timezone("Bogus/Zone")
            monkeypatch.delenv("TZ", raising=False)
            time_utils.invalidate_app_timezone_memo()

            with caplog.at_level("WARNING", logger="listarr.utils.time_utils"):
                values = [time_utils.get_app_timezone() for _ in range(20)]

                warnings = [record for record in caplog.records if "Bogus/Zone" in record.getMessage()]
                assert len(warnings) == 1
                assert all(value is timezone.utc for value in values)

                time_utils.invalidate_app_timezone_memo()
                time_utils.get_app_timezone()

                warnings = [record for record in caplog.records if "Bogus/Zone" in record.getMessage()]
                assert len(warnings) == 2


class TestSchedulerShutdownLocking:
    """WR-07: shutdown must not null the singleton out from under a live reschedule."""

    def test_shutdown_scheduler_holds_the_reschedule_lock(self, monkeypatch):
        observed = {}

        mock_scheduler = MagicMock()

        def _shutdown(wait=False):
            observed["locked_during_shutdown"] = sched._reschedule_lock.locked()

        mock_scheduler.shutdown.side_effect = _shutdown
        monkeypatch.setattr(sched, "_scheduler", mock_scheduler)

        sched.shutdown_scheduler()

        assert observed["locked_during_shutdown"] is True
        assert sched._scheduler is None
        assert sched.is_scheduler_worker() is False
        assert sched._reschedule_lock.locked() is False

    def test_shutdown_scheduler_is_a_noop_when_not_initialized(self, monkeypatch):
        monkeypatch.setattr(sched, "_scheduler", None)

        sched.shutdown_scheduler()

        assert sched._scheduler is None
        assert sched._reschedule_lock.locked() is False

    def test_reconcile_binds_scheduler_locally(self, monkeypatch):
        """A concurrent shutdown that nulls the global must not raise AttributeError
        inside an in-flight reconcile."""
        mock_scheduler = MagicMock()
        mock_scheduler.timezone = zoneinfo.ZoneInfo("UTC")
        monkeypatch.setattr(sched, "_scheduler", mock_scheduler)
        monkeypatch.setattr(sched, "_app", None)

        # _app is None -> returns early, but the guard already read the local binding.
        result = sched.reconcile_scheduler_jobs("Europe/London")
        assert result.deferred is False
        assert result.applied == 0


class _BoomQuery:
    def filter(self, *args, **kwargs):
        return self

    def count(self):
        raise OperationalError("SELECT", {}, Exception("database is locked"))

    def all(self):
        raise OperationalError("SELECT", {}, Exception("database is locked"))


class _BoomList:
    query = _BoomQuery()

    @classmethod
    def active_scheduled_query(cls):
        return cls.query.filter()


@pytest.mark.unit
class TestReconcileSchedulerJobs:
    """reconcile_scheduler_jobs(): one idempotent desired-vs-live diff."""

    @pytest.fixture(autouse=True)
    def _reset_reconcile_state(self, monkeypatch):
        monkeypatch.setattr(sched, "_last_reconciled_tz", None)
        monkeypatch.setattr(sched, "_unbuildable_crons", {})
        yield

    def _make_list(self, cron):
        from listarr.models.lists_model import List

        row = List(
            name="reconcile-unit",
            target_service="RADARR",
            tmdb_list_type="popular_movies",
            filters_json={},
            schedule_cron=cron,
            is_active=True,
        )
        db.session.add(row)
        db.session.commit()
        return row.id

    def test_applies_every_buildable_row(self, app, monkeypatch):
        with app.app_context():
            ids = [self._make_list("0 2 * * 1") for _ in range(3)]
            scheduler = MagicMock()
            scheduler.get_jobs.return_value = []
            monkeypatch.setattr(sched, "_scheduler", scheduler)
            monkeypatch.setattr(sched, "_app", app)

            result = sched.reconcile_scheduler_jobs("Europe/London")

            assert result.deferred is False
            assert result.applied == 3
            assert result.unbuildable == {}
            assert scheduler.add_job.call_count == 3
            assert sched._last_reconciled_tz == "Europe/London"
            assert {int(c.kwargs["id"][5:]) for c in scheduler.add_job.call_args_list} == set(ids)

    def test_unbuildable_row_recorded_and_others_still_applied(self, app, monkeypatch):
        with app.app_context():
            good = [self._make_list("0 2 * * 1") for _ in range(2)]
            bad = self._make_list("0 2 L * *")
            scheduler = MagicMock()
            scheduler.get_jobs.return_value = []
            monkeypatch.setattr(sched, "_scheduler", scheduler)
            monkeypatch.setattr(sched, "_app", app)

            result = sched.reconcile_scheduler_jobs("Europe/London")

            assert result.applied == 2
            assert result.unbuildable == {bad: "0 2 L * *"}
            assert {int(c.kwargs["id"][5:]) for c in scheduler.add_job.call_args_list} == set(good)

    def test_no_scheduler_reports_backlog_without_raising(self, app, monkeypatch):
        with app.app_context():
            for _ in range(2):
                self._make_list("0 2 * * 1")
            monkeypatch.setattr(sched, "_scheduler", None)
            monkeypatch.setattr(sched, "_app", app)

            result = sched.reconcile_scheduler_jobs("Europe/London")

            assert result.deferred is False
            assert result.pending == 2
            assert result.applied == 0

    def test_lock_already_held_defers_without_advancing_state(self, app, monkeypatch):
        with app.app_context():
            self._make_list("0 2 * * 1")
            scheduler = MagicMock()
            scheduler.get_jobs.return_value = []
            monkeypatch.setattr(sched, "_scheduler", scheduler)
            monkeypatch.setattr(sched, "_app", app)
            monkeypatch.setattr(sched, "_last_reconciled_tz", "Asia/Tokyo")

            assert sched._reschedule_lock.acquire(blocking=False) is True
            try:
                result = sched.reconcile_scheduler_jobs("Europe/London", blocking=False)
            finally:
                sched._reschedule_lock.release()

            assert result.deferred is True
            assert sched._last_reconciled_tz == "Asia/Tokyo"
            scheduler.add_job.assert_not_called()

    def test_operational_error_defers_without_advancing_state(self, app, monkeypatch):
        with app.app_context():
            scheduler = MagicMock()
            scheduler.get_jobs.return_value = []
            monkeypatch.setattr(sched, "_scheduler", scheduler)
            monkeypatch.setattr(sched, "_app", app)
            monkeypatch.setattr(sched, "_last_reconciled_tz", "Asia/Tokyo")
            monkeypatch.setattr(sched, "List", _BoomList)

            result = sched.reconcile_scheduler_jobs("Europe/London")

            assert result.deferred is True
            assert sched._last_reconciled_tz == "Asia/Tokyo"
            scheduler.add_job.assert_not_called()
