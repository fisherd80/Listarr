"""
Tests for scheduler service pre-flight health check.

Tests cover:
- _run_scheduled_import() health check before job submission
- Service configuration validation
- API key validation and reachability checks
- Error handling for decrypt and validate operations
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from listarr.services.scheduler import _run_scheduled_import


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
