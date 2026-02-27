"""
Route tests for settings_routes.py - Settings page and config API endpoints.

Tests cover:
- GET /settings - 3-tab settings page (Integrations, TMDB, Account)
- POST /settings/test_tmdb_api - AJAX TMDB connection testing
- POST /api/settings/test_radarr_api - AJAX Radarr connection testing
- POST /api/settings/test_sonarr_api - AJAX Sonarr connection testing
- GET /api/settings/<service>/quality-profiles - Fetch quality profiles
- GET /api/settings/<service>/root-folders - Fetch root folders
- GET/POST /api/settings/<service>/import-settings - Import settings management

Note: /settings/change-password tests are in test_auth_routes.py (Plan 03)
because that endpoint requires real authentication (current_user.check_password),
which is incompatible with the LOGIN_DISABLED=True app fixture used here.

Isolation pattern: Use db.session directly (no nested with app.app_context()
blocks). The session-scoped app fixture keeps an app context open for the
entire session; nested contexts corrupt Flask's ContextVar stack.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from listarr import db
from listarr.models.service_config_model import MediaImportSettings, ServiceConfig
from listarr.services.crypto_utils import encrypt_data


class TestSettingsPage:
    """Tests for GET /settings 3-tab settings page."""

    def test_settings_page_returns_200(self, client):
        """Settings page renders with 200 status."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Settings" in response.data

    def test_settings_page_has_three_tabs(self, client):
        """Settings page has 3 tab buttons: Integrations, TMDB, Account. No General tab."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Integrations" in response.data
        assert b"TMDB" in response.data
        assert b"Account" in response.data
        assert b"General" not in response.data


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


# ---------------------------------------------------------------------------
# Config API tests (migrated from test_config_routes.py, URLs at /api/settings/*)
# ---------------------------------------------------------------------------


class TestTestRadarrAPIAjax:
    """Tests for POST /api/settings/test_radarr_api endpoint (AJAX)."""

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_test_radarr_empty_key_uses_stored(self, mock_validate, app, client, temp_instance_path):
        """Empty api_key uses stored Radarr key from DB — returns success."""
        encrypted = encrypt_data("stored_radarr_key_9999", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_validate.return_value = True
        response = client.post(
            "/api/settings/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": ""},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_test_radarr_api_with_valid_credentials(self, mock_test, app, client):
        """Test AJAX endpoint with valid Radarr credentials."""
        mock_test.return_value = True

        response = client.post(
            "/api/settings/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": "valid_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Radarr connection successful" in data["message"]
        assert "timestamp" in data

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_test_radarr_api_with_invalid_credentials(self, mock_test, app, client):
        """Test AJAX endpoint with invalid Radarr credentials."""
        mock_test.return_value = False

        response = client.post(
            "/api/settings/test_radarr_api",
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
            "/api/settings/test_radarr_api",
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
            "/api/settings/test_radarr_api",
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
            "/api/settings/test_radarr_api",
            json={"base_url": "not-a-url", "api_key": "some_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid URL format" in data["message"]

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_test_radarr_api_updates_database(self, mock_test, app, client, temp_instance_path):
        """Test that AJAX test updates database with results."""
        mock_test.return_value = True

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
            "/api/settings/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": "test_key"},
            content_type="application/json",
        )

        assert response.status_code == 200

        config = ServiceConfig.query.filter_by(service="RADARR").first()
        assert config.last_tested_at is not None
        assert config.last_test_status == "success"

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_test_radarr_api_handles_database_error(self, mock_test, app, client):
        """Test that database errors during test are handled gracefully."""
        mock_test.return_value = True

        with patch.object(db.session, "commit", side_effect=OperationalError("DB error", None, None)):
            response = client.post(
                "/api/settings/test_radarr_api",
                json={"base_url": "http://localhost:7878", "api_key": "valid_key"},
                content_type="application/json",
            )

        # Should still return success from test, even if DB update fails
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_test_radarr_api_returns_iso_timestamp(self, mock_test, client):
        """Test that timestamp is returned in ISO format."""
        mock_test.return_value = True

        response = client.post(
            "/api/settings/test_radarr_api",
            json={"base_url": "http://localhost:7878", "api_key": "valid_key"},
            content_type="application/json",
        )

        data = response.get_json()
        timestamp = data["timestamp"]

        # Verify it's a valid ISO timestamp
        assert "T" in timestamp
        assert timestamp.endswith("Z") or "+" in timestamp or timestamp.count(":") >= 2


class TestTestSonarrAPIAjax:
    """Tests for POST /api/settings/test_sonarr_api endpoint (AJAX)."""

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_test_sonarr_api_with_valid_credentials(self, mock_test, app, client):
        """Test AJAX endpoint with valid Sonarr credentials."""
        mock_test.return_value = True

        response = client.post(
            "/api/settings/test_sonarr_api",
            json={"base_url": "http://localhost:8989", "api_key": "valid_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Sonarr connection successful" in data["message"]
        assert "timestamp" in data

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_test_sonarr_api_with_invalid_credentials(self, mock_test, app, client):
        """Test AJAX endpoint with invalid Sonarr credentials."""
        mock_test.return_value = False

        response = client.post(
            "/api/settings/test_sonarr_api",
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
            "/api/settings/test_sonarr_api",
            json={"base_url": "invalid-format", "api_key": "some_key"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid URL format" in data["message"]


class TestRadarrQualityProfilesEndpoint:
    """Tests for GET /api/settings/radarr/quality-profiles endpoint."""

    @patch("listarr.routes.settings_routes.get_quality_profiles")
    def test_fetch_radarr_quality_profiles_success(self, mock_get_profiles, app, client, temp_instance_path):
        """Test fetching Radarr quality profiles successfully."""
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

        response = client.get("/api/settings/radarr/quality-profiles")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["profiles"]) == 2
        assert data["profiles"][0]["name"] == "HD-1080p"

    def test_fetch_radarr_quality_profiles_without_config(self, client):
        """Test fetching quality profiles when Radarr not configured."""
        response = client.get("/api/settings/radarr/quality-profiles")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Radarr not configured" in data["message"]

    @patch("listarr.routes.settings_routes.get_quality_profiles")
    def test_fetch_radarr_quality_profiles_api_failure(self, mock_get_profiles, app, client, temp_instance_path):
        """Test handling of API failure when fetching quality profiles."""
        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_get_profiles.return_value = []

        response = client.get("/api/settings/radarr/quality-profiles")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch quality profiles" in data["message"]

    @patch("listarr.routes.settings_routes.decrypt_data")
    def test_fetch_radarr_quality_profiles_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test handling when decryption fails for quality profiles."""
        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_decrypt.side_effect = ValueError("Decryption failed")

        response = client.get("/api/settings/radarr/quality-profiles")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed" in data["message"]


