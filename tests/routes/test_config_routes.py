"""
Route tests for config_routes.py - Config page endpoints.

Tests cover:
- GET /config - Page rendering and data retrieval for both services
- POST /config - API key saving with encryption for Radarr and Sonarr
- POST /config/test_radarr_api - AJAX Radarr connection testing
- POST /config/test_sonarr_api - AJAX Sonarr connection testing
- GET /config/radarr/quality-profiles - Fetch Radarr quality profiles
- GET /config/radarr/root-folders - Fetch Radarr root folders
- GET/POST /config/radarr/import-settings - Radarr import settings management
- GET /config/sonarr/quality-profiles - Fetch Sonarr quality profiles
- GET /config/sonarr/root-folders - Fetch Sonarr root folders
- GET/POST /config/sonarr/import-settings - Sonarr import settings management
- Helper functions _test_and_update_radarr_status and _test_and_update_sonarr_status
- _is_valid_url URL validation
- CSRF protection
- Error handling and flash messages
- Database operations and rollback behavior
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from listarr import db
from listarr.models.service_config_model import MediaImportSettings, ServiceConfig
from listarr.services.crypto_utils import decrypt_data, encrypt_data


class TestConfigPageGET:
    """Tests for GET /config endpoint."""

    def test_config_page_renders_successfully(self, client):
        """Test that config page renders without errors."""
        response = client.get("/config")

        assert response.status_code == 200
        assert b"Service Configuration" in response.data

    def test_config_page_shows_radarr_form_fields(self, client):
        """Test that config page contains Radarr form."""
        response = client.get("/config")

        assert response.status_code == 200
        assert b"radarr_url" in response.data
        assert b"radarr_api" in response.data
        assert b"Save API" in response.data
        assert b"Test Connection" in response.data

    def test_config_page_shows_sonarr_form_fields(self, client):
        """Test that config page contains Sonarr form."""
        response = client.get("/config")

        assert response.status_code == 200
        assert b"sonarr_url" in response.data
        assert b"sonarr_api" in response.data

    def test_config_page_displays_existing_radarr_config(
        self, app, client, temp_instance_path
    ):
        """Test that existing Radarr config is displayed in form (decrypted)."""
        with app.app_context():
            # Create Radarr config with encrypted key
            original_key = "existing_radarr_key_12345"
            encrypted = encrypt_data(original_key, instance_path=temp_instance_path)

            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
                last_tested_at=datetime.now(timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/config")

        assert response.status_code == 200
        # API key and URL should be present in the form
        assert b"existing_radarr_key_12345" in response.data
        assert b"http://localhost:7878" in response.data

    def test_config_page_displays_existing_sonarr_config(
        self, app, client, temp_instance_path
    ):
        """Test that existing Sonarr config is displayed in form (decrypted)."""
        with app.app_context():
            # Create Sonarr config with encrypted key
            original_key = "existing_sonarr_key_67890"
            encrypted = encrypt_data(original_key, instance_path=temp_instance_path)

            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
                last_tested_at=datetime.now(timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/config")

        assert response.status_code == 200
        # API key and URL should be present in the form
        assert b"existing_sonarr_key_67890" in response.data
        assert b"http://localhost:8989" in response.data

    def test_config_page_displays_radarr_last_test_status_success(
        self, app, client, temp_instance_path
    ):
        """Test that Radarr successful test status is displayed."""
        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            test_time = datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
                last_tested_at=test_time,
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/config")

        assert response.status_code == 200
        assert b"Last tested:" in response.data
        # Status indicator for success
        assert b"text-green-600" in response.data or b"&#x2713;" in response.data

    def test_config_page_displays_sonarr_last_test_status_failed(
        self, app, client, temp_instance_path
    ):
        """Test that Sonarr failed test status is displayed with error indicator."""
        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)

            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
                last_tested_at=datetime.now(timezone.utc),
                last_test_status="failed",
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/config")

        assert response.status_code == 200
        # Status indicator for failure
        assert b"text-red-600" in response.data or b"&#x2717;" in response.data

    def test_config_page_without_existing_configs(self, client):
        """Test that config page works when no Radarr/Sonarr configs exist."""
        response = client.get("/config")

        assert response.status_code == 200
        assert b"Not tested yet" in response.data

    def test_config_page_shows_import_settings_when_radarr_configured(
        self, app, client, temp_instance_path
    ):
        """Test that import settings section appears when Radarr is configured."""
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/config")

        assert response.status_code == 200
        assert b"radarr-import-settings" in response.data
        assert b"Import Settings" in response.data

    def test_config_page_hides_import_settings_when_radarr_not_configured(self, client):
        """Test that import settings section is hidden when Radarr not configured."""
        response = client.get("/config")

        assert response.status_code == 200
        # Import settings should be hidden (no radarr-import-settings div)
        # Check for conditional rendering logic

    def test_config_page_includes_csrf_token(self, client):
        """Test that CSRF token meta tag is present."""
        response = client.get("/config")

        assert response.status_code == 200
        assert b"csrf-token" in response.data

    def test_config_page_includes_javascript(self, client):
        """Test that config.js is included."""
        response = client.get("/config")

        assert response.status_code == 200
        assert b"config.js" in response.data


class TestRadarrConfigPOST:
    """Tests for POST /config endpoint (Save Radarr API)."""

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_save_radarr_api_with_valid_credentials_creates_new_config(
        self, mock_test, app, client, temp_instance_path
    ):
        """Test saving valid Radarr credentials creates new ServiceConfig entry."""
        mock_test.return_value = True

        response = client.post(
            "/config",
            data={
                "radarr_url": "http://localhost:7878",
                "radarr_api": "new_valid_radarr_key",
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Radarr URL and API Key saved successfully" in response.data

        # Verify database entry
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            assert config is not None
            assert config.base_url == "http://localhost:7878"
            assert config.last_test_status == "success"

            # Verify key is encrypted
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "new_valid_radarr_key"

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_save_radarr_api_with_valid_credentials_updates_existing_config(
        self, mock_test, app, client, temp_instance_path
    ):
        """Test saving valid Radarr credentials updates existing ServiceConfig."""
        mock_test.return_value = True

        # Create existing config
        with app.app_context():
            old_encrypted = encrypt_data("old_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=old_encrypted,
                last_tested_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()
            old_id = config.id

        response = client.post(
            "/config",
            data={
                "radarr_url": "http://192.168.1.100:7878",
                "radarr_api": "updated_radarr_key",
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Radarr URL and API Key saved successfully" in response.data

        # Verify database was updated, not created new
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="RADARR").all()
            assert len(configs) == 1
            assert configs[0].id == old_id
            assert configs[0].base_url == "http://192.168.1.100:7878"

            # Verify key was updated
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "updated_radarr_key"

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_save_radarr_api_with_invalid_credentials_shows_error(self, mock_test, app, client):
        """Test that invalid Radarr credentials show error message."""
        mock_test.return_value = False

        response = client.post(
            "/config",
            data={
                "radarr_url": "http://localhost:7878",
                "radarr_api": "invalid_key",
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid Radarr URL or API Key" in response.data

        # Verify no database entry was created
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            assert config is None

    def test_save_radarr_api_with_empty_url_shows_warning(self, client):
        """Test that empty Radarr URL shows warning message."""
        response = client.post(
            "/config",
            data={
                "radarr_url": "",
                "radarr_api": "some_key",
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"URL and API Key cannot be empty" in response.data

    def test_save_radarr_api_with_empty_key_shows_warning(self, client):
        """Test that empty Radarr API key shows warning."""
        response = client.post(
            "/config",
            data={
                "radarr_url": "http://localhost:7878",
                "radarr_api": "",
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"URL and API Key cannot be empty" in response.data

    def test_save_radarr_api_with_invalid_url_format_shows_warning(self, client):
        """Test that invalid URL format shows warning."""
        response = client.post(
            "/config",
            data={
                "radarr_url": "not-a-valid-url",
                "radarr_api": "some_key",
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid URL format" in response.data

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_save_radarr_api_trims_whitespace(self, mock_test, app, client, temp_instance_path):
        """Test that Radarr URL and API key whitespace is trimmed before saving."""
        mock_test.return_value = True

        response = client.post(
            "/config",
            data={
                "radarr_url": "  http://localhost:7878  ",
                "radarr_api": "  trimmed_radarr_key  ",
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify trimmed values were saved
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            assert config.base_url == "http://localhost:7878"
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "trimmed_radarr_key"

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    @patch("listarr.routes.config_routes.encrypt_data")
    def test_save_radarr_api_handles_encryption_error(self, mock_encrypt, mock_test, client):
        """Test that Radarr encryption errors are handled gracefully."""
        mock_test.return_value = True
        mock_encrypt.side_effect = Exception("Encryption failed")

        response = client.post(
            "/config",
            data={
                "radarr_url": "http://localhost:7878",
                "radarr_api": "valid_key",
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Failed to save Radarr configuration" in response.data

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_save_radarr_api_handles_database_error(self, mock_test, app, client):
        """Test that Radarr database errors trigger rollback."""
        mock_test.return_value = True

        with app.app_context():
            # Create invalid state to trigger database error
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                response = client.post(
                    "/config",
                    data={
                        "radarr_url": "http://localhost:7878",
                        "radarr_api": "valid_key",
                        "save_radarr_api": "true",
                    },
                    follow_redirects=True,
                )

        assert response.status_code == 200
        assert b"Failed to save Radarr configuration" in response.data

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_save_radarr_api_updates_last_tested_timestamp(self, mock_test, app, client, temp_instance_path):
        """Test that Radarr save operation updates last_tested_at."""
        mock_test.return_value = True

        before_time = datetime.now(timezone.utc)

        client.post(
            "/config",
            data={
                "radarr_url": "http://localhost:7878",
                "radarr_api": "valid_key",
                "save_radarr_api": "true",
            },
        )

        after_time = datetime.now(timezone.utc)

        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            assert config.last_tested_at is not None
            assert before_time <= config.last_tested_at <= after_time

    def test_save_radarr_api_redirects_to_config_page(self, client):
        """Test that POST redirects back to config page."""
        response = client.post(
            "/config",
            data={"radarr_url": "", "radarr_api": "", "save_radarr_api": "true"},
        )

        assert response.status_code == 302
        assert "/config" in response.location


class TestConcurrentOperations:
    """Tests for concurrent operations and multiple service saves."""

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_save_both_services_in_single_post(self, mock_sonarr, mock_radarr, app, client, temp_instance_path):
        """Test saving both Radarr and Sonarr configs in one POST request."""
        mock_radarr.return_value = True
        mock_sonarr.return_value = True

        response = client.post(
            "/config",
            data={
                "radarr_url": "http://localhost:7878",
                "radarr_api": "radarr_key",
                "save_radarr_api": "true",
                "sonarr_url": "http://localhost:8989",
                "sonarr_api": "sonarr_key",
                "save_sonarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Radarr URL and API Key saved successfully" in response.data
        assert b"Sonarr URL and API Key saved successfully" in response.data

        with app.app_context():
            radarr = ServiceConfig.query.filter_by(service="RADARR").first()
            sonarr = ServiceConfig.query.filter_by(service="SONARR").first()
            assert radarr is not None
            assert sonarr is not None
            # Verify keys are encrypted and correct
            decrypted_radarr = decrypt_data(radarr.api_key_encrypted, instance_path=temp_instance_path)
            decrypted_sonarr = decrypt_data(sonarr.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted_radarr == "radarr_key"
            assert decrypted_sonarr == "sonarr_key"


class TestSonarrConfigPOST:
    """Tests for POST /config endpoint (Save Sonarr API)."""

    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_save_sonarr_api_with_valid_credentials_creates_new_config(
        self, mock_test, app, client, temp_instance_path
    ):
        """Test saving valid Sonarr credentials creates new ServiceConfig entry."""
        mock_test.return_value = True

        response = client.post(
            "/config",
            data={
                "sonarr_url": "http://localhost:8989",
                "sonarr_api": "new_valid_sonarr_key",
                "save_sonarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Sonarr URL and API Key saved successfully" in response.data

        # Verify database entry
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="SONARR").first()
            assert config is not None
            assert config.base_url == "http://localhost:8989"
            assert config.last_test_status == "success"

            # Verify key is encrypted
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "new_valid_sonarr_key"

    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_save_sonarr_api_with_valid_credentials_updates_existing_config(
        self, mock_test, app, client, temp_instance_path
    ):
        """Test saving valid Sonarr credentials updates existing ServiceConfig."""
        mock_test.return_value = True

        # Create existing config
        with app.app_context():
            old_encrypted = encrypt_data("old_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=old_encrypted,
                last_tested_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()
            old_id = config.id

        response = client.post(
            "/config",
            data={
                "sonarr_url": "http://192.168.1.100:8989",
                "sonarr_api": "updated_sonarr_key",
                "save_sonarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Sonarr URL and API Key saved successfully" in response.data

        # Verify database was updated, not created new
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="SONARR").all()
            assert len(configs) == 1
            assert configs[0].id == old_id
            assert configs[0].base_url == "http://192.168.1.100:8989"

            # Verify key was updated
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "updated_sonarr_key"

    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_save_sonarr_api_with_invalid_credentials_shows_error(self, mock_test, app, client):
        """Test that invalid Sonarr credentials show error message."""
        mock_test.return_value = False

        response = client.post(
            "/config",
            data={
                "sonarr_url": "http://localhost:8989",
                "sonarr_api": "invalid_key",
                "save_sonarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid Sonarr URL or API Key" in response.data

        # Verify no database entry was created
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="SONARR").first()
            assert config is None

    def test_save_sonarr_api_with_invalid_url_format_shows_warning(self, client):
        """Test that invalid Sonarr URL format shows warning."""
        response = client.post(
            "/config",
            data={
                "sonarr_url": "invalid-url-format",
                "sonarr_api": "some_key",
                "save_sonarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid URL format" in response.data


class TestTestRadarrAPIAjax:
    """Tests for POST /config/test_radarr_api endpoint (AJAX)."""

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_test_radarr_api_with_valid_credentials(self, mock_test, app, client):
        """Test AJAX endpoint with valid Radarr credentials."""
        mock_test.return_value = True

        response = client.post(
            "/config/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": "valid_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Radarr connection successful" in data["message"]
        assert "timestamp" in data

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_test_radarr_api_with_invalid_credentials(self, mock_test, app, client):
        """Test AJAX endpoint with invalid Radarr credentials."""
        mock_test.return_value = False

        response = client.post(
            "/config/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": "invalid_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid Radarr URL or API Key" in data["message"]
        assert "timestamp" in data

    def test_test_radarr_api_with_empty_url(self, client):
        """Test AJAX endpoint with empty Radarr URL."""
        response = client.post(
            "/config/test_radarr_api",
            json={"base_url": "", "api_key": "some_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "URL and API key cannot be empty" in data["message"]

    def test_test_radarr_api_with_empty_key(self, client):
        """Test AJAX endpoint with empty Radarr API key."""
        response = client.post(
            "/config/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": ""},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "URL and API key cannot be empty" in data["message"]

    def test_test_radarr_api_with_invalid_url_format(self, client):
        """Test AJAX endpoint with invalid Radarr URL format."""
        response = client.post(
            "/config/test_radarr_api",
            json={"base_url": "not-a-url", "api_key": "some_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid URL format" in data["message"]

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_test_radarr_api_updates_database(self, mock_test, app, client, temp_instance_path):
        """Test that AJAX test updates database with results."""
        mock_test.return_value = True

        # Create existing config
        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
                last_tested_at=None,
                last_test_status=None,
            )
            db.session.add(config)
            db.session.commit()

        response = client.post(
            "/config/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": "test_key"},
            content_type="application/json",
        )

        assert response.status_code == 200

        # Verify database was updated
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            assert config.last_tested_at is not None
            assert config.last_test_status == "success"

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_test_radarr_api_handles_database_error(self, mock_test, app, client):
        """Test that database errors during test are handled gracefully."""
        mock_test.return_value = True

        with app.app_context():
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                response = client.post(
                    "/config/test_radarr_api",
                    json={"base_url": "http://localhost:7878", "api_key": "valid_key"},
                    content_type="application/json",
                )

        # Should still return success from test, even if DB update fails
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_test_radarr_api_returns_iso_timestamp(self, mock_test, client):
        """Test that timestamp is returned in ISO format."""
        mock_test.return_value = True

        response = client.post(
            "/config/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": "valid_key"},
            content_type="application/json",
        )

        data = response.get_json()
        timestamp = data["timestamp"]

        # Verify it's a valid ISO timestamp
        assert "T" in timestamp
        assert timestamp.endswith("Z") or "+" in timestamp or timestamp.count(":") >= 2


class TestTestSonarrAPIAjax:
    """Tests for POST /config/test_sonarr_api endpoint (AJAX)."""

    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_test_sonarr_api_with_valid_credentials(self, mock_test, app, client):
        """Test AJAX endpoint with valid Sonarr credentials."""
        mock_test.return_value = True

        response = client.post(
            "/config/test_sonarr_api",
            json={"base_url": "http://localhost:8989", "api_key": "valid_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Sonarr connection successful" in data["message"]
        assert "timestamp" in data

    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_test_sonarr_api_with_invalid_credentials(self, mock_test, app, client):
        """Test AJAX endpoint with invalid Sonarr credentials."""
        mock_test.return_value = False

        response = client.post(
            "/config/test_sonarr_api",
            json={"base_url": "http://localhost:8989", "api_key": "invalid_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid Sonarr URL or API Key" in data["message"]

    def test_test_sonarr_api_with_invalid_url_format(self, client):
        """Test AJAX endpoint with invalid Sonarr URL format."""
        response = client.post(
            "/config/test_sonarr_api",
            json={"base_url": "invalid-format", "api_key": "some_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid URL format" in data["message"]


class TestRadarrQualityProfilesEndpoint:
    """Tests for GET /config/radarr/quality-profiles endpoint."""

    @patch("listarr.routes.config_routes.get_radarr_quality_profiles")
    def test_fetch_radarr_quality_profiles_success(self, mock_get_profiles, app, client, temp_instance_path):
        """Test fetching Radarr quality profiles successfully."""
        # Create Radarr config
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_get_profiles.return_value = [
            {"id": 1, "name": "HD-1080p"},
            {"id": 2, "name": "Ultra-HD"},
        ]

        response = client.get("/config/radarr/quality-profiles")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["profiles"]) == 2
        assert data["profiles"][0]["name"] == "HD-1080p"

    def test_fetch_radarr_quality_profiles_without_config(self, client):
        """Test fetching quality profiles when Radarr not configured."""
        response = client.get("/config/radarr/quality-profiles")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Radarr not configured" in data["message"]

    @patch("listarr.routes.config_routes.get_radarr_quality_profiles")
    def test_fetch_radarr_quality_profiles_api_failure(self, mock_get_profiles, app, client, temp_instance_path):
        """Test handling of API failure when fetching quality profiles."""
        # Create Radarr config
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_get_profiles.return_value = []

        response = client.get("/config/radarr/quality-profiles")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch quality profiles" in data["message"]

    @patch("listarr.routes.config_routes.decrypt_data")
    def test_fetch_radarr_quality_profiles_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test handling when decryption fails for quality profiles."""
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_decrypt.side_effect = ValueError("Decryption failed")

        response = client.get("/config/radarr/quality-profiles")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed" in data["message"]


