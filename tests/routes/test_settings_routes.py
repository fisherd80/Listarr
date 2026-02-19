"""
Route tests for settings_routes.py - Settings page endpoints.

Tests cover:
- GET /settings - Page rendering, existing TMDB config display, error handling
- POST /settings - Save TMDB API key (form submission)
- POST /settings/test_tmdb_api - AJAX connection testing

Note: /settings/change-password tests are in test_auth_routes.py (Plan 03)
because that endpoint requires real authentication (current_user.check_password),
which is incompatible with the LOGIN_DISABLED=True app fixture used here.

Isolation pattern: Use db.session directly (no nested with app.app_context()
blocks). The session-scoped app fixture keeps an app context open for the
entire session; nested contexts corrupt Flask's ContextVar stack.

For POST to /settings, use data={} (form data via WTForms request.form).
For POST to /settings/test_tmdb_api, use json={} (JSON body via request.json).
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from cryptography.fernet import InvalidToken

from listarr import db
from listarr.models.service_config_model import ServiceConfig
from listarr.services.crypto_utils import decrypt_data, encrypt_data


class TestSettingsPageGET:
    """Tests for GET /settings endpoint."""

    def test_renders_settings_page(self, client):
        """Settings page renders with 200 status."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Settings" in response.data
        assert b"TMDB" in response.data

    def test_shows_existing_tmdb_config(self, client, app, temp_instance_path):
        """Form is pre-populated when TMDB config exists."""
        encrypted = encrypt_data("existing_key_12345", instance_path=temp_instance_path)
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
        assert b"existing_key_12345" in response.data

    def test_shows_not_tested_when_no_config(self, client):
        """Shows 'Not tested yet' when no TMDB config exists."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Not tested yet" in response.data

    def test_handles_decryption_error(self, client, app, temp_instance_path):
        """Handles InvalidToken during decryption without crashing."""
        encrypted = encrypt_data("some_key", instance_path=temp_instance_path)
        config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
        db.session.add(config)
        db.session.commit()

        with patch("listarr.routes.settings_routes.decrypt_data") as mock_decrypt:
            mock_decrypt.side_effect = InvalidToken
            response = client.get("/settings")

        assert response.status_code == 200

    def test_includes_csrf_token(self, client):
        """Settings page includes CSRF token meta tag."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert b"csrf-token" in response.data

    def test_includes_javascript(self, client):
        """Settings page includes settings.js."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert b"settings.js" in response.data


class TestSettingsPagePOST:
    """Tests for POST /settings endpoint (save_api_key)."""

    def test_saves_valid_api_key(self, client, app, temp_instance_path):
        """Valid API key is saved and DB record created."""
        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = True
            response = client.post(
                "/settings",
                data={"save_api_key": "1", "tmdb_api": "valid_test_key_123", "tmdb_region": ""},
                follow_redirects=True,
            )

        assert response.status_code == 200
        assert b"TMDB API Key saved successfully" in response.data
        config = ServiceConfig.query.filter_by(service="TMDB").first()
        assert config is not None
        assert config.last_test_status == "success"
        decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
        assert decrypted == "valid_test_key_123"

    def test_rejects_invalid_api_key(self, client, app):
        """Invalid API key shows error and no DB record is created."""
        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = False
            response = client.post(
                "/settings",
                data={"save_api_key": "1", "tmdb_api": "bad_key", "tmdb_region": ""},
                follow_redirects=True,
            )

        assert response.status_code == 200
        assert b"Invalid TMDB API Key" in response.data
        config = ServiceConfig.query.filter_by(service="TMDB").first()
        assert config is None

    def test_warns_on_empty_api_key(self, client):
        """Empty API key shows warning flash message."""
        response = client.post(
            "/settings",
            data={"save_api_key": "1", "tmdb_api": "", "tmdb_region": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"API Key cannot be empty" in response.data

    def test_creates_new_config_when_none_exists(self, client, app):
        """Creates a new ServiceConfig when none exists for TMDB."""
        assert ServiceConfig.query.filter_by(service="TMDB").first() is None

        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = True
            client.post(
                "/settings",
                data={"save_api_key": "1", "tmdb_api": "new_key", "tmdb_region": ""},
                follow_redirects=True,
            )

        config = ServiceConfig.query.filter_by(service="TMDB").first()
        assert config is not None

    def test_updates_existing_config(self, client, app, temp_instance_path):
        """Updates existing ServiceConfig rather than creating a duplicate."""
        encrypted = encrypt_data("old_key", instance_path=temp_instance_path)
        existing = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
        db.session.add(existing)
        db.session.commit()
        original_id = existing.id

        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = True
            client.post(
                "/settings",
                data={"save_api_key": "1", "tmdb_api": "updated_key", "tmdb_region": ""},
                follow_redirects=True,
            )

        configs = ServiceConfig.query.filter_by(service="TMDB").all()
        assert len(configs) == 1
        assert configs[0].id == original_id
        decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
        assert decrypted == "updated_key"

    def test_handles_db_error_on_save(self, client, app):
        """DB error during commit shows error message."""
        from sqlalchemy.exc import OperationalError

        with (
            patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate,
            patch("listarr.routes.settings_routes.encrypt_data") as mock_encrypt,
        ):
            mock_validate.return_value = True
            mock_encrypt.side_effect = RuntimeError("Encryption error")
            response = client.post(
                "/settings",
                data={"save_api_key": "1", "tmdb_api": "some_key", "tmdb_region": ""},
                follow_redirects=True,
            )

        assert response.status_code == 200
        assert b"Failed to save TMDB configuration" in response.data

    def test_saves_region_setting(self, client, app, temp_instance_path):
        """tmdb_region is saved alongside the API key."""
        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = True
            client.post(
                "/settings",
                data={"save_api_key": "1", "tmdb_api": "key_with_region", "tmdb_region": "US"},
                follow_redirects=True,
            )

        config = ServiceConfig.query.filter_by(service="TMDB").first()
        assert config is not None
        assert config.tmdb_region == "US"

    def test_redirects_to_settings_on_empty_key(self, client):
        """POST with empty key redirects back to /settings (302)."""
        response = client.post(
            "/settings",
            data={"save_api_key": "1", "tmdb_api": "", "tmdb_region": ""},
        )
        assert response.status_code == 302
        assert "/settings" in response.location


class TestTmdbApiTest:
    """Tests for POST /settings/test_tmdb_api endpoint."""

    def test_valid_key_returns_success(self, client):
        """Valid API key returns success JSON."""
        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = True
            response = client.post(
                "/settings/test_tmdb_api",
                json={"api_key": "valid_key_123"},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "TMDB API Key is valid" in data["message"]
        assert "timestamp" in data

    def test_invalid_key_returns_failure(self, client):
        """Invalid API key returns failure JSON."""
        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = False
            response = client.post(
                "/settings/test_tmdb_api",
                json={"api_key": "bad_key"},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid" in data["message"]

    def test_empty_key_returns_error(self, client):
        """Empty API key returns error without calling validate."""
        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": ""},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "cannot be empty" in data["message"].lower()

    def test_updates_db_timestamp_on_test(self, client, app, temp_instance_path):
        """Test result updates last_tested_at and last_test_status in DB."""
        encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="TMDB",
            api_key_encrypted=encrypted,
            last_tested_at=None,
            last_test_status=None,
        )
        db.session.add(config)
        db.session.commit()

        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = True
            client.post(
                "/settings/test_tmdb_api",
                json={"api_key": "test_key"},
            )

        updated = ServiceConfig.query.filter_by(service="TMDB").first()
        assert updated.last_tested_at is not None
        assert updated.last_test_status == "success"
