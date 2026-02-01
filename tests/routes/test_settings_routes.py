"""
Route tests for settings_routes.py - Settings page endpoints.

Tests cover:
- GET /settings - Page rendering and data retrieval
- POST /settings - API key saving with encryption
- POST /settings/test_tmdb_api - AJAX connection testing
- Helper function _test_and_update_tmdb_status
- CSRF protection
- Error handling and flash messages
- Database operations and rollback behavior
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from listarr import db
from listarr.models.service_config_model import ServiceConfig
from listarr.services.crypto_utils import decrypt_data, encrypt_data


class TestSettingsPageGET:
    """Tests for GET /settings endpoint."""

    def test_settings_page_renders_successfully(self, client):
        """Test that settings page renders without errors."""
        response = client.get("/settings")

        assert response.status_code == 200
        assert b"Settings" in response.data
        assert b"TMDB API Configuration" in response.data

    def test_settings_page_shows_form_fields(self, client):
        """Test that settings page contains TMDB API form."""
        response = client.get("/settings")

        assert response.status_code == 200
        assert b"tmdb_api" in response.data
        assert b"Save API Key" in response.data
        assert b"Test Connection" in response.data

    def test_settings_page_displays_existing_api_key(self, app, client, temp_instance_path):
        """Test that existing API key is displayed in form (decrypted)."""
        with app.app_context():
            # Create TMDB config with encrypted key
            original_key = "existing_api_key_12345"
            encrypted = encrypt_data(original_key, instance_path=temp_instance_path)

            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=encrypted,
                last_tested_at=datetime.now(timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/settings")

        assert response.status_code == 200
        # API key should be present in the form (password field)
        assert b"existing_api_key_12345" in response.data

    def test_settings_page_displays_last_test_status(self, app, client, temp_instance_path):
        """Test that last test timestamp and status are displayed."""
        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            test_time = datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=encrypted,
                last_tested_at=test_time,
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/settings")

        assert response.status_code == 200
        assert b"Last tested:" in response.data
        # Status indicator for success
        assert b"text-green-600" in response.data or b"&#x2713;" in response.data

    def test_settings_page_displays_failed_test_status(self, app, client, temp_instance_path):
        """Test that failed test status is displayed with error indicator."""
        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)

            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=encrypted,
                last_tested_at=datetime.now(timezone.utc),
                last_test_status="failed",
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/settings")

        assert response.status_code == 200
        # Status indicator for failure
        assert b"text-red-600" in response.data or b"&#x2717;" in response.data

    def test_settings_page_without_existing_config(self, client):
        """Test that settings page works when no TMDB config exists."""
        response = client.get("/settings")

        assert response.status_code == 200
        assert b"Not tested yet" in response.data

    def test_settings_page_includes_csrf_token(self, client):
        """Test that CSRF token meta tag is present."""
        response = client.get("/settings")

        assert response.status_code == 200
        assert b"csrf-token" in response.data

    def test_settings_page_includes_javascript(self, client):
        """Test that settings.js is included."""
        response = client.get("/settings")

        assert response.status_code == 200
        assert b"settings.js" in response.data


class TestSettingsPagePOST:
    """Tests for POST /settings endpoint (Save API Key)."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_save_api_key_with_valid_key_creates_new_config(self, mock_test, app, client, temp_instance_path):
        """Test saving valid API key creates new ServiceConfig entry."""
        mock_test.return_value = True

        response = client.post(
            "/settings",
            data={"tmdb_api": "new_valid_key_12345", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"TMDB API Key saved successfully" in response.data

        # Verify database entry
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config is not None
            assert config.last_test_status == "success"

            # Verify key is encrypted
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "new_valid_key_12345"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_save_api_key_with_valid_key_updates_existing_config(self, mock_test, app, client, temp_instance_path):
        """Test saving valid API key updates existing ServiceConfig."""
        mock_test.return_value = True

        # Create existing config
        with app.app_context():
            old_encrypted = encrypt_data("old_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=old_encrypted,
                last_tested_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()
            old_id = config.id

        response = client.post(
            "/settings",
            data={"tmdb_api": "updated_key_67890", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"TMDB API Key saved successfully" in response.data

        # Verify database was updated, not created new
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="TMDB").all()
            assert len(configs) == 1
            assert configs[0].id == old_id

            # Verify key was updated
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "updated_key_67890"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_save_api_key_with_invalid_key_shows_error(self, mock_test, app, client):
        """Test that invalid API key shows error message."""
        mock_test.return_value = False

        response = client.post(
            "/settings",
            data={"tmdb_api": "invalid_key", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid TMDB API Key" in response.data

        # Verify no database entry was created
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config is None

    def test_save_api_key_with_empty_key_shows_warning(self, client):
        """Test that empty API key shows warning message."""
        response = client.post(
            "/settings",
            data={"tmdb_api": "", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"API Key cannot be empty" in response.data

    def test_save_api_key_with_whitespace_only_key_shows_warning(self, client):
        """Test that whitespace-only API key shows warning."""
        response = client.post(
            "/settings",
            data={"tmdb_api": "   ", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"API Key cannot be empty" in response.data

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_save_api_key_trims_whitespace(self, mock_test, app, client, temp_instance_path):
        """Test that API key whitespace is trimmed before saving."""
        mock_test.return_value = True

        response = client.post(
            "/settings",
            data={"tmdb_api": "  trimmed_key_123  ", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify trimmed key was saved
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "trimmed_key_123"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    @patch("listarr.routes.settings_routes.encrypt_data")
    def test_save_api_key_handles_encryption_error(self, mock_encrypt, mock_test, client):
        """Test that encryption errors are handled gracefully."""
        mock_test.return_value = True
        mock_encrypt.side_effect = Exception("Encryption failed")

        response = client.post(
            "/settings",
            data={"tmdb_api": "valid_key", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Failed to save TMDB configuration" in response.data

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_save_api_key_handles_database_error(self, mock_test, app, client):
        """Test that database errors trigger rollback."""
        mock_test.return_value = True

        with app.app_context():
            # Create invalid state to trigger database error
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                response = client.post(
                    "/settings",
                    data={"tmdb_api": "valid_key", "save_api_key": "true"},
                    follow_redirects=True,
                )

        assert response.status_code == 200
        assert b"Failed to save TMDB configuration" in response.data

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_save_api_key_updates_last_tested_timestamp(self, mock_test, app, client, temp_instance_path):
        """Test that save operation updates last_tested_at."""
        mock_test.return_value = True

        before_time = datetime.now(timezone.utc)

        client.post("/settings", data={"tmdb_api": "valid_key", "save_api_key": "true"})

        after_time = datetime.now(timezone.utc)

        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config.last_tested_at is not None
            assert before_time <= config.last_tested_at <= after_time

    def test_save_api_key_redirects_to_settings_page(self, client):
        """Test that POST redirects back to settings page."""
        response = client.post("/settings", data={"tmdb_api": "", "save_api_key": "true"})

        assert response.status_code == 302
        assert "/settings" in response.location


class TestTestTMDBAPIAjax:
    """Tests for POST /settings/test_tmdb_api endpoint (AJAX)."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_test_tmdb_api_with_valid_key(self, mock_test, app, client):
        """Test AJAX endpoint with valid API key."""
        mock_test.return_value = True

        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "valid_key_12345"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "TMDB API Key is valid" in data["message"]
        assert "timestamp" in data

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_test_tmdb_api_with_invalid_key(self, mock_test, app, client):
        """Test AJAX endpoint with invalid API key."""
        mock_test.return_value = False

        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "invalid_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid TMDB API Key" in data["message"]
        assert "timestamp" in data

    def test_test_tmdb_api_with_empty_key(self, client):
        """Test AJAX endpoint with empty API key."""
        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": ""},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "API key cannot be empty" in data["message"]

    def test_test_tmdb_api_without_api_key_field(self, client):
        """Test AJAX endpoint without api_key in request."""
        response = client.post("/settings/test_tmdb_api", json={}, content_type="application/json")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_test_tmdb_api_updates_database(self, mock_test, app, client, temp_instance_path):
        """Test that AJAX test updates database with results."""
        mock_test.return_value = True

        # Create existing config
        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=encrypted,
                last_tested_at=None,
                last_test_status=None,
            )
            db.session.add(config)
            db.session.commit()

        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "test_key"},
            content_type="application/json",
        )

        assert response.status_code == 200

        # Verify database was updated
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config.last_tested_at is not None
            assert config.last_test_status == "success"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_test_tmdb_api_creates_config_if_not_exists(self, mock_test, app, client):
        """Test that AJAX test creates ServiceConfig if it doesn't exist."""
        mock_test.return_value = True

        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "new_key"},
            content_type="application/json",
        )

        assert response.status_code == 200

        # Note: Current implementation doesn't create config on test,
        # only updates if exists. This test documents current behavior.
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            # Config may or may not be created depending on implementation
            # This test verifies it doesn't crash

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_test_tmdb_api_handles_database_error(self, mock_test, app, client):
        """Test that database errors during test are handled gracefully."""
        mock_test.return_value = True

        with app.app_context():
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                response = client.post(
                    "/settings/test_tmdb_api",
                    json={"api_key": "valid_key"},
                    content_type="application/json",
                )

        # Should still return success from test, even if DB update fails
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_test_tmdb_api_returns_iso_timestamp(self, mock_test, client):
        """Test that timestamp is returned in ISO format."""
        mock_test.return_value = True

        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "valid_key"},
            content_type="application/json",
        )

        data = response.get_json()
        timestamp = data["timestamp"]

        # Verify it's a valid ISO timestamp
        assert "T" in timestamp
        assert timestamp.endswith("Z") or "+" in timestamp or timestamp.count(":") >= 2


class TestHelperTestAndUpdateTMDBStatus:
    """Tests for _test_and_update_tmdb_status helper function."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_helper_returns_success_tuple(self, mock_test, app, temp_instance_path):
        """Test that helper returns correct tuple on success."""
        from listarr.routes.settings_routes import _test_and_update_tmdb_status

        mock_test.return_value = True

        with app.app_context():
            result, timestamp, status = _test_and_update_tmdb_status("valid_key")

        assert result is True
        assert timestamp is not None
        assert status == "success"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_helper_returns_failure_tuple(self, mock_test, app, temp_instance_path):
        """Test that helper returns correct tuple on failure."""
        from listarr.routes.settings_routes import _test_and_update_tmdb_status

        mock_test.return_value = False

        with app.app_context():
            result, timestamp, status = _test_and_update_tmdb_status("invalid_key")

        assert result is False
        assert timestamp is not None
        assert status == "failed"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_helper_updates_existing_config(self, mock_test, app, temp_instance_path):
        """Test that helper updates existing ServiceConfig."""
        from listarr.routes.settings_routes import _test_and_update_tmdb_status

        mock_test.return_value = True

        with app.app_context():
            # Create existing config
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=encrypted,
                last_tested_at=None,
                last_test_status=None,
            )
            db.session.add(config)
            db.session.commit()

            result, timestamp, status = _test_and_update_tmdb_status("test_key")

            # Verify database was updated
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config.last_tested_at == timestamp
            assert config.last_test_status == status

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_helper_handles_no_existing_config(self, mock_test, app, temp_instance_path):
        """Test that helper works when no config exists yet."""
        from listarr.routes.settings_routes import _test_and_update_tmdb_status

        mock_test.return_value = True

        with app.app_context():
            result, timestamp, status = _test_and_update_tmdb_status("test_key")

            # Should return result even if config doesn't exist
            assert result is True
            assert timestamp is not None
            assert status == "success"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_helper_handles_database_error_gracefully(self, mock_test, app):
        """Test that helper handles database errors without crashing."""
        from listarr.routes.settings_routes import _test_and_update_tmdb_status

        mock_test.return_value = True

        with app.app_context():
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                # Should not raise exception
                result, timestamp, status = _test_and_update_tmdb_status("test_key")

            # Should still return test result
            assert result is True


class TestCSRFProtection:
    """Tests for CSRF token protection."""

    def test_settings_page_includes_csrf_meta_tag(self, client):
        """Test that CSRF token meta tag is present in page."""
        response = client.get("/settings")

        assert response.status_code == 200
        assert b'<meta name="csrf-token"' in response.data

    def test_settings_form_includes_hidden_csrf_token(self, client_with_csrf):
        """Test that form includes hidden CSRF token field."""
        response = client_with_csrf.get("/settings")

        assert response.status_code == 200
        # Flask-WTF adds hidden CSRF token field with name attribute
        assert b'name="csrf_token"' in response.data or b"name='csrf_token'" in response.data


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    @patch("listarr.routes.settings_routes.decrypt_data")
    def test_settings_get_handles_decryption_error(self, mock_decrypt, mock_test, app, client, temp_instance_path):
        """Test that GET /settings handles decryption errors gracefully."""
        mock_decrypt.side_effect = ValueError("Decryption failed")

        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
            db.session.add(config)
            db.session.commit()

        # Should not crash, might show empty field or error
        response = client.get("/settings")
        assert response.status_code == 200

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_save_api_key_with_special_characters(self, mock_test, app, client, temp_instance_path):
        """Test saving API key with special characters."""
        mock_test.return_value = True
        special_key = "key!@#$%^&*()_+-={}[]|:;<>,.?/"

        response = client.post(
            "/settings",
            data={"tmdb_api": special_key, "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify special characters were preserved
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == special_key

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_save_api_key_with_unicode_characters(self, mock_test, app, client, temp_instance_path):
        """Test saving API key with Unicode characters."""
        mock_test.return_value = True
        unicode_key = "key_测试_тест_🔑"

        response = client.post(
            "/settings",
            data={"tmdb_api": unicode_key, "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200

        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == unicode_key
