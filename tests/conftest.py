"""
Pytest fixtures and configuration for Listarr test suite.

This module provides reusable fixtures for:
- Flask application setup with test configuration
- Test client for making requests
- Database initialization and cleanup
- Encryption key management
- Mock data generation
- Authentication fixtures for testing auth routes
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
    LOGIN_DISABLED is set to True to bypass @login_required for existing tests.
    A test user is created to bypass the setup check.

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
        "LOGIN_DISABLED": True,  # Bypass @login_required for existing tests
    }

    try:
        app = create_app(test_config=test_config)
        app.instance_path = temp_instance_path

        with app.app_context():
            db.create_all()

            # Create a default test user to bypass setup check
            # This ensures existing tests don't get redirected to /setup
            from listarr.models.user_model import User

            user = User(username="testuser")
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()

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
def app_with_auth(temp_instance_path):
    """
    Create Flask application with authentication ENABLED.

    Use this fixture for auth-specific tests where login protection
    needs to be tested. Unlike the standard app fixture, this does
    NOT set LOGIN_DISABLED=True.

    Args:
        temp_instance_path: Temporary instance directory fixture

    Yields:
        Flask: Configured Flask application with auth enabled
    """
    # Read the encryption key from the temp directory and set as env var
    key_path = os.path.join(temp_instance_path, ".fernet_key")
    with open(key_path, "rb") as f:
        key = f.read().decode()

    old_fernet_key = os.environ.get("FERNET_KEY")
    os.environ["FERNET_KEY"] = key

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
        # Note: LOGIN_DISABLED is NOT set — auth is active
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
    LOGIN_DISABLED is set to True to bypass @login_required for existing tests.
    A test user is created to bypass the setup check.

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
        "LOGIN_DISABLED": True,  # Bypass @login_required for existing tests
    }

    try:
        app = create_app(test_config=test_config)
        app.instance_path = temp_instance_path

        with app.app_context():
            db.create_all()

            # Create a default test user to bypass setup check
            from listarr.models.user_model import User

            user = User(username="testuser")
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()

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
def auth_client(app_with_auth):
    """
    Create a test client with authentication enabled.

    Use this for testing auth routes and protected endpoints.

    Args:
        app_with_auth: Flask application with auth enabled

    Returns:
        FlaskClient: Test client with auth protection active
    """
    return app_with_auth.test_client()


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
def test_user(app_with_auth):
    """
    Create a test user in the database.

    Creates a user with username="testuser" and password="testpassword".
    Use this fixture when you need a user to exist but don't need to be
    logged in yet.

    Args:
        app_with_auth: Flask application with auth enabled

    Yields:
        User: The created test user object
    """
    from listarr.models.user_model import User

    with app_with_auth.app_context():
        user = User(username="testuser")
        user.set_password("testpassword")
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture(scope="function")
def authenticated_client(auth_client, test_user):
    """
    Create a test client that is already logged in.

    This fixture creates a test user and logs them in via POST to /login.
    Use this when testing routes that require authentication.

    Args:
        auth_client: Test client with auth enabled
        test_user: Test user fixture

    Returns:
        FlaskClient: Test client with active login session
    """
    auth_client.post(
        "/login",
        data={
            "username": "testuser",
            "password": "testpassword",
        },
        follow_redirects=True,
    )
    return auth_client


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
