"""
Integration tests for Settings functionality.

Tests cover:
- TMDB API integration with real mocking (test_tmdb_api endpoint)
- Database operations with encryption
- Error recovery and rollback scenarios
- Timestamp tracking across requests

Note: POST /settings form submission tests removed — settings_page() is now a
GET-only stub (Phase 3 will implement real settings forms with AJAX submission).
"""

from datetime import datetime, timezone
from unittest.mock import patch

from listarr import db
from listarr.models.service_config_model import ServiceConfig
from listarr.services.crypto_utils import encrypt_data


class TestSettingsEndToEndWorkflow:
    """Integration tests for complete settings AJAX workflows."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_failed_test_then_successful_test_workflow(self, mock_test, app, client):
        """Test workflow: failed test, fix key, successful test."""
        # Step 1: Test with invalid key
        mock_test.return_value = False
        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "invalid_key"},
            content_type="application/json",
        )

        data = response.get_json()
        assert data["success"] is False

        # Step 2: Test with valid key
        mock_test.return_value = True
        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "valid_key"},
            content_type="application/json",
        )

        data = response.get_json()
        assert data["success"] is True


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_database_rollback_on_save_error(self, mock_test, app, client, temp_instance_path):
        """Test that database rollback works on save errors."""
        mock_test.return_value = True

        with app.app_context():
            # Create initial config
            encrypted = encrypt_data("original_key", instance_path=temp_instance_path)
            config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
            db.session.add(config)
            db.session.commit()

            # Force commit to fail
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                client.post(
                    "/settings/test_tmdb_api",
                    json={"api_key": "test_key"},
                    content_type="application/json",
                )

            # Verify original config is still intact
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config is not None

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_database_rollback_on_test_error(self, mock_test, app, client, temp_instance_path):
        """Test that database rollback works on AJAX test errors."""
        mock_test.return_value = True

        with app.app_context():
            # Create initial config
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=encrypted,
                last_tested_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()
            original_time = config.last_tested_at

            # Force commit to fail during test update
            with patch.object(db.session, "commit", side_effect=Exception("DB error")):
                client.post(
                    "/settings/test_tmdb_api",
                    json={"api_key": "test_key"},
                    content_type="application/json",
                )

            # Verify original timestamp is intact (rollback worked)
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config.last_tested_at == original_time


class TestTimestampTracking:
    """Integration tests for timestamp tracking."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_timestamp_updated_on_each_test(self, mock_test, app, client, temp_instance_path):
        """Test that last_tested_at is updated on each test."""
        mock_test.return_value = True

        with app.app_context():
            # Create config with old timestamp
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=encrypted,
                last_tested_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()
            old_time = config.last_tested_at

        # Test connection
        client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "test_key"},
            content_type="application/json",
        )

        # Verify timestamp was updated
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config.last_tested_at > old_time

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_status_changes_from_success_to_failed(self, mock_test, app, client, temp_instance_path):
        """Test that status correctly changes when test fails."""
        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=encrypted,
                last_tested_at=datetime.now(timezone.utc),
                last_test_status="success",
            )
            db.session.add(config)
            db.session.commit()

        # Test with failed result
        mock_test.return_value = False
        client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "test_key"},
            content_type="application/json",
        )

        # Verify status changed to failed
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config.last_test_status == "failed"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_status_changes_from_failed_to_success(self, mock_test, app, client, temp_instance_path):
        """Test that status correctly changes when test succeeds."""
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

        # Test with success result
        mock_test.return_value = True
        client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "test_key"},
            content_type="application/json",
        )

        # Verify status changed to success
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config.last_test_status == "success"


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    def test_page_loads_with_corrupted_encrypted_data(self, app, client, temp_instance_path):
        """Test that page still loads when encrypted data is corrupted."""
        with app.app_context():
            # Save corrupted encrypted data
            config = ServiceConfig(service="TMDB", api_key_encrypted="corrupted_data_not_valid_encryption")
            db.session.add(config)
            db.session.commit()

        # Page should still load (stub renders without decrypting)
        response = client.get("/settings")
        assert response.status_code == 200


class TestMultipleRequestsScenarios:
    """Integration tests for scenarios with multiple requests."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_interleaved_test_and_save_requests(self, mock_test, app, client):
        """Test handling of interleaved test requests."""
        mock_test.return_value = True

        # Multiple test operations
        client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "key_1"},
            content_type="application/json",
        )

        client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "key_1"},
            content_type="application/json",
        )

        # Settings page should still load
        response = client.get("/settings")
        assert response.status_code == 200