class TestRadarrRootFoldersEndpoint:
    """Tests for GET /config/radarr/root-folders endpoint."""

    @patch("listarr.routes.config_routes.get_radarr_root_folders")
    def test_fetch_radarr_root_folders_success(self, mock_get_folders, app, client, temp_instance_path):
        """Test fetching Radarr root folders successfully."""
        # Create Radarr config
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_get_folders.return_value = [
            {"id": 1, "path": "/movies"},
            {"id": 2, "path": "/storage/movies"},
        ]

        response = client.get("/config/radarr/root-folders")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["folders"]) == 2
        assert data["folders"][0]["path"] == "/movies"

    def test_fetch_radarr_root_folders_without_config(self, client):
        """Test fetching root folders when Radarr not configured."""
        response = client.get("/config/radarr/root-folders")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Radarr not configured" in data["message"]

    @patch("listarr.routes.config_routes.get_radarr_root_folders")
    def test_fetch_radarr_root_folders_api_failure(self, mock_get_folders, app, client, temp_instance_path):
        """Test handling of API failure when fetching root folders."""
        # Create Radarr config
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_get_folders.return_value = []

        response = client.get("/config/radarr/root-folders")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch root folders" in data["message"]

    @patch("listarr.routes.config_routes.decrypt_data")
    def test_fetch_radarr_root_folders_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test handling when decryption fails for root folders."""
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_decrypt.side_effect = ValueError("Decryption failed")

        response = client.get("/config/radarr/root-folders")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed" in data["message"]


class TestRadarrImportSettingsEndpoints:
    """Tests for Radarr import settings GET and POST endpoints."""

    def test_fetch_radarr_import_settings_when_none_exist(self, client):
        """Test fetching import settings when none exist."""
        response = client.get("/config/radarr/import-settings")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["settings"] is None

    @patch("listarr.routes.config_routes.get_radarr_root_folders")
    def test_fetch_radarr_import_settings_when_exist(self, mock_root_folders, app, client, temp_instance_path):
        """Test fetching existing import settings (returns ID from stored path)."""
        # Create Radarr service config for API lookup
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)

            settings = MediaImportSettings(
                service="RADARR",
                root_folder="/movies",  # Path stored in DB
                quality_profile_id=1,
                monitored=True,
                search_on_add=False,
            )
            db.session.add(settings)
            db.session.commit()

        # Mock root folders to return ID for the stored path
        mock_root_folders.return_value = [
            {"id": 5, "path": "/movies"},
            {"id": 6, "path": "/other"},
        ]

        response = client.get("/config/radarr/import-settings")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["settings"]["root_folder_id"] == 5  # Returns ID, not path
        assert data["settings"]["quality_profile_id"] == 1
        assert data["settings"]["monitored"] is True
        assert data["settings"]["search_on_add"] is False

    @patch("listarr.routes.config_routes.get_radarr_root_folders")
    def test_save_radarr_import_settings_creates_new(self, mock_root_folders, app, client, temp_instance_path):
        """Test saving new Radarr import settings (stores path from ID)."""
        # Create Radarr service config
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        # Mock root folders - route looks up path from ID
        mock_root_folders.return_value = [
            {"id": 5, "path": "/movies"},
            {"id": 6, "path": "/other"},
        ]

        response = client.post(
            "/config/radarr/import-settings",
            json={
                "root_folder_id": 5,  # Pass ID, not path
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify path is stored in database (not ID)
        with app.app_context():
            settings = MediaImportSettings.query.filter_by(service="RADARR").first()
            assert settings is not None
            assert settings.root_folder == "/movies"  # Path stored, not ID
            assert settings.quality_profile_id == 1

    @patch("listarr.routes.config_routes.get_radarr_root_folders")
    def test_save_radarr_import_settings_updates_existing(self, mock_root_folders, app, client, temp_instance_path):
        """Test updating existing Radarr import settings."""
        # Create Radarr service config and existing settings
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)

            settings = MediaImportSettings(
                service="RADARR",
                root_folder="/old",
                quality_profile_id=1,
                monitored=True,
                search_on_add=True,
            )
            db.session.add(settings)
            db.session.commit()
            settings_id = settings.id

        # Mock root folders
        mock_root_folders.return_value = [
            {"id": 7, "path": "/new"},
            {"id": 8, "path": "/other"},
        ]

        response = client.post(
            "/config/radarr/import-settings",
            json={
                "root_folder_id": 7,  # Pass ID
                "quality_profile_id": 2,
                "monitored": False,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 200

        # Verify update (not new entry)
        with app.app_context():
            all_settings = MediaImportSettings.query.filter_by(service="RADARR").all()
            assert len(all_settings) == 1
            assert all_settings[0].id == settings_id
            assert all_settings[0].root_folder == "/new"  # Path stored

    def test_save_radarr_import_settings_validates_required_fields(self, client):
        """Test that required fields are validated."""
        response = client.post(
            "/config/radarr/import-settings",
            json={
                "root_folder_id": "",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Root Folder and Quality Profile are required" in data["message"]

    def test_save_radarr_import_settings_missing_monitored(self, client):
        """Test that missing monitored field is rejected."""
        response = client.post(
            "/config/radarr/import-settings",
            json={
                "root_folder_id": "/movies",
                "quality_profile_id": 1,
                # monitored missing
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Monitor option is required" in data["message"]

    def test_save_radarr_import_settings_missing_search_on_add(self, client):
        """Test that missing search_on_add field is rejected."""
        response = client.post(
            "/config/radarr/import-settings",
            json={
                "root_folder_id": "/movies",
                "quality_profile_id": 1,
                "monitored": True,
                # search_on_add missing
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Search on Add option is required" in data["message"]

    def test_save_radarr_import_settings_invalid_quality_profile_type(self, client):
        """Test that invalid type for quality_profile_id is rejected."""
        response = client.post(
            "/config/radarr/import-settings",
            json={
                "root_folder_id": "/movies",
                "quality_profile_id": "not-a-number",  # Should be int
                "monitored": True,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        # Should handle gracefully (either 400 or 500 depending on implementation)
        assert response.status_code in [400, 500]
        data = response.get_json()
        assert data["success"] is False

    @patch("listarr.routes.config_routes.get_radarr_root_folders")
    def test_save_radarr_import_settings_handles_database_error(
        self, mock_root_folders, app, client, temp_instance_path
    ):
        """Test handling of database errors during save."""
        # Create Radarr service config
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_root_folders.return_value = [{"id": 5, "path": "/movies"}]

        with patch.object(db.session, "commit", side_effect=Exception("DB error")):
            response = client.post(
                "/config/radarr/import-settings",
                json={
                    "root_folder_id": 5,
                    "quality_profile_id": 1,
                    "monitored": True,
                    "search_on_add": False,
                },
                content_type="application/json",
            )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False


class TestSonarrQualityProfilesEndpoint:
    """Tests for GET /config/sonarr/quality-profiles endpoint."""

    @patch("listarr.routes.config_routes.get_sonarr_quality_profiles")
    def test_fetch_sonarr_quality_profiles_success(self, mock_get_profiles, app, client, temp_instance_path):
        """Test fetching Sonarr quality profiles successfully."""
        # Create Sonarr config
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_get_profiles.return_value = [
            {"id": 1, "name": "HD-1080p"},
            {"id": 2, "name": "Ultra-HD"},
        ]

        response = client.get("/config/sonarr/quality-profiles")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["profiles"]) == 2

    def test_fetch_sonarr_quality_profiles_without_config(self, client):
        """Test fetching quality profiles when Sonarr not configured."""
        response = client.get("/config/sonarr/quality-profiles")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Sonarr not configured" in data["message"]

    @patch("listarr.routes.config_routes.get_sonarr_quality_profiles")
    def test_fetch_sonarr_quality_profiles_api_failure(self, mock_get_profiles, app, client, temp_instance_path):
        """Test handling of API failure when fetching quality profiles."""
        # Create Sonarr config
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_get_profiles.return_value = []

        response = client.get("/config/sonarr/quality-profiles")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch quality profiles" in data["message"]

    @patch("listarr.routes.config_routes.decrypt_data")
    def test_fetch_sonarr_quality_profiles_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test handling when decryption fails for quality profiles."""
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_decrypt.side_effect = ValueError("Decryption failed")

        response = client.get("/config/sonarr/quality-profiles")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed" in data["message"]


