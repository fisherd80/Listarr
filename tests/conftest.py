"""
Pytest fixtures and configuration for Listarr test suite.

This module provides reusable fixtures for:
- Flask application setup with test configuration
- Test client for making requests
- Database initialization and cleanup
- Encryption key management
- Mock data generation
- Authentication fixtures for testing auth routes

Performance design:
- app/app_with_auth/app_with_csrf are session-scoped: create_app() runs once per session
  instead of once per test, eliminating ~399 redundant app initializations.
- SCHEDULER_WORKER=false prevents APScheduler BackgroundScheduler thread startup during tests.
  Without this, each create_app() would start a real scheduler thread pool.
- StaticPool forces all SQLite connections to share one in-memory database, allowing
  session-scoped app to work with tests that write data and then make HTTP requests.
- db_session is function-scoped with table truncation: each test gets a clean DB
  state without recreating the schema. The begin_nested()/rollback savepoint pattern
  cannot be used here because Flask route handlers call db.session.commit() during
  HTTP requests, which releases SAVEPOINTs unconditionally per SQLAlchemy's design.
  Table truncation is the correct isolation strategy for committing integration tests.
- fernet_key_isolation is a function-scoped autouse fixture that temporarily unsets
  FERNET_KEY for tests that do not use any session-scoped app fixture, so unit tests
  for crypto_utils can test file-based key loading without env-var interference.
- dashboard_cache is reset before each test so tests that expect an empty/unconfigured
  dashboard state are not affected by previous tests that populated the in-memory cache.
"""

import os
import tempfile

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import StaticPool, text

from listarr import create_app, db

