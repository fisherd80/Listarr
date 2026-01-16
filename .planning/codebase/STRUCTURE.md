# Codebase Structure

**Analysis Date:** 2026-01-12

## Directory Layout

```
Listarr - Development/
├── listarr/                    # Main application package
│   ├── forms/                  # Flask-WTF forms
│   ├── models/                 # SQLAlchemy ORM models
│   ├── routes/                 # HTTP route handlers
│   ├── services/               # External API services
│   ├── static/                 # Static assets (CSS, JS)
│   │   └── js/                 # JavaScript files
│   ├── templates/              # Jinja2 templates
│   └── __init__.py             # Flask app factory
├── tests/                      # Test suite
│   ├── integration/            # Integration tests
│   ├── routes/                 # Route handler tests
│   ├── unit/                   # Unit tests
│   └── conftest.py             # Pytest fixtures
├── instance/                   # Runtime data (not in repo)
│   ├── .fernet_key             # Encryption key
│   └── listarr.db              # SQLite database
├── .planning/                  # Planning/documentation
├── run.py                      # Development server entry
├── setup.py                    # First-time setup script
├── Dockerfile                  # Docker build config
├── docker-compose.yml          # Docker Compose config
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
└── .env.example                # Environment template
```

## Directory Purposes

**listarr/**
- Purpose: Main application package
- Contains: All Python source code for the application
- Key files: `__init__.py` (Flask app factory)
- Subdirectories: forms/, models/, routes/, services/, static/, templates/

**listarr/forms/**
- Purpose: Flask-WTF form classes for validation
- Contains: Form definitions with validators
- Key files: `config_forms.py` (RadarrAPIForm, SonarrAPIForm), `settings_forms.py` (TmdbApiForm)
- Subdirectories: None

**listarr/models/**
- Purpose: SQLAlchemy ORM models
- Contains: Database table definitions
- Key files: `service_config_model.py` (ServiceConfig, MediaImportSettings), `lists_model.py` (List), `jobs_model.py` (Job, JobItem), `tag_model.py` (Tag), `user_model.py` (User), `custom_types.py` (TZDateTime)
- Subdirectories: None

**listarr/routes/**
- Purpose: HTTP route handlers
- Contains: Flask blueprints for each feature
- Key files: `dashboard_routes.py`, `config_routes.py`, `settings_routes.py`, `lists_routes.py`, `jobs_routes.py`, `__init__.py` (blueprint registration)
- Subdirectories: None

**listarr/services/**
- Purpose: External API integrations and utilities
- Contains: Service modules for TMDB, Radarr, Sonarr, encryption, caching
- Key files: `tmdb_service.py`, `radarr_service.py`, `sonarr_service.py`, `crypto_utils.py`, `dashboard_cache.py`
- Subdirectories: None

**listarr/static/js/**
- Purpose: Frontend JavaScript for dynamic interactions
- Contains: Vanilla JavaScript files
- Key files: `config.js` (config page interactions), `dashboard.js` (dashboard updates), `settings.js` (settings page interactions)
- Subdirectories: None

**listarr/templates/**
- Purpose: Jinja2 HTML templates
- Contains: HTML templates for each page
- Key files: `base.html` (base layout), `dashboard.html`, `config.html`, `settings.html`, `lists.html`, `jobs.html`
- Subdirectories: None

**tests/**
- Purpose: Test suite
- Contains: Unit, integration, and route tests
- Key files: `conftest.py` (pytest fixtures), `README.md` (test documentation)
- Subdirectories: unit/, integration/, routes/

**instance/**
- Purpose: Runtime data directory
- Contains: Database and encryption key
- Key files: `.fernet_key` (Fernet encryption key), `listarr.db` (SQLite database)
- Subdirectories: None
- Note: Generated at runtime, not in version control

## Key File Locations

**Entry Points:**
- `run.py` - Development server entry point
- `setup.py` - First-time setup (key generation, DB initialization)
- `listarr/__init__.py` - Flask app factory

**Configuration:**
- `requirements.txt` - Python dependencies
- `pytest.ini` - Test configuration
- `.env.example` - Environment variable template
- `Dockerfile` - Docker build configuration
- `docker-compose.yml` - Docker Compose configuration
- `.gitignore` - Git ignore rules

**Core Logic:**
- `listarr/routes/*.py` - HTTP request handlers
- `listarr/services/*.py` - External API integrations
- `listarr/models/*.py` - Database models

**Testing:**
- `tests/unit/*.py` - Unit tests
- `tests/integration/*.py` - Integration tests
- `tests/routes/*.py` - Route handler tests
- `tests/conftest.py` - Shared test fixtures

**Documentation:**
- `README.md` - User-facing installation and usage guide
- `tests/README.md` - Test documentation
- `.planning/` - Planning and codebase documentation

## Naming Conventions

**Files:**
- snake_case for all Python files: `config_routes.py`, `crypto_utils.py`, `tmdb_service.py`
- test_*.py for test files: `test_crypto_utils.py`, `test_config_routes.py`
- Lowercase for templates: `dashboard.html`, `config.html`

**Directories:**
- snake_case for all directories: `listarr/`, `tests/`, `instance/`
- Plural for collections: `routes/`, `models/`, `services/`, `templates/`

**Special Patterns:**
- `__init__.py` for package initialization and blueprint registration
- `conftest.py` for pytest shared fixtures
- `.env.example` for environment variable templates

## Where to Add New Code

**New Route/Endpoint:**
- Primary code: `listarr/routes/<feature>_routes.py`
- Tests: `tests/routes/test_<feature>_routes.py`, `tests/integration/test_<feature>_integration.py`
- Template: `listarr/templates/<feature>.html`
- Frontend: `listarr/static/js/<feature>.js`

**New Database Model:**
- Implementation: `listarr/models/<entity>_model.py`
- Tests: `tests/unit/test_<entity>_model.py`
- Migration: Manual SQL or update `setup.py` to create table

**New External Service Integration:**
- Implementation: `listarr/services/<service>_service.py`
- Tests: `tests/unit/test_<service>_service.py`
- Configuration: Add to `listarr/models/service_config_model.py` if needs API keys

**New Form:**
- Implementation: `listarr/forms/<feature>_forms.py`
- Usage: Import in route handler
- Tests: Test via route tests

**Utilities:**
- Shared helpers: `listarr/services/<utility_name>.py`
- Type definitions: `listarr/models/custom_types.py`

## Special Directories

**instance/**
- Purpose: Runtime-generated data (encryption key, database)
- Source: Generated by `setup.py` on first run
- Committed: No (excluded in `.gitignore`)
- Persistence: Docker volume `listarr-data:/app/instance` in production

**.planning/**
- Purpose: Planning documentation and codebase maps
- Source: Generated by `/gsd:map-codebase` command
- Committed: Yes (tracked in version control)

---

*Structure analysis: 2026-01-12*
*Update when directory structure changes*
