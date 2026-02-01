"""
Unit tests for ServiceConfig model.

Tests cover:
- Model field validation
- Database constraints (unique service)
- Timestamp handling
- Model creation and updates
- Field types and nullable constraints
"""

from datetime import datetime, timezone

import pytest

from listarr import db
from listarr.models.service_config_model import ServiceConfig


class TestServiceConfigModel:
    """Tests for ServiceConfig database model."""

    def test_create_service_config(self, app):
        """Test creating a ServiceConfig instance."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="encrypted_key_data"
            )
            db.session.add(config)
            db.session.commit()

            assert config.id is not None
            assert config.service == "TMDB"
            assert config.api_key_encrypted == "encrypted_key_data"

    def test_service_config_default_values(self, app):
        """Test that default values are set correctly."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="encrypted_key"
            )
            db.session.add(config)
            db.session.commit()

            assert config.is_enabled is True
            assert config.last_tested_at is None
            assert config.last_test_status is None
            assert config.base_url is None

    def test_service_config_with_all_fields(self, app):
        """Test creating ServiceConfig with all fields populated."""
        with app.app_context():
            test_time = datetime(2023, 6, 15, 10, 30, 0, tzinfo=timezone.utc)

            config = ServiceConfig(
                service="Radarr",
                base_url="http://localhost:7878",
                api_key_encrypted="encrypted_radarr_key",
                is_enabled=True,
                last_tested_at=test_time,
                last_test_status="success"
            )
            db.session.add(config)
            db.session.commit()

            assert config.service == "Radarr"
            assert config.base_url == "http://localhost:7878"
            assert config.api_key_encrypted == "encrypted_radarr_key"
            assert config.is_enabled is True
            assert config.last_tested_at == test_time
            assert config.last_test_status == "success"

    def test_service_name_must_be_unique(self, app):
        """Test that service name has unique constraint."""
        with app.app_context():
            config1 = ServiceConfig(
                service="TMDB",
                api_key_encrypted="key1"
            )
            db.session.add(config1)
            db.session.commit()

            # Try to create duplicate
            config2 = ServiceConfig(
                service="TMDB",
                api_key_encrypted="key2"
            )
            db.session.add(config2)

            with pytest.raises(Exception):  # SQLAlchemy IntegrityError
                db.session.commit()

            db.session.rollback()

    def test_service_config_query_by_service(self, app):
        """Test querying ServiceConfig by service name."""
        with app.app_context():
            config = ServiceConfig(
                service="Sonarr",
                api_key_encrypted="sonarr_key"
            )
            db.session.add(config)
            db.session.commit()

            found = ServiceConfig.query.filter_by(service="Sonarr").first()

            assert found is not None
            assert found.service == "Sonarr"
            assert found.api_key_encrypted == "sonarr_key"

    def test_service_config_update(self, app):
        """Test updating ServiceConfig fields."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="old_key",
                last_test_status="failed"
            )
            db.session.add(config)
            db.session.commit()

            config_id = config.id

            # Update fields
            config.api_key_encrypted = "new_key"
            config.last_test_status = "success"
            config.last_tested_at = datetime.now(timezone.utc)
            db.session.commit()

            # Query again to verify
            updated = ServiceConfig.query.get(config_id)
            assert updated.api_key_encrypted == "new_key"
            assert updated.last_test_status == "success"
            assert updated.last_tested_at is not None

    def test_service_config_delete(self, app):
        """Test deleting ServiceConfig."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="key"
            )
            db.session.add(config)
            db.session.commit()

            config_id = config.id

            db.session.delete(config)
            db.session.commit()

            # Verify deleted
            found = ServiceConfig.query.get(config_id)
            assert found is None

    def test_service_field_is_required(self, app):
        """Test that service field is required (NOT NULL)."""
        with app.app_context():
            config = ServiceConfig(
                api_key_encrypted="key"
                # Missing service field
            )
            db.session.add(config)

            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()

            db.session.rollback()

    def test_api_key_encrypted_field_is_required(self, app):
        """Test that api_key_encrypted field is required (NOT NULL)."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB"
                # Missing api_key_encrypted
            )
            db.session.add(config)

            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()

            db.session.rollback()

    def test_created_at_timestamp_auto_set(self, app):
        """Test that created_at is automatically set on creation."""
        with app.app_context():
            before_time = datetime.now(timezone.utc)

            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="key"
            )
            db.session.add(config)
            db.session.commit()

            after_time = datetime.now(timezone.utc)

            # created_at should be set automatically
            assert config.created_at is not None
            # Should be within reasonable time range
            # Note: created_at may not have timezone info depending on DB
            if config.created_at.tzinfo:
                assert before_time <= config.created_at <= after_time

    def test_service_config_stores_long_encrypted_keys(self, app):
        """Test that model can store long encrypted key strings."""
        with app.app_context():
            # Simulate long encrypted key (Fernet tokens are typically 100+ chars)
            long_key = "A" * 500

            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=long_key
            )
            db.session.add(config)
            db.session.commit()

            found = ServiceConfig.query.filter_by(service="TMDB").first()
            assert found.api_key_encrypted == long_key

    def test_multiple_service_configs(self, app):
        """Test storing multiple different service configurations."""
        with app.app_context():
            services = [
                ServiceConfig(service="TMDB", api_key_encrypted="tmdb_key"),
                ServiceConfig(service="Radarr", api_key_encrypted="radarr_key", base_url="http://radarr:7878"),
                ServiceConfig(service="Sonarr", api_key_encrypted="sonarr_key", base_url="http://sonarr:8989"),
            ]

            for service in services:
                db.session.add(service)

            db.session.commit()

            # Verify all were saved
            all_configs = ServiceConfig.query.all()
            assert len(all_configs) == 3

            service_names = [c.service for c in all_configs]
            assert "TMDB" in service_names
            assert "Radarr" in service_names
            assert "Sonarr" in service_names

    def test_last_test_status_values(self, app):
        """Test different last_test_status values."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="key"
            )
            db.session.add(config)
            db.session.commit()

            # Test different status values
            for status in ["success", "failed", None]:
                config.last_test_status = status
                db.session.commit()

                found = ServiceConfig.query.filter_by(service="TMDB").first()
                assert found.last_test_status == status

    def test_is_enabled_toggle(self, app):
        """Test toggling is_enabled flag."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="key",
                is_enabled=True
            )
            db.session.add(config)
            db.session.commit()

            # Disable
            config.is_enabled = False
            db.session.commit()

            found = ServiceConfig.query.filter_by(service="TMDB").first()
            assert found.is_enabled is False

            # Re-enable
            config.is_enabled = True
            db.session.commit()

            found = ServiceConfig.query.filter_by(service="TMDB").first()
            assert found.is_enabled is True

    def test_base_url_optional_for_tmdb(self, app):
        """Test that base_url is optional (for TMDB which doesn't need it)."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="key",
                base_url=None
            )
            db.session.add(config)
            db.session.commit()

            found = ServiceConfig.query.filter_by(service="TMDB").first()
            assert found.base_url is None

    def test_base_url_can_be_set(self, app):
        """Test that base_url can be set for services that need it."""
        with app.app_context():
            config = ServiceConfig(
                service="Radarr",
                api_key_encrypted="key",
                base_url="http://192.168.1.100:7878"
            )
            db.session.add(config)
            db.session.commit()

            found = ServiceConfig.query.filter_by(service="Radarr").first()
            assert found.base_url == "http://192.168.1.100:7878"

    def test_service_config_representation(self, app):
        """Test that model can be printed/represented."""
        with app.app_context():
            config = ServiceConfig(
                service="TMDB",
                api_key_encrypted="key"
            )
            db.session.add(config)
            db.session.commit()

            # Should not raise exception
            str(config)
            repr(config)