# ---------------------------------------------------------------------------
# Session-scoped encryption key (shared across all tests in the session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def temp_instance_path():
    """
    Create a temporary instance directory for the entire test session.

    A single directory with one encryption key is shared across all tests.
    Per-test isolation is achieved via DB table truncation (db_session fixture).

    Yields:
        str: Path to temporary instance directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = os.path.join(tmpdir, ".fernet_key")
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        yield tmpdir


# ---------------------------------------------------------------------------
# Session-scoped Flask app fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app(temp_instance_path):
    """
    Create and configure a Flask application instance for the entire test session.

    Uses in-memory SQLite with StaticPool so all connections share the same DB.
    LOGIN_DISABLED is set to True to bypass @login_required for existing tests.
    A test user is created to bypass the setup check.

    SCHEDULER_WORKER=false prevents APScheduler from starting threads.

    Args:
        temp_instance_path: Temporary instance directory fixture (session-scoped)

    Yields:
        Flask: Configured Flask application instance
    """
    key_path = os.path.join(temp_instance_path, ".fernet_key")
    with open(key_path, "rb") as f:
        key = f.read().decode()

    old_fernet_key = os.environ.get("FERNET_KEY")
    os.environ["FERNET_KEY"] = key
    old_scheduler_worker = os.environ.get("SCHEDULER_WORKER")
    os.environ["SCHEDULER_WORKER"] = "false"

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
        "LOGIN_DISABLED": True,
    }

    try:
        app = create_app(test_config=test_config)
        app.instance_path = temp_instance_path

        with app.app_context():
            db.create_all()

            from listarr.models.user_model import User

            user = User(username="testuser")
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()

            yield app

            db.session.remove()
            db.drop_all()
    finally:
        if old_fernet_key is None:
            os.environ.pop("FERNET_KEY", None)
        else:
            os.environ["FERNET_KEY"] = old_fernet_key

        if old_scheduler_worker is None:
            os.environ.pop("SCHEDULER_WORKER", None)
        else:
            os.environ["SCHEDULER_WORKER"] = old_scheduler_worker


@pytest.fixture(scope="session")
def app_with_auth(temp_instance_path):
    """
    Create Flask application with authentication ENABLED for the entire test session.

    Use this fixture for auth-specific tests where login protection
    needs to be tested. Unlike the standard app fixture, this does
    NOT set LOGIN_DISABLED=True.

    SCHEDULER_WORKER=false prevents APScheduler from starting threads.

    Args:
        temp_instance_path: Temporary instance directory fixture (session-scoped)

    Yields:
        Flask: Configured Flask application with auth enabled
    """
    key_path = os.path.join(temp_instance_path, ".fernet_key")
    with open(key_path, "rb") as f:
        key = f.read().decode()

    old_fernet_key = os.environ.get("FERNET_KEY")
    os.environ["FERNET_KEY"] = key
    old_scheduler_worker = os.environ.get("SCHEDULER_WORKER")
    os.environ["SCHEDULER_WORKER"] = "false"

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
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

        with app.app_context():
            db.session.remove()
            db.drop_all()
    finally:
        if old_fernet_key is None:
            os.environ.pop("FERNET_KEY", None)
        else:
            os.environ["FERNET_KEY"] = old_fernet_key

        if old_scheduler_worker is None:
            os.environ.pop("SCHEDULER_WORKER", None)
        else:
            os.environ["SCHEDULER_WORKER"] = old_scheduler_worker


@pytest.fixture(scope="session")
def app_with_csrf(temp_instance_path):
    """
    Create Flask application with CSRF protection enabled for the entire test session.

    Use this fixture when testing CSRF token validation.
    LOGIN_DISABLED is set to True to bypass @login_required for existing tests.
    A test user is created to bypass the setup check.

    SCHEDULER_WORKER=false prevents APScheduler from starting threads.

    Args:
        temp_instance_path: Temporary instance directory fixture (session-scoped)

    Yields:
        Flask: Configured Flask application with CSRF enabled
    """
    key_path = os.path.join(temp_instance_path, ".fernet_key")
    with open(key_path, "rb") as f:
        key = f.read().decode()

    old_fernet_key = os.environ.get("FERNET_KEY")
    os.environ["FERNET_KEY"] = key
    old_scheduler_worker = os.environ.get("SCHEDULER_WORKER")
    os.environ["SCHEDULER_WORKER"] = "false"

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
        "WTF_CSRF_ENABLED": True,
        "SECRET_KEY": "test-secret-key",
        "LOGIN_DISABLED": True,
    }

    try:
        app = create_app(test_config=test_config)
        app.instance_path = temp_instance_path

        with app.app_context():
            db.create_all()

            from listarr.models.user_model import User

            user = User(username="testuser")
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()

        yield app

        with app.app_context():
            db.session.remove()
            db.drop_all()
    finally:
        if old_fernet_key is None:
            os.environ.pop("FERNET_KEY", None)
        else:
            os.environ["FERNET_KEY"] = old_fernet_key

        if old_scheduler_worker is None:
            os.environ.pop("SCHEDULER_WORKER", None)
        else:
            os.environ["SCHEDULER_WORKER"] = old_scheduler_worker


# ---------------------------------------------------------------------------
# Function-scoped DB isolation: each test gets a clean slate via table truncation
# ---------------------------------------------------------------------------

# Tables to truncate between tests, in dependency order (children before parents)
# to avoid foreign key constraint violations.
_TEST_DATA_TABLES = [
    "job_items",
    "jobs",
    "lists",
    "media_import_settings",
    "service_config",
]

# App fixtures that create a persistent session-level test user at startup.
# These require the users table to be preserved across tests (only non-user
# tables are truncated). app_with_auth does NOT pre-create a user, so its
# users table must also be cleared between tests to prevent test_user fixture
# from hitting UNIQUE constraint violations.
_APPS_WITH_SESSION_USER = {"app", "app_with_csrf"}

# Default dashboard cache values (mirrors the initial values in dashboard_cache.py)
_DEFAULT_RADARR_CACHE = {
    "configured": False,
    "status": "not_configured",
    "version": None,
    "total_movies": 0,
    "missing_movies": 0,
    "added_by_listarr": 0,
}
_DEFAULT_SONARR_CACHE = {
    "configured": False,
    "status": "not_configured",
    "version": None,
    "total_series": 0,
    "missing_episodes": 0,
    "added_by_listarr": 0,
}


def _delete_test_rows(tables):
    """
    Delete all rows from the given tables using the current session.

    Must be called within an active app context. The tables list must be
    ordered with children before parents to satisfy foreign key constraints.

    Args:
        tables: List of table name strings to truncate
    """
    for table in tables:
        db.session.execute(text(f"DELETE FROM {table}"))
    db.session.commit()


def _reset_dashboard_cache():
    """
    Reset the module-level dashboard cache to its default (unconfigured) state.

    With session-scoped app fixtures, the in-memory dashboard cache persists
    between tests. Tests that expect an empty/unconfigured dashboard state
    must have the cache reset before making dashboard API requests.
    """
    import copy

    from listarr.services import dashboard_cache

    with dashboard_cache._cache_lock:
        dashboard_cache._dashboard_cache["radarr"] = copy.deepcopy(_DEFAULT_RADARR_CACHE)
        dashboard_cache._dashboard_cache["sonarr"] = copy.deepcopy(_DEFAULT_SONARR_CACHE)


@pytest.fixture(scope="function", autouse=True)
def db_session(request):
    """
    Ensure each test starts with a clean database state (test data tables empty).

    Truncates all test data tables before and after each test runs. Also resets
    the in-memory dashboard cache so tests see a clean unconfigured state.

    Only activates for tests that use the session-scoped app fixtures.

    The users table handling depends on which app fixture is used:
    - app / app_with_csrf: users table preserved (session-level test user
      created at startup must survive for the setup check to pass)
    - app_with_auth: users table is also truncated (no session-level user;
      test_user fixture creates users per-test and they must not leak)

    The begin_nested()/rollback savepoint pattern is NOT used here because
    Flask route handlers call db.session.commit() during HTTP requests, which
    releases SAVEPOINTs unconditionally per SQLAlchemy's design. Table
    truncation is the correct isolation strategy for committing integration tests.

    Context handling:
    - app: has a persistent session-level app context (from ``with app.app_context():``
      in the fixture). db.session calls here use that context directly.
    - app_with_auth / app_with_csrf: do NOT maintain a persistent app context.
      These fixtures push/pop their context only for setup and teardown. This
      prevents their context from contaminating the main app's context stack.
      For these fixtures, db cleanup must run inside an explicit app context.

    Yields:
        SQLAlchemy session for the current test (or None if no app fixture used)
    """
    # Determine which app fixture this test uses (if any)
    app_fixture = None
    active_fixture_name = None
    for fixture_name in ("app", "app_with_auth", "app_with_csrf"):
        if fixture_name in request.fixturenames:
            app_fixture = request.getfixturevalue(fixture_name)
            active_fixture_name = fixture_name
            break

    if app_fixture is None:
        # Test doesn't use any session-scoped app fixture — nothing to do
        yield None
        return

    # For app_with_auth, also clear users since there's no session-level user
    include_users = active_fixture_name not in _APPS_WITH_SESSION_USER
    tables_to_clear = _TEST_DATA_TABLES + (["users"] if include_users else [])

    # app has a persistent app context; app_with_auth/app_with_csrf do not.
    # For the latter two, push a context explicitly for cleanup operations.
    needs_explicit_context = active_fixture_name in ("app_with_auth", "app_with_csrf")

    if needs_explicit_context:
        with app_fixture.app_context():
            _delete_test_rows(tables_to_clear)
            db.session.remove()
    else:
        # app fixture keeps the context open — db.session works directly
        _delete_test_rows(tables_to_clear)
        db.session.remove()

    # Reset in-memory dashboard cache to unconfigured defaults
    _reset_dashboard_cache()

    yield db.session

    # Clean state after the test (guards against incomplete test cleanup)
    if needs_explicit_context:
        with app_fixture.app_context():
            _delete_test_rows(tables_to_clear)
            db.session.remove()
    else:
        _delete_test_rows(tables_to_clear)
        db.session.remove()


# ---------------------------------------------------------------------------
# Isolation fixture for crypto unit tests (FERNET_KEY env var cleanup)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function", autouse=True)
def fernet_key_isolation(request):
    """
    Temporarily unset FERNET_KEY for tests that do not use a session-scoped app.

    The session-scoped app fixtures (app, app_with_auth, app_with_csrf) set the
    FERNET_KEY environment variable as a process-wide side effect and keep it set
    for the entire test session. Unit tests in test_crypto_utils.py that test
    file-based key loading expect FERNET_KEY to be absent, but find the
    session-level value instead, causing incorrect behavior.

    This fixture saves and temporarily removes FERNET_KEY for tests that don't
    use any session-scoped app fixture, restoring it after the test completes.
    Tests that use the app fixtures are not affected.

    Yields:
        None
    """
    uses_session_app = any(fname in request.fixturenames for fname in ("app", "app_with_auth", "app_with_csrf"))

    if uses_session_app:
        # App tests need FERNET_KEY set — don't touch it
        yield
        return

    # Non-app tests: temporarily remove FERNET_KEY so file-based loading works
    saved_key = os.environ.pop("FERNET_KEY", None)
    try:
        yield
    finally:
        if saved_key is not None:
            os.environ["FERNET_KEY"] = saved_key


# ---------------------------------------------------------------------------
# Function-scoped client fixtures
# ---------------------------------------------------------------------------


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

    from listarr.models.service_config_model import ServiceConfig
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