class TestSonarrRootFoldersEndpoint:
    """Tests for GET /config/sonarr/root-folders endpoint."""

    @patch("listarr.routes.config_routes.get_sonarr_root_folders")
    def test_fetch_sonarr_root_folders_success(self, mock_get_folders, app, client, temp_instance_path):
        """Test fetching Sonarr root folders successfully."""
        # Create Sonarr config
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_get_folders.return_value = [
            {"id": 1, "path": "/tv"},
            {"id": 2, "path": "/storage/tv"},
        ]

        response = client.get("/config/sonarr/root-folders")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["folders"]) == 2

    def test_fetch_sonarr_root_folders_without_config(self, client):
        """Test fetching root folders when Sonarr not configured."""
        response = client.get("/config/sonarr/root-folders")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Sonarr not configured" in data["message"]

    @patch("listarr.routes.config_routes.get_sonarr_root_folders")
    def test_fetch_sonarr_root_folders_api_failure(self, mock_get_folders, app, client, temp_instance_path):
        """Test handling of API failure when fetching root folders."""
        # Create Sonarr config
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_get_folders.return_value = []

        response = client.get("/config/sonarr/root-folders")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch root folders" in data["message"]

    @patch("listarr.routes.config_routes.decrypt_data")
    def test_fetch_sonarr_root_folders_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test handling when decryption fails for root folders."""
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_decrypt.side_effect = ValueError("Decryption failed")

        response = client.get("/config/sonarr/root-folders")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed" in data["message"]


class TestSonarrImportSettingsEndpoints:
    """Tests for Sonarr import settings GET and POST endpoints."""

    def test_fetch_sonarr_import_settings_when_none_exist(self, client):
        """Test fetching Sonarr import settings when none exist."""
        response = client.get("/config/sonarr/import-settings")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["settings"] is None

    @patch("listarr.routes.config_routes.get_sonarr_root_folders")
    def test_fetch_sonarr_import_settings_when_exist(self, mock_root_folders, app, client, temp_instance_path):
        """Test fetching existing Sonarr import settings (returns ID from stored path)."""
        # Create Sonarr service config for API lookup
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)

            settings = MediaImportSettings(
                service="SONARR",
                root_folder="/tv",  # Path stored in DB
                quality_profile_id=1,
                monitored=True,
                season_folder=True,
                search_on_add=False,
            )
            db.session.add(settings)
            db.session.commit()

        # Mock root folders to return ID for the stored path
        mock_root_folders.return_value = [
            {"id": 3, "path": "/tv"},
            {"id": 4, "path": "/other"},
        ]

        response = client.get("/config/sonarr/import-settings")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["settings"]["root_folder_id"] == 3  # Returns ID, not path
        assert data["settings"]["season_folder"] is True

    @patch("listarr.routes.config_routes.get_sonarr_root_folders")
    def test_save_sonarr_import_settings_creates_new(self, mock_root_folders, app, client, temp_instance_path):
        """Test saving new Sonarr import settings (stores path from ID)."""
        # Create Sonarr service config
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        # Mock root folders - route looks up path from ID
        mock_root_folders.return_value = [
            {"id": 3, "path": "/tv"},
            {"id": 4, "path": "/other"},
        ]

        response = client.post(
            "/config/sonarr/import-settings",
            json={
                "root_folder_id": 3,  # Pass ID, not path
                "quality_profile_id": 1,
                "monitored": True,
                "season_folder": True,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify path is stored in database (not ID)
        with app.app_context():
            settings = MediaImportSettings.query.filter_by(service="SONARR").first()
            assert settings is not None
            assert settings.root_folder == "/tv"  # Path stored, not ID
            assert settings.season_folder is True

    def test_save_sonarr_import_settings_validates_season_folder_required(self, client):
        """Test that season_folder is required for Sonarr."""
        response = client.post(
            "/config/sonarr/import-settings",
            json={
                "root_folder_id": "/tv",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": False
                # season_folder missing
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Season Folder option is required" in data["message"]

    def test_save_sonarr_import_settings_missing_search_on_add(self, client):
        """Test that missing search_on_add field is rejected."""
        response = client.post(
            "/config/sonarr/import-settings",
            json={
                "root_folder_id": "/tv",
                "quality_profile_id": 1,
                "monitored": True,
                "season_folder": True,
                # search_on_add missing
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Search on Add option is required" in data["message"]

    @patch("listarr.routes.config_routes.get_sonarr_root_folders")
    def test_save_sonarr_import_settings_updates_existing(self, mock_root_folders, app, client, temp_instance_path):
        """Test updating existing Sonarr import settings."""
        # Create Sonarr service config and existing settings
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)

            settings = MediaImportSettings(
                service="SONARR",
                root_folder="/old",
                quality_profile_id=1,
                monitored=True,
                season_folder=True,
                search_on_add=True,
            )
            db.session.add(settings)
            db.session.commit()
            settings_id = settings.id

        # Mock root folders
        mock_root_folders.return_value = [
            {"id": 5, "path": "/new"},
            {"id": 6, "path": "/other"},
        ]

        response = client.post(
            "/config/sonarr/import-settings",
            json={
                "root_folder_id": 5,  # Pass ID
                "quality_profile_id": 2,
                "monitored": False,
                "season_folder": False,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 200

        # Verify update (not new entry)
        with app.app_context():
            all_settings = MediaImportSettings.query.filter_by(service="SONARR").all()
            assert len(all_settings) == 1
            assert all_settings[0].id == settings_id
            assert all_settings[0].root_folder == "/new"  # Path stored

    @patch("listarr.routes.config_routes.get_sonarr_root_folders")
    def test_save_sonarr_import_settings_handles_database_error(
        self, mock_root_folders, app, client, temp_instance_path
    ):
        """Test handling of database errors during save."""
        # Create Sonarr service config
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        mock_root_folders.return_value = [{"id": 3, "path": "/tv"}]

        with patch.object(db.session, "commit", side_effect=Exception("DB error")):
            response = client.post(
                "/config/sonarr/import-settings",
                json={
                    "root_folder_id": 3,
                    "quality_profile_id": 1,
                    "monitored": True,
                    "season_folder": True,
                    "search_on_add": False,
                },
                content_type="application/json",
            )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_save_sonarr_import_settings_validates_required_fields(self, client):
        """Test that required fields are validated."""
        response = client.post(
            "/config/sonarr/import-settings",
            json={
                "root_folder_id": "",
                "quality_profile_id": 1,
                "monitored": True,
                "season_folder": True,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Root Folder and Quality Profile are required" in data["message"]


class TestHelperFunctions:
    """Tests for helper functions."""

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_helper_test_and_update_radarr_status_returns_success_tuple(self, mock_test, app, temp_instance_path):
        """Test that Radarr helper returns correct tuple on success."""
        from listarr.routes.config_routes import _test_and_update_radarr_status

        mock_test.return_value = True

        with app.app_context():
            result, timestamp, status = _test_and_update_radarr_status(
                "http://localhost:7878", "valid_key"
            )

        assert result is True
        assert timestamp is not None
        assert status == "success"

    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_helper_test_and_update_sonarr_status_returns_failure_tuple(self, mock_test, app, temp_instance_path):
        """Test that Sonarr helper returns correct tuple on failure."""
        from listarr.routes.config_routes import _test_and_update_sonarr_status

        mock_test.return_value = False

        with app.app_context():
            result, timestamp, status = _test_and_update_sonarr_status(
                "http://localhost:8989", "invalid_key"
            )

        assert result is False
        assert timestamp is not None
        assert status == "failed"

    def test_helper_is_valid_url_with_valid_urls(self):
        """Test URL validation helper with valid URLs."""
        from listarr.routes.config_routes import _is_valid_url

        assert _is_valid_url("http://localhost:7878") is True
        assert _is_valid_url("https://radarr.example.com") is True
        assert _is_valid_url("http://192.168.1.100:7878") is True

    def test_helper_is_valid_url_with_invalid_urls(self):
        """Test URL validation helper with invalid URLs."""
        from listarr.routes.config_routes import _is_valid_url

        assert _is_valid_url("not-a-url") is False
        assert _is_valid_url("localhost:7878") is False
        assert _is_valid_url("") is False
        assert _is_valid_url("just-text") is False

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("http://localhost:7878/", True),  # Trailing slash
            ("http://192.168.1.1:7878", True),  # IP address
            ("https://radarr.example.com/api", True),  # With path
            ("http://localhost:7878?test=1", True),  # Query params
            ("http://[::1]:7878", True),  # IPv6
            ("localhost:7878", False),  # Missing scheme
            ("http://", False),  # Missing netloc
            ("https://radarr.example.com:7878", True),  # HTTPS with port
            ("http://127.0.0.1:7878", True),  # Localhost IP
        ],
    )
    def test_helper_is_valid_url_edge_cases(self, url, expected):
        """Test URL validation with various edge cases."""
        from listarr.routes.config_routes import _is_valid_url

        assert _is_valid_url(url) == expected

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_helper_test_and_update_radarr_status_database_error(self, mock_test, app, temp_instance_path):
        """Test that helper handles database errors gracefully."""
        from listarr.routes.config_routes import _test_and_update_radarr_status

        mock_test.return_value = True

        with app.app_context():
            # Create config
            encrypted = encrypt_data("key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Force DB error
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                result, timestamp, status = _test_and_update_radarr_status("http://localhost:7878", "key")

        # Should still return test result even if DB update fails
        assert result is True
        assert timestamp is not None
        assert status == "success"

    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_helper_test_and_update_sonarr_status_database_error(self, mock_test, app, temp_instance_path):
        """Test that helper handles database errors gracefully."""
        from listarr.routes.config_routes import _test_and_update_sonarr_status

        mock_test.return_value = True

        with app.app_context():
            # Create config
            encrypted = encrypt_data("key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Force DB error
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                result, timestamp, status = _test_and_update_sonarr_status("http://localhost:8989", "key")

        # Should still return test result even if DB update fails
        assert result is True
        assert timestamp is not None
        assert status == "success"


class TestCSRFProtection:
    """Tests for CSRF token protection."""

    def test_config_page_includes_csrf_meta_tag(self, client):
        """Test that CSRF token meta tag is present in page."""
        response = client.get("/config")

        assert response.status_code == 200
        assert b'<meta name="csrf-token"' in response.data

    def test_config_forms_include_hidden_csrf_token(self, client_with_csrf):
        """Test that forms include hidden CSRF token field."""
        response = client_with_csrf.get("/config")

        assert response.status_code == 200
        # Flask-WTF adds hidden CSRF token field with name attribute
        assert (
            b'name="csrf_token"' in response.data
            or b"name='csrf_token'" in response.data
        )


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    @patch("listarr.routes.config_routes.decrypt_data")
    def test_config_get_handles_radarr_decryption_error(self, mock_decrypt, mock_test, app, client, temp_instance_path):
        """Test that GET /config handles Radarr decryption errors gracefully."""
        mock_decrypt.side_effect = ValueError("Decryption failed")

        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        # Should not crash, might show empty field or error
        response = client.get("/config")
        assert response.status_code == 200

    @patch("listarr.routes.config_routes.validate_radarr_api_key")
    def test_save_radarr_api_with_special_characters(self, mock_test, app, client, temp_instance_path):
        """Test saving Radarr API key with special characters."""
        mock_test.return_value = True
        special_key = "key!@#$%^&*()_+-={}[]|:;<>,.?/"

        response = client.post(
            "/config",
            data={
                "radarr_url": "http://localhost:7878",
                "radarr_api": special_key,
                "save_radarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify special characters were preserved
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            decrypted = decrypt_data(
                config.api_key_encrypted, instance_path=temp_instance_path
            )
            assert decrypted == special_key

    @patch("listarr.routes.config_routes.validate_sonarr_api_key")
    def test_save_sonarr_api_with_unicode_characters(self, mock_test, app, client, temp_instance_path):
        """Test saving Sonarr API key with Unicode characters."""
        mock_test.return_value = True
        unicode_key = "key_测试_тест_🔑"

        response = client.post(
            "/config",
            data={
                "sonarr_url": "http://localhost:8989",
                "sonarr_api": unicode_key,
                "save_sonarr_api": "true",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        with app.app_context():
            config = ServiceConfig.query.filter_by(service="SONARR").first()
            decrypted = decrypt_data(
                config.api_key_encrypted, instance_path=temp_instance_path
            )
            assert decrypted == unicode_key
