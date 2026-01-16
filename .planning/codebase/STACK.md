# Technology Stack

**Analysis Date:** 2026-01-12

## Languages

**Primary:**
- Python 3.11 - All application code (`Dockerfile`, `requirements.txt`)

**Secondary:**
- JavaScript - Frontend interactions (`listarr/static/js/*.js`)
- HTML/Jinja2 - Templates (`listarr/templates/*.html`)

## Runtime

**Environment:**
- Python 3.11 - `Dockerfile` (multi-stage build uses python:3.11-slim)
- Gunicorn 21.2.0 WSGI server - `requirements.txt`, `Dockerfile` CMD (2 workers, 4 threads)

**Package Manager:**
- pip - Python package manager
- Lockfile: requirements.txt with pinned versions

## Frameworks

**Core:**
- Flask 3.0.0 - Web framework (`requirements.txt`, `listarr/__init__.py`)
- Flask-SQLAlchemy 3.1.1 - ORM integration (`requirements.txt`)
- SQLAlchemy 2.0.23 - Database ORM (`requirements.txt`)
- Flask-WTF 1.2.1 - CSRF protection and forms (`requirements.txt`)
- WTForms 3.1.1 - Form validation (`requirements.txt`, `listarr/forms/config_forms.py`)

**Testing:**
- pytest >= 7.4.0 - Test framework (`tests/requirements-test.txt`, `pytest.ini`)
- pytest-flask >= 1.2.0 - Flask testing utilities
- pytest-cov >= 4.1.0 - Coverage reporting
- pytest-mock >= 3.11.1 - Mocking support
- responses >= 0.23.0 - HTTP mocking
- freezegun >= 1.2.0 - Time mocking

**Build/Dev:**
- Docker - Containerization (`Dockerfile`, `docker-compose.yml`)
- Gunicorn - Production WSGI server

## Key Dependencies

**Critical:**
- tmdbv3api >= 1.9.0 - TMDB API client (`requirements.txt`, `listarr/services/tmdb_service.py`)
- pyarr >= 5.0.0 - Radarr/Sonarr API client (`requirements.txt`, `listarr/services/radarr_service.py`, `listarr/services/sonarr_service.py`)
- cryptography >= 41.0.7 - Fernet encryption for API keys (`requirements.txt`, `listarr/services/crypto_utils.py`)
- requests >= 2.31.0 - HTTP client for API calls (`requirements.txt`)

**Infrastructure:**
- Werkzeug 3.0.1 - WSGI utilities (`requirements.txt`)
- SQLite - Embedded database (no separate installation required)

## Configuration

**Environment:**
- Environment variables via `.env` file (`.env.example` provided)
- `LISTARR_SECRET_KEY` - Flask session secret (required in production)
- `FERNET_KEY` - Optional encryption key override (default: `instance/.fernet_key`)
- `FLASK_ENV` - Environment mode (development/production)
- `PORT` - Application port (default 5000)

**Build:**
- No build configuration files for Python (runtime interpreted)
- Docker build configuration: `Dockerfile`, `docker-compose.yml`

## Platform Requirements

**Development:**
- Any platform with Python 3.11+
- No external dependencies beyond Python packages
- SQLite bundled with Python

**Production:**
- Docker container deployment
- Multi-stage build (builder + runtime)
- Non-root user execution (listarr:listarr, UID 1000)
- Health checks configured
- Resource limits: 1 CPU, 512MB RAM
- Volume mount for persistent data: `instance/` directory

---

*Stack analysis: 2026-01-12*
*Update after major dependency changes*
