"""
Integration tests for Config functionality.

Tests cover:
- Full end-to-end workflows for Radarr/Sonarr configuration
- Database operations with encryption
- Radarr/Sonarr API integration with real mocking
- Import settings workflows (fetch → populate → save → retrieve)
- Error recovery and rollback scenarios
- Multi-step workflows (test → save → reload → verify)
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from listarr.models.service_config_model import ServiceConfig, MediaImportSettings
from listarr import db
from listarr.services.crypto_utils import encrypt_data, decrypt_data


class TestRadarrConfigEndToEndWorkflow:
    """Integration tests for complete Radarr configuration workflows."""

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_full_radarr_save_and_retrieve_workflow(self, mock_test, app, client, temp_instance_path):
        """Test complete Radarr workflow: save API key, reload page, verify displayed."""
        mock_test.return_value = True

        # Step 1: Save Radarr API key
        response = client.post('/config', data={
            'radarr_url': 'http://localhost:7878',
            'radarr_api': 'radarr_test_key_12345',
            'save_radarr_api': 'true'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Radarr URL and API Key saved successfully' in response.data

        # Step 2: Reload page (simulates user refresh)
        response = client.get('/config')

        assert response.status_code == 200
        # API key should be present (decrypted for display)
        assert b'radarr_test_key_12345' in response.data
        assert b'http://localhost:7878' in response.data

        # Step 3: Verify database state
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            assert config is not None
            assert config.base_url == 'http://localhost:7878'
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == 'radarr_test_key_12345'

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_radarr_ajax_test_then_save_workflow(self, mock_test, app, client, temp_instance_path):
        """Test workflow: AJAX test Radarr connection, then save."""
        mock_test.return_value = True

        # Step 1: Test connection via AJAX
        response = client.post('/config/test_radarr_api',
            json={'base_url': 'http://localhost:7878', 'api_key': 'test_key_ajax'},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Step 2: Save the same credentials
        response = client.post('/config', data={
            'radarr_url': 'http://localhost:7878',
            'radarr_api': 'test_key_ajax',
            'save_radarr_api': 'true'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Radarr URL and API Key saved successfully' in response.data

        # Step 3: Verify single database entry with updated status
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="RADARR").all()
            # Should only have one config entry
            assert len(configs) <= 1

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_update_existing_radarr_key_workflow(self, mock_test, app, client, temp_instance_path):
        """Test workflow: save Radarr key, update with new key, verify update."""
        mock_test.return_value = True

        # Step 1: Save initial key
        client.post('/config', data={
            'radarr_url': 'http://localhost:7878',
            'radarr_api': 'initial_radarr_key',
            'save_radarr_api': 'true'
        })

        # Step 2: Update with new key and URL
        response = client.post('/config', data={
            'radarr_url': 'http://192.168.1.100:7878',
            'radarr_api': 'updated_radarr_key',
            'save_radarr_api': 'true'
        }, follow_redirects=True)

        assert response.status_code == 200

        # Step 3: Verify only one config exists with updated values
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="RADARR").all()
            assert len(configs) == 1
            assert configs[0].base_url == 'http://192.168.1.100:7878'
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == 'updated_radarr_key'

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_failed_radarr_test_then_successful_test_workflow(self, mock_test, app, client):
        """Test workflow: failed Radarr test, fix credentials, successful test."""
        # Step 1: Test with invalid credentials
        mock_test.return_value = False
        response = client.post('/config/test_radarr_api',
            json={'base_url': 'http://invalid:7878', 'api_key': 'invalid_key'},
            content_type='application/json'
        )

        data = response.get_json()
        assert data['success'] is False

        # Step 2: Test with valid credentials
        mock_test.return_value = True
        response = client.post('/config/test_radarr_api',
            json={'base_url': 'http://localhost:7878', 'api_key': 'valid_key'},
            content_type='application/json'
        )

        data = response.get_json()
        assert data['success'] is True


class TestSonarrConfigEndToEndWorkflow:
    """Integration tests for complete Sonarr configuration workflows."""

    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_full_sonarr_save_and_retrieve_workflow(self, mock_test, app, client, temp_instance_path):
        """Test complete Sonarr workflow: save API key, reload page, verify displayed."""
        mock_test.return_value = True

        # Step 1: Save Sonarr API key
        response = client.post('/config', data={
            'sonarr_url': 'http://localhost:8989',
            'sonarr_api': 'sonarr_test_key_12345',
            'save_sonarr_api': 'true'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Sonarr URL and API Key saved successfully' in response.data

        # Step 2: Reload page (simulates user refresh)
        response = client.get('/config')

        assert response.status_code == 200
        # API key should be present (decrypted for display)
        assert b'sonarr_test_key_12345' in response.data
        assert b'http://localhost:8989' in response.data

        # Step 3: Verify database state
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="SONARR").first()
            assert config is not None
            assert config.base_url == 'http://localhost:8989'
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == 'sonarr_test_key_12345'

    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_sonarr_ajax_test_then_save_workflow(self, mock_test, app, client, temp_instance_path):
        """Test workflow: AJAX test Sonarr connection, then save."""
        mock_test.return_value = True

        # Step 1: Test connection via AJAX
        response = client.post('/config/test_sonarr_api',
            json={'base_url': 'http://localhost:8989', 'api_key': 'test_key_ajax'},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Step 2: Save the same credentials
        response = client.post('/config', data={
            'sonarr_url': 'http://localhost:8989',
            'sonarr_api': 'test_key_ajax',
            'save_sonarr_api': 'true'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Sonarr URL and API Key saved successfully' in response.data

        # Step 3: Verify single database entry with updated status
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="SONARR").all()
            # Should only have one config entry
            assert len(configs) <= 1

    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_update_existing_sonarr_key_workflow(self, mock_test, app, client, temp_instance_path):
        """Test workflow: save Sonarr key, update with new key, verify update."""
        mock_test.return_value = True

        # Step 1: Save initial key
        client.post('/config', data={
            'sonarr_url': 'http://localhost:8989',
            'sonarr_api': 'initial_sonarr_key',
            'save_sonarr_api': 'true'
        })

        # Step 2: Update with new key and URL
        response = client.post('/config', data={
            'sonarr_url': 'http://192.168.1.100:8989',
            'sonarr_api': 'updated_sonarr_key',
            'save_sonarr_api': 'true'
        }, follow_redirects=True)

        assert response.status_code == 200

        # Step 3: Verify only one config exists with updated values
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="SONARR").all()
            assert len(configs) == 1
            assert configs[0].base_url == 'http://192.168.1.100:8989'
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == 'updated_sonarr_key'


class TestRadarrImportSettingsWorkflow:
    """Integration tests for Radarr import settings workflows."""

    @patch('listarr.routes.config_routes.get_radarr_quality_profiles')
    @patch('listarr.routes.config_routes.get_radarr_root_folders')
    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_full_radarr_import_settings_workflow(
        self, mock_test, mock_root_folders, mock_quality_profiles, app, client, temp_instance_path
    ):
        """Test complete workflow: configure Radarr → fetch settings → save → retrieve."""
        mock_test.return_value = True
        mock_quality_profiles.return_value = [
            {'id': 1, 'name': 'HD-1080p'},
            {'id': 2, 'name': 'Ultra-HD'}
        ]
        mock_root_folders.return_value = [
            {'id': 1, 'path': '/movies'},
            {'id': 2, 'path': '/storage/movies'}
        ]

        # Step 1: Configure Radarr
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted
            )
            db.session.add(config)
            db.session.commit()

        # Step 2: Fetch quality profiles
        response = client.get('/config/radarr/quality-profiles')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['profiles']) == 2

        # Step 3: Fetch root folders
        response = client.get('/config/radarr/root-folders')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['folders']) == 2

        # Step 4: Save import settings
        response = client.post('/config/radarr/import-settings',
            json={
                'root_folder_id': '/movies',
                'quality_profile_id': 1,
                'monitored': True,
                'search_on_add': False
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Step 5: Retrieve saved settings
        response = client.get('/config/radarr/import-settings')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['settings']['root_folder_id'] == '/movies'
        assert data['settings']['quality_profile_id'] == 1
        assert data['settings']['monitored'] is True
        assert data['settings']['search_on_add'] is False

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_radarr_import_settings_update_workflow(self, mock_test, app, client, temp_instance_path):
        """Test workflow: save import settings, update, verify changes."""
        mock_test.return_value = True

        # Create Radarr config
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted
            )
            db.session.add(config)
            db.session.commit()

        # Step 1: Save initial settings
        client.post('/config/radarr/import-settings',
            json={
                'root_folder_id': '/movies',
                'quality_profile_id': 1,
                'monitored': True,
                'search_on_add': True
            },
            content_type='application/json'
        )

        # Step 2: Update settings
        response = client.post('/config/radarr/import-settings',
            json={
                'root_folder_id': '/storage/movies',
                'quality_profile_id': 2,
                'monitored': False,
                'search_on_add': False
            },
            content_type='application/json'
        )
        assert response.status_code == 200

        # Step 3: Verify only one settings entry exists with updated values
        with app.app_context():
            settings = MediaImportSettings.query.filter_by(service="RADARR").all()
            assert len(settings) == 1
            assert settings[0].root_folder == '/storage/movies'
            assert settings[0].quality_profile_id == 2
            assert settings[0].monitored is False
            assert settings[0].search_on_add is False


class TestSonarrImportSettingsWorkflow:
    """Integration tests for Sonarr import settings workflows."""

    @patch('listarr.routes.config_routes.get_sonarr_quality_profiles')
    @patch('listarr.routes.config_routes.get_sonarr_root_folders')
    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_full_sonarr_import_settings_workflow(
        self, mock_test, mock_root_folders, mock_quality_profiles, app, client, temp_instance_path
    ):
        """Test complete workflow: configure Sonarr → fetch settings → save → retrieve."""
        mock_test.return_value = True
        mock_quality_profiles.return_value = [
            {'id': 1, 'name': 'HD-1080p'},
            {'id': 2, 'name': 'Ultra-HD'}
        ]
        mock_root_folders.return_value = [
            {'id': 1, 'path': '/tv'},
            {'id': 2, 'path': '/storage/tv'}
        ]

        # Step 1: Configure Sonarr
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted
            )
            db.session.add(config)
            db.session.commit()

        # Step 2: Fetch quality profiles
        response = client.get('/config/sonarr/quality-profiles')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['profiles']) == 2

        # Step 3: Fetch root folders
        response = client.get('/config/sonarr/root-folders')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['folders']) == 2

        # Step 4: Save import settings (includes season_folder for Sonarr)
        response = client.post('/config/sonarr/import-settings',
            json={
                'root_folder_id': '/tv',
                'quality_profile_id': 1,
                'monitored': True,
                'season_folder': True,
                'search_on_add': False
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Step 5: Retrieve saved settings
        response = client.get('/config/sonarr/import-settings')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['settings']['root_folder_id'] == '/tv'
        assert data['settings']['quality_profile_id'] == 1
        assert data['settings']['monitored'] is True
        assert data['settings']['season_folder'] is True
        assert data['settings']['search_on_add'] is False

    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_sonarr_import_settings_update_workflow(self, mock_test, app, client, temp_instance_path):
        """Test workflow: save Sonarr import settings, update, verify changes."""
        mock_test.return_value = True

        # Create Sonarr config
        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted
            )
            db.session.add(config)
            db.session.commit()

        # Step 1: Save initial settings
        client.post('/config/sonarr/import-settings',
            json={
                'root_folder_id': '/tv',
                'quality_profile_id': 1,
                'monitored': True,
                'season_folder': True,
                'search_on_add': True
            },
            content_type='application/json'
        )

        # Step 2: Update settings
        response = client.post('/config/sonarr/import-settings',
            json={
                'root_folder_id': '/storage/tv',
                'quality_profile_id': 2,
                'monitored': False,
                'season_folder': False,
                'search_on_add': False
            },
            content_type='application/json'
        )
        assert response.status_code == 200

        # Step 3: Verify only one settings entry exists with updated values
        with app.app_context():
            settings = MediaImportSettings.query.filter_by(service="SONARR").all()
            assert len(settings) == 1
            assert settings[0].root_folder == '/storage/tv'
            assert settings[0].quality_profile_id == 2
            assert settings[0].monitored is False
            assert settings[0].season_folder is False
            assert settings[0].search_on_add is False


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_concurrent_radarr_config_updates_are_handled(self, mock_test, app, client, temp_instance_path):
        """Test that multiple updates to same Radarr config work correctly."""
        mock_test.return_value = True

        with app.app_context():
            # Create initial config
            encrypted = encrypt_data("initial_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted
            )
            db.session.add(config)
            db.session.commit()
            config_id = config.id

        # Perform multiple updates
        for i in range(3):
            client.post('/config', data={
                'radarr_url': f'http://localhost:787{i}',
                'radarr_api': f'key_version_{i}',
                'save_radarr_api': 'true'
            })

        # Verify only one config exists with final version
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="RADARR").all()
            assert len(configs) == 1
            assert configs[0].id == config_id
            assert configs[0].base_url == 'http://localhost:7872'
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == 'key_version_2'

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_database_rollback_on_radarr_save_error(self, mock_test, app, client, temp_instance_path):
        """Test that database rollback works on Radarr save errors."""
        mock_test.return_value = True

        with app.app_context():
            # Create initial config
            encrypted = encrypt_data("original_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted
            )
            db.session.add(config)
            db.session.commit()

            # Force commit to fail
            with patch.object(db.session, 'commit', side_effect=Exception("DB error")):
                client.post('/config', data={
                    'radarr_url': 'http://localhost:7878',
                    'radarr_api': 'new_key',
                    'save_radarr_api': 'true'
                })

            # Verify original key is still intact (rollback worked)
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == 'original_key'

    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_database_rollback_on_sonarr_test_error(self, mock_test, app, client, temp_instance_path):
        """Test that database rollback works on Sonarr AJAX test errors."""
        mock_test.return_value = True

        with app.app_context():
            # Create initial config
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
                last_tested_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                last_test_status="success"
            )
            db.session.add(config)
            db.session.commit()
            original_time = config.last_tested_at

            # Force commit to fail during test update
            with patch.object(db.session, 'commit', side_effect=Exception("DB error")):
                client.post('/config/test_sonarr_api',
                    json={'base_url': 'http://localhost:8989', 'api_key': 'test_key'},
                    content_type='application/json'
                )

            # Verify original timestamp is intact (rollback worked)
            config = ServiceConfig.query.filter_by(service="SONARR").first()
            assert config.last_tested_at == original_time

    def test_encryption_key_persistence_across_config_requests(self, app, client, temp_instance_path):
        """Test that encryption key is properly loaded for each config request."""
        with app.app_context():
            # Encrypt with app's key
            radarr_encrypted = encrypt_data("persistent_radarr_key", instance_path=temp_instance_path)
            sonarr_encrypted = encrypt_data("persistent_sonarr_key", instance_path=temp_instance_path)

            radarr_config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=radarr_encrypted
            )
            sonarr_config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=sonarr_encrypted
            )
            db.session.add(radarr_config)
            db.session.add(sonarr_config)
            db.session.commit()

        # Make request (should load key and decrypt)
        response = client.get('/config')

        assert response.status_code == 200
        # Should successfully decrypt and display keys
        assert b'persistent_radarr_key' in response.data
        assert b'persistent_sonarr_key' in response.data


class TestEncryptionIntegration:
    """Integration tests for encryption workflows."""

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_radarr_encryption_roundtrip_through_database(self, mock_test, app, client, temp_instance_path):
        """Test full Radarr encryption roundtrip: encrypt → save → retrieve → decrypt."""
        mock_test.return_value = True
        original_key = "secret_radarr_key_12345"

        # Save key (encrypts)
        client.post('/config', data={
            'radarr_url': 'http://localhost:7878',
            'radarr_api': original_key,
            'save_radarr_api': 'true'
        })

        # Retrieve from database and decrypt
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            encrypted = config.api_key_encrypted

            # Verify encrypted value is different from original
            assert encrypted != original_key

            # Decrypt and verify
            decrypted = decrypt_data(encrypted, instance_path=temp_instance_path)
            assert decrypted == original_key

    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_sonarr_multiple_keys_encrypted_differently(self, mock_test, app, client, temp_instance_path):
        """Test that same Sonarr key encrypted multiple times produces different ciphertext."""
        mock_test.return_value = True
        api_key = "same_sonarr_key"

        encrypted_values = []

        for _ in range(3):
            with app.app_context():
                # Encrypt and save
                client.post('/config', data={
                    'sonarr_url': 'http://localhost:8989',
                    'sonarr_api': api_key,
                    'save_sonarr_api': 'true'
                })

                config = ServiceConfig.query.filter_by(service="SONARR").first()
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

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_radarr_timestamp_updated_on_each_test(self, mock_test, app, client, temp_instance_path):
        """Test that Radarr last_tested_at is updated on each test."""
        mock_test.return_value = True

        with app.app_context():
            # Create config with old timestamp
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
                last_tested_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                last_test_status="success"
            )
            db.session.add(config)
            db.session.commit()
            old_time = config.last_tested_at

        # Test connection
        client.post('/config/test_radarr_api',
            json={'base_url': 'http://localhost:7878', 'api_key': 'test_key'},
            content_type='application/json'
        )

        # Verify timestamp was updated
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            assert config.last_tested_at > old_time

    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_sonarr_status_changes_from_success_to_failed(self, mock_test, app, client, temp_instance_path):
        """Test that Sonarr status correctly changes when test fails."""
        with app.app_context():
            encrypted = encrypt_data("test_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
                last_tested_at=datetime.now(timezone.utc),
                last_test_status="success"
            )
            db.session.add(config)
            db.session.commit()

        # Test with failed result
        mock_test.return_value = False
        client.post('/config/test_sonarr_api',
            json={'base_url': 'http://localhost:8989', 'api_key': 'test_key'},
            content_type='application/json'
        )

        # Verify status changed to failed
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="SONARR").first()
            assert config.last_test_status == "failed"


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_recovery_from_invalid_radarr_key_save_attempt(self, mock_test, app, client, temp_instance_path):
        """Test that application recovers from invalid Radarr key save attempt."""
        # Step 1: Try to save invalid key
        mock_test.return_value = False
        response = client.post('/config', data={
            'radarr_url': 'http://localhost:7878',
            'radarr_api': 'invalid_key',
            'save_radarr_api': 'true'
        }, follow_redirects=True)

        assert b'Invalid Radarr URL or API Key' in response.data

        # Step 2: Save valid key
        mock_test.return_value = True
        response = client.post('/config', data={
            'radarr_url': 'http://localhost:7878',
            'radarr_api': 'valid_key',
            'save_radarr_api': 'true'
        }, follow_redirects=True)

        assert b'Radarr URL and API Key saved successfully' in response.data

        # Step 3: Verify valid key is in database
        with app.app_context():
            config = ServiceConfig.query.filter_by(service="RADARR").first()
            decrypted = decrypt_data(config.api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == 'valid_key'

    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    @patch('listarr.routes.config_routes.encrypt_data')
    def test_recovery_from_sonarr_encryption_failure(self, mock_encrypt, mock_test, app, client, temp_instance_path):
        """Test that application recovers from Sonarr encryption failure."""
        mock_test.return_value = True

        # Step 1: Cause encryption to fail
        mock_encrypt.side_effect = Exception("Encryption error")
        response = client.post('/config', data={
            'sonarr_url': 'http://localhost:8989',
            'sonarr_api': 'test_key',
            'save_sonarr_api': 'true'
        }, follow_redirects=True)

        assert b'Failed to save Sonarr configuration' in response.data

        # Step 2: Fix encryption and retry
        mock_encrypt.side_effect = None
        mock_encrypt.side_effect = lambda data, instance_path: encrypt_data(data, instance_path)

        response = client.post('/config', data={
            'sonarr_url': 'http://localhost:8989',
            'sonarr_api': 'test_key',
            'save_sonarr_api': 'true'
        }, follow_redirects=True)

        # Should work now
        assert response.status_code == 200


class TestMultipleRequestsScenarios:
    """Integration tests for scenarios with multiple requests."""

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    @patch('listarr.routes.config_routes.validate_sonarr_api_key')
    def test_simultaneous_radarr_and_sonarr_configuration(
        self, mock_sonarr_test, mock_radarr_test, app, client, temp_instance_path
    ):
        """Test configuring both Radarr and Sonarr in same session."""
        mock_radarr_test.return_value = True
        mock_sonarr_test.return_value = True

        # Configure Radarr
        client.post('/config', data={
            'radarr_url': 'http://localhost:7878',
            'radarr_api': 'radarr_key',
            'save_radarr_api': 'true'
        })

        # Configure Sonarr
        client.post('/config', data={
            'sonarr_url': 'http://localhost:8989',
            'sonarr_api': 'sonarr_key',
            'save_sonarr_api': 'true'
        })

        # Both should be saved independently
        with app.app_context():
            radarr_config = ServiceConfig.query.filter_by(service="RADARR").first()
            sonarr_config = ServiceConfig.query.filter_by(service="SONARR").first()

            assert radarr_config is not None
            assert sonarr_config is not None

            radarr_key = decrypt_data(radarr_config.api_key_encrypted, instance_path=temp_instance_path)
            sonarr_key = decrypt_data(sonarr_config.api_key_encrypted, instance_path=temp_instance_path)

            assert radarr_key == 'radarr_key'
            assert sonarr_key == 'sonarr_key'

    @patch('listarr.routes.config_routes.validate_radarr_api_key')
    def test_rapid_succession_radarr_save_requests(self, mock_test, app, client, temp_instance_path):
        """Test handling of rapid succession Radarr save requests."""
        mock_test.return_value = True

        # Simulate rapid saves
        for i in range(5):
            client.post('/config', data={
                'radarr_url': f'http://localhost:787{i}',
                'radarr_api': f'key_{i}',
                'save_radarr_api': 'true'
            })

        # Should have exactly one config with last key
        with app.app_context():
            configs = ServiceConfig.query.filter_by(service="RADARR").all()
            assert len(configs) == 1
            decrypted = decrypt_data(configs[0].api_key_encrypted, instance_path=temp_instance_path)
            assert decrypted == 'key_4'
            assert configs[0].base_url == 'http://localhost:7874'