class TestRadarrRootFoldersEndpoint:
    """Tests for GET /api/settings/radarr/root-folders endpoint."""

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_fetch_radarr_root_folders_success(self, mock_get_folders, app, client, temp_instance_path):
        """Test fetching Radarr root folders successfully."""
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

        response = client.get("/api/settings/radarr/root-folders")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["folders"]) == 2
        assert data["folders"][0]["path"] == "/movies"

    def test_fetch_radarr_root_folders_without_config(self, client):
        """Test fetching root folders when Radarr not configured."""
        response = client.get("/api/settings/radarr/root-folders")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Radarr not configured" in data["message"]

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_fetch_radarr_root_folders_api_failure(self, mock_get_folders, app, client, temp_instance_path):
        """Test handling of API failure when fetching root folders."""
        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_get_folders.return_value = []

        response = client.get("/api/settings/radarr/root-folders")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch root folders" in data["message"]

    @patch("listarr.routes.settings_routes.decrypt_data")
    def test_fetch_radarr_root_folders_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test handling when decryption fails for root folders."""
        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_decrypt.side_effect = ValueError("Decryption failed")

        response = client.get("/api/settings/radarr/root-folders")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed" in data["message"]


class TestRadarrImportSettingsEndpoints:
    """Tests for Radarr import settings GET and POST endpoints."""

    def test_fetch_radarr_import_settings_when_none_exist(self, client):
        """Test fetching import settings when none exist."""
        response = client.get("/api/settings/radarr/import-settings")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["settings"] is None

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_fetch_radarr_import_settings_when_exist(self, mock_root_folders, app, client, temp_instance_path):
        """Test fetching existing import settings (returns ID from stored path)."""
        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)

        settings = MediaImportSettings(
            service="RADARR",
            root_folder="/movies",
            quality_profile_id=1,
            monitored=True,
            search_on_add=False,
        )
        db.session.add(settings)
        db.session.commit()

        mock_root_folders.return_value = [
            {"id": 5, "path": "/movies"},
            {"id": 6, "path": "/other"},
        ]

        response = client.get("/api/settings/radarr/import-settings")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["settings"]["root_folder_id"] == 5
        assert data["settings"]["quality_profile_id"] == 1
        assert data["settings"]["monitored"] is True
        assert data["settings"]["search_on_add"] is False

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_save_radarr_import_settings_creates_new(self, mock_root_folders, app, client, temp_instance_path):
        """Test saving new Radarr import settings (stores path from ID)."""
        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_root_folders.return_value = [
            {"id": 5, "path": "/movies"},
            {"id": 6, "path": "/other"},
        ]

        response = client.post(
            "/api/settings/radarr/import-settings",
            json={
                "root_folder_id": 5,
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        settings = MediaImportSettings.query.filter_by(service="RADARR").first()
        assert settings is not None
        assert settings.root_folder == "/movies"
        assert settings.quality_profile_id == 1

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_save_radarr_import_settings_updates_existing(self, mock_root_folders, app, client, temp_instance_path):
        """Test updating existing Radarr import settings."""
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

        mock_root_folders.return_value = [
            {"id": 7, "path": "/new"},
            {"id": 8, "path": "/other"},
        ]

        response = client.post(
            "/api/settings/radarr/import-settings",
            json={
                "root_folder_id": 7,
                "quality_profile_id": 2,
                "monitored": False,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 200

        all_settings = MediaImportSettings.query.filter_by(service="RADARR").all()
        assert len(all_settings) == 1
        assert all_settings[0].id == settings_id
        assert all_settings[0].root_folder == "/new"

    def test_save_radarr_import_settings_validates_required_fields(self, client):
        """Test that required fields are validated."""
        response = client.post(
            "/api/settings/radarr/import-settings",
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
            "/api/settings/radarr/import-settings",
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
            "/api/settings/radarr/import-settings",
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

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_save_radarr_import_settings_handles_database_error(
        self, mock_root_folders, app, client, temp_instance_path
    ):
        """Test handling of database errors during save."""
        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_root_folders.return_value = [{"id": 5, "path": "/movies"}]

        with patch.object(db.session, "commit", side_effect=OperationalError("DB error", None, None)):
            response = client.post(
                "/api/settings/radarr/import-settings",
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
    """Tests for GET /api/settings/sonarr/quality-profiles endpoint."""

    @patch("listarr.routes.settings_routes.get_quality_profiles")
    def test_fetch_sonarr_quality_profiles_success(self, mock_get_profiles, app, client, temp_instance_path):
        """Test fetching Sonarr quality profiles successfully."""
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

        response = client.get("/api/settings/sonarr/quality-profiles")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["profiles"]) == 2

    def test_fetch_sonarr_quality_profiles_without_config(self, client):
        """Test fetching quality profiles when Sonarr not configured."""
        response = client.get("/api/settings/sonarr/quality-profiles")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Sonarr not configured" in data["message"]

    @patch("listarr.routes.settings_routes.get_quality_profiles")
    def test_fetch_sonarr_quality_profiles_api_failure(self, mock_get_profiles, app, client, temp_instance_path):
        """Test handling of API failure when fetching quality profiles."""
        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_get_profiles.return_value = []

        response = client.get("/api/settings/sonarr/quality-profiles")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch quality profiles" in data["message"]

    @patch("listarr.routes.settings_routes.decrypt_data")
    def test_fetch_sonarr_quality_profiles_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test handling when decryption fails for quality profiles."""
        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_decrypt.side_effect = ValueError("Decryption failed")

        response = client.get("/api/settings/sonarr/quality-profiles")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed" in data["message"]


