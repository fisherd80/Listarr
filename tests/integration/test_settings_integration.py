"""
Integration tests for Settings functionality.

Tests cover:
- Full end-to-end workflows for settings management
- Database operations with encryption
- TMDB API integration with real mocking
- Error recovery and rollback scenarios
- Multi-step workflows (test -> save -> retrieve)
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from listarr import db
from listarr.models.service_config_model import ServiceConfig
from listarr.services.crypto_utils import decrypt_data, encrypt_data


class TestSettingsEndToEndWorkflow:
    """Integration tests for complete settings workflows."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_full_save_and_retrieve_workflow(self, mock_test, app, client, temp_instance_path):
        """Test complete workflow: save API key, reload page, verify displayed."""
        mock_test.return_value = True

        # Step 1: Save API key
        response = client.post(
            "/settings",
            data={"tmdb_api": "integration_test_key_12345", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"TMDB API Key saved successfully" in response.data

        # Step 2: Reload page (simulates user refresh)
        response = client.get("/settings")

        assert response.status_code == 200
        # API key should be present (decrypted for display)
        assert b"integration_test_key_12345" in response.data

        # Step 3: Verify database state
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config is not None
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "integration_test_key_12345"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_ajax_test_then_save_workflow(self, mock_test, app, client, temp_instance_path):
        """Test workflow: AJAX test connection, then save."""
        mock_test.return_value = True

        # Step 1: Test connection via AJAX
        response = client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "test_key_ajax"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Step 2: Save the same key
        response = client.post(
            "/settings",
            data={"tmdb_api": "test_key_ajax", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"TMDB API Key saved successfully" in response.data

        # Step 3: Verify single database entry with updated status
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="TMDB").all()
            # Should only have one config entry
            assert len(configs) <= 1

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_update_existing_key_workflow(self, mock_test, app, client, temp_instance_path):
        """Test workflow: save key, update with new key, verify update."""
        mock_test.return_value = True

        # Step 1: Save initial key
        client.post("/settings", data={"tmdb_api": "initial_key", "save_api_key": "true"})

        # Step 2: Update with new key
        response = client.post(
            "/settings",
            data={"tmdb_api": "updated_key", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Step 3: Verify only one config exists with updated key
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="TMDB").all()
            assert len(configs) == 1
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "updated_key"

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
    def test_concurrent_config_updates_are_handled(self, mock_test, app, client, temp_instance_path):
        """Test that multiple updates to same config work correctly."""
        mock_test.return_value = True

        with app.app_context():
            # Create initial config
            encrypted = encrypt_data("initial_key", instance_path=temp_instance_path)
            config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
            db.session.add(config)
            db.session.commit()
            config_id = config.id

        # Perform multiple updates
        for i in range(3):
            client.post(
                "/settings",
                data={"tmdb_api": f"key_version_{i}", "save_api_key": "true"},
            )

        # Verify only one config exists with final version
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="TMDB").all()
            assert len(configs) == 1
            assert configs[0].id == config_id
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "key_version_2"

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
            with patch.object(db.session, "commit", side_effect=OperationalError("DB error", None, None)):
                client.post("/settings", data={"tmdb_api": "new_key", "save_api_key": "true"})

            # Verify original key is still intact (rollback worked)
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "original_key"

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
            with patch.object(db.session, "commit", side_effect=OperationalError("DB error", None, None)):
                client.post(
                    "/settings/test_tmdb_api",
                    json={"api_key": "test_key"},
                    content_type="application/json",
                )

            # Verify original timestamp is intact (rollback worked)
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            assert config.last_tested_at == original_time

    def test_encryption_key_persistence_across_requests(self, app, client, temp_instance_path):
        """Test that encryption key is properly loaded for each request."""
        with app.app_context():
            # Encrypt with app's key
            encrypted = encrypt_data("persistent_key", instance_path=temp_instance_path)

            config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
            db.session.add(config)
            db.session.commit()

        # Make request (should load key and decrypt)
        response = client.get("/settings")

        assert response.status_code == 200
        # Should successfully decrypt and display key
        assert b"persistent_key" in response.data


class TestEncryptionIntegration:
    """Integration tests for encryption workflows."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_encryption_roundtrip_through_database(self, mock_test, app, client, temp_instance_path):
        """Test full encryption roundtrip: encrypt -> save -> retrieve -> decrypt."""
        mock_test.return_value = True
        original_key = "secret_api_key_12345"

        # Save key (encrypts)
        client.post("/settings", data={"tmdb_api": original_key, "save_api_key": "true"})

        # Retrieve from database and decrypt
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            encrypted = config.api_key_encrypted

            # Verify encrypted value is different from original
            assert encrypted != original_key

            # Decrypt and verify
            decrypted = decrypt_data(encrypted, instance_path=temp_instance_path)
            assert decrypted == original_key

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_multiple_keys_encrypted_differently(self, mock_test, app, client, temp_instance_path):
        """Test that same key encrypted multiple times produces different ciphertext."""
        mock_test.return_value = True
        api_key = "same_key"

        encrypted_values = []

        for _ in range(3):
            with app.app_context():
                # Encrypt and save
                client.post("/settings", data={"tmdb_api": api_key, "save_api_key": "true"})

                config = ServiceConfig.query.filter_by(service="TMDB").first()
                encrypted_values.append(config.api_key_encrypted)

                # Clear for next iteration
                db.session.delete(config)
                db.session.commit()

        # All encrypted values should be different (due to nonce)
        assert len(set(encrypted_values)) == 3

        # But all should decrypt to same value
        with app.app_context():
            for encrypted in encrypted_values:
                decrypted = decrypt_data(encrypted, instance_path=temp_instance_path)
                assert decrypted == api_key


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

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_recovery_from_invalid_key_save_attempt(self, mock_test, app, client, temp_instance_path):
        """Test that application recovers from invalid key save attempt."""
        # Step 1: Try to save invalid key
        mock_test.return_value = False
        response = client.post(
            "/settings",
            data={"tmdb_api": "invalid_key", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert b"Invalid TMDB API Key" in response.data

        # Step 2: Save valid key
        mock_test.return_value = True
        response = client.post(
            "/settings",
            data={"tmdb_api": "valid_key", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert b"TMDB API Key saved successfully" in response.data

        # Step 3: Verify valid key is in database
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="TMDB").first()
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "valid_key"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    @patch("listarr.routes.settings_routes.encrypt_data")
    def test_recovery_from_encryption_failure(self, mock_encrypt, mock_test, app, client, temp_instance_path):
        """Test that application recovers from encryption failure."""
        mock_test.return_value = True

        # Step 1: Cause encryption to fail
        mock_encrypt.side_effect = RuntimeError("Encryption error")
        response = client.post(
            "/settings",
            data={"tmdb_api": "test_key", "save_api_key": "true"},
            follow_redirects=True,
        )

        assert b"Failed to save TMDB configuration" in response.data

        # Step 2: Fix encryption and retry
        mock_encrypt.side_effect = None
        mock_encrypt.side_effect = lambda data, instance_path: encrypt_data(data, instance_path)

        response = client.post(
            "/settings",
            data={"tmdb_api": "test_key", "save_api_key": "true"},
            follow_redirects=True,
        )

        # Should work now
        assert response.status_code == 200

    def test_page_loads_with_corrupted_encrypted_data(self, app, client, temp_instance_path):
        """Test that page still loads when encrypted data is corrupted."""
        with app.app_context():
            # Save corrupted encrypted data
            config = ServiceConfig(service="TMDB", api_key_encrypted="corrupted_data_not_valid_encryption")
            db.session.add(config)
            db.session.commit()

        # Page should still load (may show empty field or handle error)
        response = client.get("/settings")
        assert response.status_code == 200


class TestMultipleRequestsScenarios:
    """Integration tests for scenarios with multiple requests."""

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_rapid_succession_save_requests(self, mock_test, app, client, temp_instance_path):
        """Test handling of rapid succession save requests."""
        mock_test.return_value = True

        # Simulate rapid saves
        for i in range(5):
            client.post("/settings", data={"tmdb_api": f"key_{i}", "save_api_key": "true"})

        # Should have exactly one config with last key
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="TMDB").all()
            assert len(configs) == 1
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == "key_4"

    @patch("listarr.routes.settings_routes.validate_tmdb_api_key")
    def test_interleaved_test_and_save_requests(self, mock_test, app, client):
        """Test handling of interleaved test and save requests."""
        mock_test.return_value = True

        # Interleave test and save operations
        client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "key_1"},
            content_type="application/json",
        )

        client.post("/settings", data={"tmdb_api": "key_1", "save_api_key": "true"})

        client.post(
            "/settings/test_tmdb_api",
            json={"api_key": "key_1"},
            content_type="application/json",
        )

        # Should complete without errors
        response = client.get("/settings")
        assert response.status_code == 200
