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
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from listarr.services.scheduler import (
    _get_scheduler_timezone,
    _run_scheduled_import,
    get_next_run_time,
    schedule_list,
    validate_cron_expression,
)


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