class TestSonarrRootFoldersEndpoint:
    """Tests for GET /api/settings/sonarr/root-folders endpoint."""

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_fetch_sonarr_root_folders_success(self, mock_get_folders, app, client, temp_instance_path):
        """Test fetching Sonarr root folders successfully."""
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

        response = client.get("/api/settings/sonarr/root-folders")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["folders"]) == 2

    def test_fetch_sonarr_root_folders_without_config(self, client):
        """Test fetching root folders when Sonarr not configured."""
        response = client.get("/api/settings/sonarr/root-folders")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Sonarr not configured" in data["message"]

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_fetch_sonarr_root_folders_api_failure(self, mock_get_folders, app, client, temp_instance_path):
        """Test handling of API failure when fetching root folders."""
        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_get_folders.return_value = []

        response = client.get("/api/settings/sonarr/root-folders")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch root folders" in data["message"]

    @patch("listarr.routes.settings_routes.decrypt_data")
    def test_fetch_sonarr_root_folders_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test handling when decryption fails for root folders."""
        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_decrypt.side_effect = ValueError("Decryption failed")

        response = client.get("/api/settings/sonarr/root-folders")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed" in data["message"]


class TestSonarrImportSettingsEndpoints:
    """Tests for Sonarr import settings GET and POST endpoints."""

    def test_fetch_sonarr_import_settings_when_none_exist(self, client):
        """Test fetching Sonarr import settings when none exist."""
        response = client.get("/api/settings/sonarr/import-settings")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["settings"] is None

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_fetch_sonarr_import_settings_when_exist(self, mock_root_folders, app, client, temp_instance_path):
        """Test fetching existing Sonarr import settings (returns ID from stored path)."""
        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)

        settings = MediaImportSettings(
            service="SONARR",
            root_folder="/tv",
            quality_profile_id=1,
            monitored=True,
            season_folder=True,
            search_on_add=False,
        )
        db.session.add(settings)
        db.session.commit()

        mock_root_folders.return_value = [
            {"id": 3, "path": "/tv"},
            {"id": 4, "path": "/other"},
        ]

        response = client.get("/api/settings/sonarr/import-settings")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["settings"]["root_folder_id"] == 3
        assert data["settings"]["season_folder"] is True

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_save_sonarr_import_settings_creates_new(self, mock_root_folders, app, client, temp_instance_path):
        """Test saving new Sonarr import settings (stores path from ID)."""
        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_root_folders.return_value = [
            {"id": 3, "path": "/tv"},
            {"id": 4, "path": "/other"},
        ]

        response = client.post(
            "/api/settings/sonarr/import-settings",
            json={
                "root_folder_id": 3,
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

        settings = MediaImportSettings.query.filter_by(service="SONARR").first()
        assert settings is not None
        assert settings.root_folder == "/tv"
        assert settings.season_folder is True

    def test_save_sonarr_import_settings_validates_season_folder_required(self, client):
        """Test that season_folder is required for Sonarr."""
        response = client.post(
            "/api/settings/sonarr/import-settings",
            json={
                "root_folder_id": "/tv",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": False,
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
            "/api/settings/sonarr/import-settings",
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

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_save_sonarr_import_settings_updates_existing(self, mock_root_folders, app, client, temp_instance_path):
        """Test updating existing Sonarr import settings."""
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

        mock_root_folders.return_value = [
            {"id": 5, "path": "/new"},
            {"id": 6, "path": "/other"},
        ]

        response = client.post(
            "/api/settings/sonarr/import-settings",
            json={
                "root_folder_id": 5,
                "quality_profile_id": 2,
                "monitored": False,
                "season_folder": False,
                "search_on_add": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 200

        all_settings = MediaImportSettings.query.filter_by(service="SONARR").all()
        assert len(all_settings) == 1
        assert all_settings[0].id == settings_id
        assert all_settings[0].root_folder == "/new"

    @patch("listarr.routes.settings_routes.get_root_folders")
    def test_save_sonarr_import_settings_handles_database_error(
        self, mock_root_folders, app, client, temp_instance_path
    ):
        """Test handling of database errors during save."""
        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        mock_root_folders.return_value = [{"id": 3, "path": "/tv"}]

        with patch.object(db.session, "commit", side_effect=OperationalError("DB error", None, None)):
            response = client.post(
                "/api/settings/sonarr/import-settings",
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
            "/api/settings/sonarr/import-settings",
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
    """Tests for helper functions in settings_routes."""

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_helper_test_and_update_service_status_returns_success_tuple_radarr(
        self, mock_test, app, temp_instance_path
    ):
        """Test that service helper returns correct tuple on success for Radarr."""
        from listarr.routes.settings_routes import _test_and_update_service_status

        mock_test.return_value = True

        result, timestamp, status = _test_and_update_service_status("RADARR", "http://localhost:7878", "valid_key")

        assert result is True
        assert timestamp is not None
        assert status == "success"

    @patch("listarr.routes.settings_routes.validate_api_key")
    def test_helper_test_and_update_service_status_returns_failure_tuple_sonarr(
        self, mock_test, app, temp_instance_path
    ):
        """Test that service helper returns correct tuple on failure for Sonarr."""
        from listarr.routes.settings_routes import _test_and_update_service_status

        mock_test.return_value = False

        result, timestamp, status = _test_and_update_service_status("SONARR", "http://localhost:8989", "invalid_key")

        assert result is False
        assert timestamp is not None
        assert status == "failed"

    def test_helper_is_valid_url_with_valid_urls(self):
        """Test URL validation helper with valid URLs."""
        from listarr.routes.settings_routes import _is_valid_url

        assert _is_valid_url("http://localhost:7878") is True
        assert _is_valid_url("https://radarr.example.com") is True
        assert _is_valid_url("http://192.168.1.100:7878") is True

    def test_helper_is_valid_url_with_invalid_urls(self):
        """Test URL validation helper with invalid URLs."""
        from listarr.routes.settings_routes import _is_valid_url

        assert _is_valid_url("not-a-url") is False
        assert _is_valid_url("localhost:7878") is False
        assert _is_valid_url("") is False
        assert _is_valid_url("just-text") is False

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("http://localhost:7878/", True),
            ("http://192.168.1.1:7878", True),
            ("https://radarr.example.com/api", True),
            ("http://localhost:7878?test=1", True),
            ("http://[::1]:7878", True),
            ("localhost:7878", False),
            ("http://", False),
            ("https://radarr.example.com:7878", True),
            ("http://127.0.0.1:7878", True),
        ],
    )
    def test_helper_is_valid_url_edge_cases(self, url, expected):
        """Test URL validation with various edge cases."""
        from listarr.routes.settings_routes import _is_valid_url

        assert _is_valid_url(url) == expected


# ---------------------------------------------------------------------------
# New connection-save endpoint tests (Plan 03-01)
# ---------------------------------------------------------------------------


class TestSaveRadarrConnection:
    """Tests for POST /api/settings/radarr/connection."""

    def test_save_empty_api_key_uses_stored_key(self, client, app, temp_instance_path):
        """POST with empty api_key returns 200 if a stored encrypted key exists (fallback)."""
        encrypted = encrypt_data("stored_api_key_1234", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.routes.settings_routes.validate_api_key") as mock_validate,
            patch("listarr.routes.settings_routes.encrypt_data") as mock_encrypt,
        ):
            mock_validate.return_value = True
            mock_encrypt.return_value = "re_encrypted_key"
            response = client.post(
                "/api/settings/radarr/connection",
                json={"base_url": "http://localhost:7878", "api_key": ""},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_save_empty_api_key_no_stored_key_returns_400(self, client):
        """POST with empty api_key and no pre-configured service returns 400."""
        response = client.post(
            "/api/settings/radarr/connection",
            json={"base_url": "http://localhost:7878", "api_key": ""},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_save_valid_connection(self, client, app):
        """Successful connection test + save returns success JSON."""
        with (
            patch("listarr.routes.settings_routes.validate_api_key") as mock_validate,
            patch("listarr.routes.settings_routes.encrypt_data") as mock_encrypt,
        ):
            mock_validate.return_value = True
            mock_encrypt.return_value = "encrypted_key"
            response = client.post(
                "/api/settings/radarr/connection",
                json={"base_url": "http://localhost:7878", "api_key": "testapikey1234"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["key_last4"] == "1234"

    def test_save_empty_fields_returns_400(self, client):
        """Empty URL or API key returns 400."""
        response = client.post(
            "/api/settings/radarr/connection",
            json={"base_url": "", "api_key": ""},
        )
        assert response.status_code == 400

    def test_save_invalid_url_returns_400(self, client):
        """Invalid URL format returns 400."""
        response = client.post(
            "/api/settings/radarr/connection",
            json={"base_url": "not-a-url", "api_key": "key123"},
        )
        assert response.status_code == 400

    def test_save_test_fails_returns_test_failed(self, client):
        """Failed connection test returns test_failed flag for save-anyway UX."""
        with patch("listarr.routes.settings_routes.validate_api_key") as mock_validate:
            mock_validate.return_value = False
            response = client.post(
                "/api/settings/radarr/connection",
                json={"base_url": "http://localhost:7878", "api_key": "badkey1234"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert data["test_failed"] is True

    def test_force_save_bypasses_test(self, client, app):
        """force_save=True saves even without testing."""
        with patch("listarr.routes.settings_routes.encrypt_data") as mock_encrypt:
            mock_encrypt.return_value = "encrypted_key"
            response = client.post(
                "/api/settings/radarr/connection",
                json={"base_url": "http://localhost:7878", "api_key": "key1234", "force_save": True},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_invalid_service_returns_400(self, client):
        """Non-radarr/sonarr service returns 400."""
        response = client.post(
            "/api/settings/plex/connection",
            json={"base_url": "http://localhost", "api_key": "key"},
        )
        assert response.status_code == 400


class TestSaveSonarrConnection:
    """Tests for POST /api/settings/sonarr/connection."""

    def test_save_valid_sonarr_connection(self, client, app):
        """Successful connection test + save returns success JSON."""
        with (
            patch("listarr.routes.settings_routes.validate_api_key") as mock_validate,
            patch("listarr.routes.settings_routes.encrypt_data") as mock_encrypt,
        ):
            mock_validate.return_value = True
            mock_encrypt.return_value = "encrypted_key"
            response = client.post(
                "/api/settings/sonarr/connection",
                json={"base_url": "http://localhost:8989", "api_key": "sonarrkey1234"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["key_last4"] == "1234"


class TestSaveTmdbSettings:
    """Tests for POST /api/settings/tmdb."""

    def test_save_empty_api_key_uses_stored_key(self, client, app, temp_instance_path):
        """POST with empty api_key returns 200 if a stored encrypted TMDB key exists (fallback)."""
        encrypted = encrypt_data("stored_tmdb_key_5678", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="TMDB",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate,
            patch("listarr.routes.settings_routes.encrypt_data") as mock_encrypt,
        ):
            mock_validate.return_value = True
            mock_encrypt.return_value = "re_encrypted_key"
            response = client.post(
                "/api/settings/tmdb",
                json={"api_key": "", "region": "US"},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_save_valid_tmdb_settings(self, client, app):
        """Successful TMDB save returns success JSON."""
        with (
            patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate,
            patch("listarr.routes.settings_routes.encrypt_data") as mock_encrypt,
        ):
            mock_validate.return_value = True
            mock_encrypt.return_value = "encrypted_key"
            response = client.post(
                "/api/settings/tmdb",
                json={"api_key": "tmdbkey12345678", "region": "US"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_save_empty_api_key_returns_400(self, client):
        """Empty API key returns 400."""
        response = client.post("/api/settings/tmdb", json={"api_key": "", "region": "US"})
        assert response.status_code == 400

    def test_save_test_fails_returns_test_failed(self, client):
        """Failed TMDB connection test returns test_failed flag."""
        with patch("listarr.routes.settings_routes.validate_tmdb_api_key") as mock_validate:
            mock_validate.return_value = False
            response = client.post(
                "/api/settings/tmdb",
                json={"api_key": "badtmdbkey1234", "region": "US"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert data["test_failed"] is True

    def test_force_save_bypasses_test(self, client, app):
        """force_save=True saves without testing the TMDB key."""
        with patch("listarr.routes.settings_routes.encrypt_data") as mock_encrypt:
            mock_encrypt.return_value = "encrypted_key"
            response = client.post(
                "/api/settings/tmdb",
                json={"api_key": "tmdbkey12345678", "region": "", "force_save": True},
            )
        assert response.status_code == 200
        assert response.get_json()["success"] is True


class TestSettingsPageContext:
    """Tests for enriched GET /settings context (Plan 03-01)."""

    def test_settings_page_with_configured_service(self, client, app):
        """Configured service shows without error in rendered page."""
        enc_key = encrypt_data("my_radarr_api_key", instance_path=app.instance_path)
        cfg = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=enc_key,
            last_test_status="success",
        )
        db.session.add(cfg)
        db.session.commit()
        response = client.get("/settings")
        assert response.status_code == 200

    def test_settings_page_unconfigured_renders(self, client):
        """Page renders when no services configured."""
        response = client.get("/settings")
        assert response.status_code == 200
