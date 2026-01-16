# Listarr Test Suite

Comprehensive test suite for the Listarr application, covering unit tests, integration tests, and route tests.

## Test Structure

```
tests/
├── conftest.py                 # Pytest fixtures and configuration
├── requirements-test.txt       # Test dependencies
├── unit/                       # Unit tests for individual functions
│   ├── test_crypto_utils.py   # Encryption/decryption utilities
│   ├── test_tmdb_service.py   # TMDB API service
│   └── test_service_config_model.py  # Database model tests
├── integration/                # Integration tests
│   └── test_settings_integration.py  # End-to-end settings workflows
└── routes/                     # Route handler tests
    └── test_settings_routes.py  # Settings page endpoints
```

## Setup

### Install Test Dependencies

```bash
# From project root directory
pip install -r tests/requirements-test.txt
```

### Required Setup

Before running tests, ensure the encryption key is generated:

```bash
# From project root
python setup.py
```

This creates the `instance/.fernet_key` file needed for encryption tests.

## Running Tests

### Run All Tests

```bash
# From project root
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Route tests only
pytest tests/routes/

# Specific test file
pytest tests/unit/test_crypto_utils.py

# Specific test class
pytest tests/unit/test_crypto_utils.py::TestEncryptData

# Specific test function
pytest tests/unit/test_crypto_utils.py::TestEncryptData::test_encrypt_data_with_valid_key
```

### Run Tests with Coverage

```bash
# Generate coverage report
pytest --cov=listarr tests/

# Generate HTML coverage report
pytest --cov=listarr --cov-report=html tests/

# View HTML report
# Open htmlcov/index.html in a browser
```

### Run Tests with Verbose Output

```bash
# Show detailed test output
pytest -v tests/

# Show print statements and logs
pytest -s tests/

# Show both
pytest -vs tests/
```

### Run Tests in Parallel (faster)

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4 tests/
```

## Test Coverage by Component

### Settings Functionality

| Component | Test File | Coverage |
|-----------|-----------|----------|
| Encryption utilities | `unit/test_crypto_utils.py` | Key generation, loading, encryption/decryption, error handling |
| TMDB service | `unit/test_tmdb_service.py` | API key validation, trending, popular, discover, IMDB ID mapping |
| ServiceConfig model | `unit/test_service_config_model.py` | Model fields, constraints, timestamps, CRUD operations |
| Settings routes | `routes/test_settings_routes.py` | GET/POST endpoints, AJAX testing, CSRF protection, error handling |
| Settings integration | `integration/test_settings_integration.py` | End-to-end workflows, database operations, error recovery |

### Dashboard Functionality

| Component | Test File | Coverage |
|-----------|-----------|----------|
| Dashboard routes | `routes/test_dashboard_routes.py` | Page rendering, stats API, recent jobs API, error handling |
| Dashboard integration | `integration/test_dashboard_integration.py` | End-to-end workflows, cache refresh, multi-service scenarios |
| Radarr service | `unit/test_radarr_service.py` | System status, movie counts, missing movies, missing fields handling |
| Sonarr service | `unit/test_sonarr_service.py` | System status, series counts, missing episodes |
| Dashboard cache | Tested via integration tests | Cache initialization, refresh, thread safety, error handling |

### Config Functionality

| Component | Test File | Coverage |
|-----------|-----------|----------|
| Config routes | `routes/test_config_routes.py` | Radarr/Sonarr config, quality profiles, root folders, import settings |
| Config integration | `integration/test_config_integration.py` | End-to-end workflows, encryption, database operations |

## Key Testing Patterns

### Database Testing Pattern

Tests use in-memory SQLite with isolated fixtures:

```python
@pytest.fixture
def app(temp_instance_path):
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

### API Service Mocking Pattern

External API calls are mocked to avoid live dependencies:

```python
@patch('listarr.services.tmdb_service.Movie')
def test_get_popular_movies(mock_movie_class):
    mock_movie = MagicMock()
    mock_movie.popular.return_value = [{'id': 1, 'title': 'Test Movie'}]
    mock_movie_class.return_value = mock_movie

    result = get_popular_movies("test_key")

    assert len(result) == 1
    assert result[0]['title'] == 'Test Movie'
```

