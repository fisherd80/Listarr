# Listarr Test Suite

Automated test suite covering unit tests, integration tests, and route tests.

## Test Structure

```
tests/
├── conftest.py                        # Pytest fixtures and shared configuration
├── unit/                              # Unit tests for individual functions/classes
│   ├── test_crypto_utils.py          # Encryption/decryption utilities
│   ├── test_radarr_service.py        # Radarr API service
│   ├── test_sonarr_service.py        # Sonarr API service
│   ├── test_service_config_model.py  # ServiceConfig database model
│   ├── test_tmdb_service.py          # TMDB API service
│   ├── test_tmdb_cache.py            # TMDB caching layer
│   ├── test_time_utils.py            # Time/timezone utilities
│   ├── test_user_model.py            # User model
│   └── services/
│       ├── test_import_service.py    # Import orchestration service
│       ├── test_job_executor.py      # Job execution service
│       └── test_scheduler.py         # APScheduler integration
├── integration/                       # Integration tests
│   ├── test_import_integration.py    # Import service end-to-end workflows
│   └── test_settings_integration.py  # Settings end-to-end workflows
└── routes/                            # Route handler tests
    ├── test_auth_routes.py            # Authentication endpoints
    ├── test_activity_routes.py        # Activity page endpoints
    ├── test_lists_routes.py           # Lists page and API endpoints
    └── test_settings_routes.py        # Settings page endpoints
```

## Setup

Install dev dependencies (includes pytest, coverage, and test utilities):

```bash
pip install -r requirements-dev.txt
```

Generate the encryption key and database before running tests:

```bash
python manage.py
```

## Running Tests

```bash
pytest tests/                            # Run all tests (600+)
pytest tests/unit/                       # Unit tests only
pytest tests/integration/                # Integration tests only
pytest tests/routes/                     # Route tests only
pytest --cov=listarr tests/             # Run with coverage (CI requires 60%)
pytest -k "test_name"                    # Run a single test by name
pytest -m encryption                     # Run by marker
```

## Key Testing Patterns

### Database Isolation

Tests use in-memory SQLite with `StaticPool` so all connections share one in-memory DB. The session-scoped app fixture creates tables once; per-test cleanup truncates tables between tests (children before parents) rather than using savepoints — route handlers call `db.session.commit()` unconditionally, which releases any savepoint.

```python
@pytest.fixture(scope="session")
def app(temp_instance_path):
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SCHEDULER_WORKER": "false",
    }
    ...
```

### API Mocking

External API calls are mocked via `@patch` or the `responses` library to avoid live dependencies:

```python
@patch("listarr.services.tmdb_service.http_session")
def test_get_popular_movies(mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"id": 1, "title": "Test Movie"}]}
    mock_session.get.return_value = mock_response
    result = get_popular_movies("test_key")
    assert result[0]["title"] == "Test Movie"
```

### Encryption Isolation

The `fernet_key_isolation` fixture unsets `FERNET_KEY` to test file-based key loading with temporary instance directories:

```python
def test_encryption_roundtrip(temp_instance_path):
    generate_key(instance_path=temp_instance_path)
    encrypted = encrypt_data("secret_key", instance_path=temp_instance_path)
    assert decrypt_data(encrypted, instance_path=temp_instance_path) == "secret_key"
```

### CSRF Testing

Default `app` fixture has CSRF disabled. Use `app_with_csrf` fixture for tests that need CSRF protection:

```python
def test_form_submit_requires_csrf_token(app_with_csrf, client):
    ...
```

## Test Coverage by Component

| Component | Test File(s) |
|-----------|-------------|
| Encryption utilities | `unit/test_crypto_utils.py` |
| User model | `unit/test_user_model.py` |
| ServiceConfig model | `unit/test_service_config_model.py` |
| TMDB service + cache | `unit/test_tmdb_service.py`, `unit/test_tmdb_cache.py` |
| Radarr / Sonarr services | `unit/test_radarr_service.py`, `unit/test_sonarr_service.py` |
| Import service | `unit/services/test_import_service.py`, `integration/test_import_integration.py` |
| Job executor | `unit/services/test_job_executor.py` |
| Scheduler | `unit/services/test_scheduler.py` |
| Authentication routes | `routes/test_auth_routes.py` |
| Settings routes | `routes/test_settings_routes.py`, `integration/test_settings_integration.py` |
| Lists routes | `routes/test_lists_routes.py` |
| Activity routes | `routes/test_activity_routes.py` |

## Troubleshooting

**`RuntimeError: Encryption key not found`** — Run `python manage.py` to generate `instance/.fernet_key`.

**Database errors** — Tests use in-memory SQLite; ensure `SQLALCHEMY_DATABASE_URI=sqlite:///:memory:` in test config.

**Import errors for `listarr`** — Run tests from the project root directory.

**Scheduler errors** — `SCHEDULER_WORKER=false` prevents APScheduler thread startup during tests; verify it is set in test config.
