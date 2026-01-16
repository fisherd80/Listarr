# Coding Conventions

**Analysis Date:** 2026-01-12

## Naming Patterns

**Files:**
- snake_case for all Python files: `crypto_utils.py`, `service_config_model.py`, `tmdb_service.py`
- test_*.py for test files: `test_crypto_utils.py`, `test_config_routes.py`
- Lowercase for templates: `dashboard.html`, `config.html`
- Lowercase for JavaScript: `config.js`, `dashboard.js`, `settings.js`

**Functions:**
- snake_case for all functions: `encrypt_data()`, `get_trending_movies()`, `validate_radarr_api_key()`
- Private functions prefixed with underscore: `_get_key_path()`, `_is_valid_url()`, `_calculate_radarr_stats()`
- Boolean-returning functions use descriptive names: `validate_tmdb_api_key()`, `is_enabled`

**Variables:**
- snake_case for all variables: `instance_path`, `api_key_encrypted`, `base_url`, `temp_instance_path`
- Boolean variables prefix with verb: `is_enabled`, `cache_enabled`, `search_on_add`
- Descriptive names preferred over abbreviations: `quality_profile_id` not `qp_id`

**Types:**
- PascalCase for classes: `ServiceConfig`, `List`, `Job`, `RadarrAPIForm`, `TZDateTime`
- PascalCase for database models: `User`, `JobItem`, `MediaImportSettings`, `Tag`
- Database table names in snake_case: `__tablename__ = "service_config"`, `__tablename__ = "lists"`

## Code Style

**Formatting:**
- Indentation: 4 spaces (Python standard)
- Line length: No strict limit, but reasonable wrapping
- Quotes: Double quotes for strings throughout: `"RADARR"`, `"http://localhost:7878"`
- Semicolons: Not used (Python standard)

**Import Organization:**
1. Standard library imports: `from flask import ...`, `from datetime import ...`
2. Third-party imports: `from flask_sqlalchemy import ...`, `from cryptography.fernet import ...`
3. Local imports: `from listarr.routes import ...`, `from listarr.models import ...`
4. Blank line between groups

Example from `listarr/routes/config_routes.py`:
```python
from flask import render_template, flash, request, redirect, url_for, current_app, jsonify
from datetime import datetime, timezone
from urllib.parse import urlparse
from listarr.routes import bp
```

**Linting:**
- No explicit linter configuration detected
- Code follows PEP 8 conventions

## Import Organization

**Order:**
1. Flask and standard library
2. Third-party packages (Flask extensions, libraries)
3. Local application imports (models, services)

**Grouping:**
- Blank line between import groups
- No alphabetical sorting within groups (order by logical grouping)

**Path Aliases:**
- None detected (uses explicit relative imports)

## Error Handling

**Patterns:**
- Throw exceptions, catch at route boundaries
- Database operations use try/except with `db.session.rollback()` on error
- Services log errors but let exceptions bubble up
- Routes catch exceptions and flash user-friendly messages

**Error Types:**
- Catch specific exceptions where possible: `ValueError`, `InvalidToken`
- Some bare `Exception` catches in service validation functions (noted in CONCERNS.md)
- Log errors with `current_app.logger.error(f"...", exc_info=True)`

## Logging

**Framework:**
- Python logging via `current_app.logger`
- Levels: DEBUG, INFO, WARNING, ERROR

**Patterns:**
- Log at service boundaries and error conditions
- Include context in error messages: `f"Error validating Radarr API key: {str(e)}"`
- Use `exc_info=True` for stack traces on errors
- No console.log in production code (except for debugging)

## Comments

**When to Comment:**
- Explain why, not what: `# Check environment variable first`
- Document business logic and edge cases
- Avoid obvious comments: `# Increment counter`

**Docstrings:**
- Triple-quoted docstrings on all public functions and classes
- Multi-line format with Args and Returns sections

Example from `listarr/services/crypto_utils.py`:
```python
def encrypt_data(data: str, instance_path=None) -> str:
    """
    Encrypt data using Fernet encryption.

    Args:
        data (str): The data to encrypt
        instance_path (str): Path to instance folder for key location

    Returns:
        str: Encrypted token as string
    """
```

**Module-Level Documentation:**
- Module docstring at top of file explaining purpose

Example from `tests/routes/test_config_routes.py`:
```python
"""
Route tests for config_routes.py - Config page endpoints.

Tests cover:
- GET /config - Page rendering and data retrieval
- POST /config - API key saving with encryption
...
"""
```

**TODO Comments:**
- Not heavily used in codebase
- Format: `# TODO: description`

## Function Design

**Size:**
- Functions generally under 50 lines
- Some route handlers exceed this (noted in CONCERNS.md)
- Extract helpers for complex logic

**Parameters:**
- Max 3-4 parameters
- Use keyword arguments for optional parameters: `instance_path=None`
- Type hints in function signatures: `def encrypt_data(data: str, instance_path=None) -> str:`

**Return Values:**
- Explicit return statements
- Return early for guard clauses
- Boolean functions return True/False explicitly

## Module Design

**Exports:**
- Named exports (no default exports)
- Public API functions at module level
- Private functions prefixed with underscore

**Barrel Files:**
- `__init__.py` used for package initialization
- Blueprint registration in `listarr/routes/__init__.py`
- No circular dependencies detected

---

*Convention analysis: 2026-01-12*
*Update when patterns change*