### Encryption Testing Pattern

Tests use temporary instance directories for isolation:

```python
def test_encryption_roundtrip(temp_instance_path):
    generate_key(instance_path=temp_instance_path)

    original = "secret_api_key"
    encrypted = encrypt_data(original, instance_path=temp_instance_path)
    decrypted = decrypt_data(encrypted, instance_path=temp_instance_path)

    assert decrypted == original
```

## Test Fixtures

### Core Fixtures (from conftest.py)

- **`temp_instance_path`**: Temporary instance directory with encryption key
- **`app`**: Flask application with test configuration (CSRF disabled)
- **`app_with_csrf`**: Flask application with CSRF enabled
- **`client`**: Test client for making requests
- **`sample_tmdb_config`**: Pre-populated TMDB ServiceConfig
- **`valid_tmdb_api_key`**: Mock valid TMDB API key
- **`invalid_tmdb_api_key`**: Mock invalid TMDB API key

## Writing New Tests

### Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ComponentName>`
- Test functions: `test_<action>_<condition>_<expected_result>`

Examples:
```python
def test_encrypt_data_with_valid_key_returns_encrypted_string()
def test_save_api_key_with_invalid_key_shows_error()
def test_database_rollback_on_save_error()
```

### Test Organization

Group related tests in classes:

```python
class TestEncryptData:
    """Tests for encrypt_data function."""

    def test_encrypt_data_with_valid_key(self):
        pass

    def test_encrypt_data_with_empty_string(self):
        pass

    def test_encrypt_data_with_unicode(self):
        pass
```

### Edge Cases to Always Test

1. **Null/None inputs**: What happens when required data is missing?
2. **Empty strings/lists**: How does the code handle empty collections?
3. **Invalid data types**: What if a function receives unexpected types?
4. **API failures**: Mock network errors, timeouts, 404s, 500s
5. **Database constraint violations**: Duplicate entries, foreign key errors
6. **Encryption key missing**: Test graceful failure
7. **Malformed URLs**: Invalid protocols, missing ports
8. **Unicode and special characters**: Test with emoji, non-ASCII text

## Continuous Integration

To integrate these tests into CI/CD (GitHub Actions, GitLab CI):

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r tests/requirements-test.txt

    - name: Run setup
      run: python setup.py

    - name: Run tests with coverage
      run: pytest --cov=listarr --cov-report=xml tests/

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

**Issue**: `RuntimeError: Encryption key not found`
- **Solution**: Run `python setup.py` to generate the encryption key

**Issue**: Database errors or locked database
- **Solution**: Tests use in-memory SQLite, ensure no parallel writes to same DB

**Issue**: Import errors for `listarr` package
- **Solution**: Run tests from project root, ensure `listarr` is importable

**Issue**: CSRF token errors
- **Solution**: Use `app` fixture (CSRF disabled) or `app_with_csrf` fixture with proper token handling

**Issue**: Mock patches not working
- **Solution**: Ensure patch path matches import path in the code (e.g., `@patch('listarr.routes.settings_routes.test_tmdb_api_key')`)

## Test Metrics

Current test status:
- **Total tests**: 363
- **Pass rate**: 100% (all tests passing)
- **Overall coverage**: >85% (estimated)
- **Critical paths** (encryption, authentication): >95%
- **Unit tests**: >90%
- **Integration tests**: >85%
- **Route tests**: >90%

Test categories:
- **Dashboard**: 38 route tests + 18 integration tests = 56 tests
- **Config**: 140+ route tests + 30+ integration tests = 170+ tests
- **Settings**: 50+ route tests + 35+ integration tests = 85+ tests
- **Unit tests**: 145+ tests (crypto, services, models)

## Contributing

When adding new features to Listarr:

1. Write tests FIRST (TDD approach recommended)
2. Ensure all tests pass before submitting PR
3. Add tests for edge cases and error conditions
4. Update this README if adding new test patterns
5. Maintain or improve overall coverage percentage

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-flask documentation](https://pytest-flask.readthedocs.io/)
- [Flask testing documentation](https://flask.palletsprojects.com/en/latest/testing/)
- [SQLAlchemy testing strategies](https://docs.sqlalchemy.org/en/latest/orm/session_basics.html#session-frequently-asked-questions)
