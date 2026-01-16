# Testing Patterns

**Analysis Date:** 2026-01-12

## Test Framework

**Runner:**
- pytest - Test framework
- Config: `pytest.ini` in project root

**Assertion Library:**
- pytest built-in `assert`
- Matchers: Standard Python comparisons (==, is, in, etc.)

**Run Commands:**
```bash
pytest tests/                              # Run all tests
pytest -v tests/                           # Verbose output
pytest tests/unit/                         # Unit tests only
pytest tests/integration/                  # Integration tests only
pytest tests/routes/                       # Route tests only
pytest --cov=listarr tests/                # With coverage
pytest --cov=listarr --cov-report=html     # HTML coverage report
```

## Test File Organization

**Location:**
- Unit tests in `tests/unit/` alongside test subject
- Integration tests in `tests/integration/`
- Route tests in `tests/routes/`

**Naming:**
- Unit tests: `test_<module_name>.py` (e.g., `test_crypto_utils.py`)
- Integration tests: `test_<feature>_integration.py` (e.g., `test_config_integration.py`)
- Route tests: `test_<feature>_routes.py` (e.g., `test_config_routes.py`)

**Structure:**
```
tests/
├── conftest.py                          # Shared fixtures
├── unit/
│   ├── test_crypto_utils.py            # Encryption/decryption
│   ├── test_tmdb_service.py            # TMDB API service
│   ├── test_radarr_service.py          # Radarr API service
│   ├── test_sonarr_service.py          # Sonarr API service
│   └── test_service_config_model.py    # Database model
├── integration/
│   ├── test_settings_integration.py    # Settings workflows
│   ├── test_config_integration.py      # Config workflows
│   └── test_dashboard_integration.py   # Dashboard workflows
├── routes/
│   ├── test_settings_routes.py         # Settings endpoints
│   ├── test_config_routes.py           # Config endpoints
│   └── test_dashboard_routes.py        # Dashboard endpoints
└── README.md                            # Test documentation
```

## Test Structure

**Suite Organization:**
```python
import pytest
from unittest.mock import patch, MagicMock

class TestEncryptData:
    """Tests for encrypt_data function."""

    def test_encrypt_data_with_valid_key(self, temp_instance_path):
        # arrange
        generate_key(instance_path=temp_instance_path)
        data = "secret_api_key"

        # act
        encrypted = encrypt_data(data, instance_path=temp_instance_path)

        # assert
        assert encrypted is not None
        assert encrypted != data
```

**Patterns:**
- Group related tests in classes by component
- Use descriptive class names: `TestRadarrConfigPOST`, `TestEncryptData`
- Arrange-Act-Assert pattern in test bodies
- Use fixtures for setup (`temp_instance_path`, `app`, `client`)

## Mocking

**Framework:**
- unittest.mock (Python standard library)
- pytest-mock plugin

**Patterns:**
```python
# Mock external API calls
@patch('listarr.services.tmdb_service.Movie')
def test_get_popular_movies(mock_movie_class):
    mock_movie = MagicMock()
    mock_movie.popular.return_value = [{'id': 1, 'title': 'Test Movie'}]
    mock_movie_class.return_value = mock_movie

    result = get_popular_movies("test_key")

    assert len(result) == 1
    assert result[0]['title'] == 'Test Movie'

# Mock route dependencies
@patch('listarr.routes.config_routes.validate_radarr_api_key')
def test_save_radarr_config(mock_validate, client):
    mock_validate.return_value = True
    response = client.post('/config', data={...})
    assert response.status_code == 200
```

**What to Mock:**
- External API calls (TMDB, Radarr, Sonarr)
- File system operations (in some tests)
- Network requests
- Time/dates (using freezegun)

**What NOT to Mock:**
- Database operations (use in-memory SQLite)
- Encryption utilities (test actual encryption)
- Flask request/response objects (use test client)

## Fixtures and Factories

**Test Data:**
```python
# Fixture pattern from tests/conftest.py
@pytest.fixture(scope='function')
def temp_instance_path(tmp_path):
    """Temporary instance directory with encryption key."""
    instance_path = tmp_path / "instance"
    instance_path.mkdir()
    generate_key(instance_path=str(instance_path))
    return str(instance_path)

@pytest.fixture(scope='function')
def app(temp_instance_path):
    """Flask application with test configuration."""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    }
    app = create_app(test_config=test_config)
    app.instance_path = temp_instance_path

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
```

**Location:**
- Shared fixtures: `tests/conftest.py`
- Test-specific factories: Defined in test files

## Coverage

**Requirements:**
- Overall coverage target: >85%
- Critical paths (encryption, authentication): >95%
- No enforced minimum per file

**Configuration:**
From `pytest.ini`:
```ini
[coverage:run]
source = listarr
omit =
    */tests/*
    */venv/*
    */__pycache__/*

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
```

**View Coverage:**
```bash
pytest --cov=listarr --cov-report=html tests/
# Open htmlcov/index.html in browser
```

## Test Types

**Unit Tests:**
- Scope: Test single function/class in isolation
- Mocking: Mock all external dependencies
- Speed: Fast (<1s per test)
- Location: `tests/unit/`
- Example: `test_crypto_utils.py` (encryption roundtrip, key generation)

**Integration Tests:**
- Scope: Test multiple modules together
- Mocking: Mock external services, use real internal modules
- Setup: In-memory database, temporary instance directory
- Location: `tests/integration/`
- Example: `test_config_integration.py` (full save → reload → verify workflow)

**Route Tests:**
- Scope: Test HTTP endpoints
- Mocking: Mock service layer dependencies
- Setup: Test client with CSRF disabled
- Location: `tests/routes/`
- Example: `test_config_routes.py` (GET/POST endpoints, AJAX calls)

## Common Patterns

**Async Testing:**
Not applicable (no async code in codebase)

**Error Testing:**
```python
def test_encrypt_data_with_missing_key_raises_error(temp_instance_path):
    # Remove the key file
    key_path = os.path.join(temp_instance_path, ".fernet_key")
    os.remove(key_path)

    with pytest.raises(RuntimeError, match="Encryption key not found"):
        encrypt_data("test", instance_path=temp_instance_path)
```

**Database Testing:**
```python
def test_service_config_crud(app):
    with app.app_context():
        # Create
        config = ServiceConfig(service="TMDB", api_key_encrypted="encrypted")
        db.session.add(config)
        db.session.commit()

        # Read
        found = ServiceConfig.query.filter_by(service="TMDB").first()
        assert found is not None
        assert found.service == "TMDB"
```

**Snapshot Testing:**
- Not used in this codebase

---

*Testing analysis: 2026-01-12*
*Update when test patterns change*
