"""
Pytest fixtures and configuration for Listarr test suite.

This module provides reusable fixtures for:
- Flask application setup with test configuration
- Test client for making requests
- Database initialization and cleanup
- Encryption key management
- Mock data generation
"""

import os
import tempfile

import pytest
from cryptography.fernet import Fernet

from listarr import create_app, db
from listarr.models.service_config_model import ServiceConfig


@pytest.fixture(scope="function")
def temp_instance_path():
    """
    Create a temporary instance directory for testing.

    This fixture ensures each test has an isolated instance directory
    with its own encryption key and database.

    Yields:
        str: Path to temporary instance directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate encryption key in temp directory
        key_path = os.path.join(tmpdir, ".fernet_key")
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        yield tmpdir


@pytest.fixture(scope="function")
def app(temp_instance_path):
    """
    Create and configure a Flask application instance for testing.

    Uses in-memory SQLite database and temporary instance path for isolation.

    Args:
        temp_instance_path: Temporary instance directory fixture

    Yields:
        Flask: Configured Flask application instance
    """
    # Read the encryption key from the temp directory and set as env var
    # This must be done BEFORE create_app() since it loads the key during init
    key_path = os.path.join(temp_instance_path, ".fernet_key")
    with open(key_path, "rb") as f:
        key = f.read().decode()

    old_fernet_key = os.environ.get("FERNET_KEY")
    os.environ["FERNET_KEY"] = key

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for easier testing
        "SECRET_KEY": "test-secret-key",
    }

    try:
        app = create_app(test_config=test_config)
        app.instance_path = temp_instance_path

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()
    finally:
        # Restore original FERNET_KEY env var
        if old_fernet_key is None:
            os.environ.pop("FERNET_KEY", None)
        else:
            os.environ["FERNET_KEY"] = old_fernet_key


@pytest.fixture(scope="function")
def app_with_csrf(temp_instance_path):
    """
    Create Flask application with CSRF protection enabled.

    Use this fixture when testing CSRF token validation.

    Args:
        temp_instance_path: Temporary instance directory fixture

    Yields:
        Flask: Configured Flask application with CSRF enabled
    """
    # Read the encryption key from the temp directory and set as env var
    # This must be done BEFORE create_app() since it loads the key during init
    key_path = os.path.join(temp_instance_path, ".fernet_key")
    with open(key_path, "rb") as f:
        key = f.read().decode()

    old_fernet_key = os.environ.get("FERNET_KEY")
    os.environ["FERNET_KEY"] = key

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": True,
        "SECRET_KEY": "test-secret-key",
    }

    try:
        app = create_app(test_config=test_config)
        app.instance_path = temp_instance_path

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()
    finally:
        # Restore original FERNET_KEY env var
        if old_fernet_key is None:
            os.environ.pop("FERNET_KEY", None)
        else:
            os.environ["FERNET_KEY"] = old_fernet_key


@pytest.fixture(scope="function")
def client(app):
    """
    Create a test client for making requests to the application.

    Args:
        app: Flask application fixture

    Returns:
        FlaskClient: Test client instance
    """
    return app.test_client()


@pytest.fixture(scope="function")
def client_with_csrf(app_with_csrf):
    """
    Create a test client with CSRF protection enabled.

    Args:
        app_with_csrf: Flask application with CSRF enabled

    Returns:
        FlaskClient: Test client with CSRF protection
    """
    return app_with_csrf.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """
    Create a CLI test runner for the application.

    Args:
        app: Flask application fixture

    Returns:
        FlaskCliRunner: CLI test runner instance
    """
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def sample_tmdb_config(app, temp_instance_path):
    """
    Create a sample TMDB ServiceConfig entry in the database.

    Args:
        app: Flask application fixture
        temp_instance_path: Temporary instance path for encryption

    Returns:
        ServiceConfig: TMDB configuration record
    """
    from datetime import datetime, timezone

    from listarr.services.crypto_utils import encrypt_data

    with app.app_context():
        encrypted_key = encrypt_data("test_tmdb_api_key_12345", instance_path=temp_instance_path)

        config = ServiceConfig(
            service="TMDB",
            api_key_encrypted=encrypted_key,
            last_tested_at=datetime.now(timezone.utc),
            last_test_status="success",
        )
        db.session.add(config)
        db.session.commit()

        return config


@pytest.fixture
def valid_tmdb_api_key():
    """
    Provide a mock valid TMDB API key for testing.

    Returns:
        str: Mock TMDB API key
    """
    return "valid_tmdb_api_key_1234567890abcdef"


@pytest.fixture
def invalid_tmdb_api_key():
    """
    Provide a mock invalid TMDB API key for testing.

    Returns:
        str: Mock invalid TMDB API key
    """
    return "invalid_key"
