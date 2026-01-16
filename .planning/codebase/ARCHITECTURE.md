# Architecture

**Analysis Date:** 2026-01-12

## Pattern Overview

**Overall:** Monolithic Flask web application with layered MVC-style architecture

**Key Characteristics:**
- Single Flask application with blueprint-based routing
- SQLite embedded database (no external DB required)
- File-based encryption key storage
- In-memory caching for dashboard statistics
- Service layer pattern for external API integrations

## Layers

**HTTP/Web Layer:**
- Purpose: Handle HTTP requests and route to appropriate handlers
- Contains: Flask routes organized by feature domain (`dashboard_routes.py`, `config_routes.py`, `settings_routes.py`, `lists_routes.py`, `jobs_routes.py`)
- Location: `listarr/routes/*.py`
- Depends on: Service layer for business logic, models for data access
- Used by: Client browsers and AJAX requests

**Presentation/Template Layer:**
- Purpose: Server-side HTML rendering
- Contains: Jinja2 templates for each page
- Location: `listarr/templates/*.html`
- Depends on: Route layer for data context
- Used by: Flask render_template calls

**Frontend Client Layer:**
- Purpose: Dynamic UI interactions and AJAX calls
- Contains: Vanilla JavaScript for dashboard updates, config forms, settings
- Location: `listarr/static/js/*.js` (config.js, dashboard.js, settings.js)
- Depends on: Backend API endpoints
- Used by: Browser DOM events

**Service Layer:**
- Purpose: External API integrations and utilities
- Contains: TMDB, Radarr, Sonarr API wrappers, encryption utilities, dashboard cache
- Location: `listarr/services/*.py`
- Depends on: Python stdlib, external API libraries (tmdbv3api, pyarr, cryptography)
- Used by: Route layer

**Data/Persistence Layer:**
- Purpose: Database models and data access
- Contains: SQLAlchemy ORM models (User, ServiceConfig, MediaImportSettings, List, Job, JobItem, Tag)
- Location: `listarr/models/*.py`
- Depends on: SQLAlchemy, custom TZDateTime type
- Used by: Routes and services

**Form/Validation Layer:**
- Purpose: Input validation and CSRF protection
- Contains: Flask-WTF forms (RadarrAPIForm, SonarrAPIForm, TmdbApiForm)
- Location: `listarr/forms/*.py`
- Depends on: WTForms validators
- Used by: Route handlers for POST requests

## Data Flow

**HTTP Request Lifecycle (Dashboard Stats Example):**

1. User navigates to `/` (dashboard page)
2. Route handler `dashboard_routes.py:dashboard_page()` renders template
3. Frontend JavaScript (`dashboard.js`) calls `/api/dashboard/stats?refresh=true`
4. Route handler checks refresh parameter
5. If refresh: call `dashboard_cache.refresh_dashboard_cache()`
   - Fetches ServiceConfig for Radarr/Sonarr
   - Decrypts API keys using `crypto_utils.decrypt_data()`
   - Calls Radarr/Sonarr APIs via `radarr_service.get_system_status()`, `get_movie_count()`, etc.
   - Updates in-memory `_dashboard_cache` with thread lock
6. Return JSON with stats (online/offline status, counts, versions)
7. JavaScript renders HTML with dashboard data

**Configuration Flow (Radarr Setup):**

1. User POST to `/config` with RadarrAPIForm
2. Route validates form (URL, API key present)
3. Route calls `radarr_service.validate_radarr_api_key()` to test connection
4. If valid: encrypt API key using `crypto_utils.encrypt_data()`
5. Save to database (ServiceConfig model with `db.session.commit()`)
6. Update last_tested_at, last_test_status timestamps
7. Trigger dashboard cache refresh
8. Return success flash message and redirect

**State Management:**
- File-based: All persistent state lives in `instance/` directory (database, encryption key)
- In-memory: Dashboard statistics cached in `_dashboard_cache` dict
- Session: Flask sessions for user state (not heavily used)

## Key Abstractions

**Service Pattern:**
- Purpose: Encapsulate external API interactions
- Examples: `listarr/services/tmdb_service.py`, `listarr/services/radarr_service.py`, `listarr/services/sonarr_service.py`
- Pattern: Pure functions, stateless operations, return data structures

**Encryption Abstraction:**
- Purpose: Secure API key storage
- Examples: `listarr/services/crypto_utils.py` (`encrypt_data()`, `decrypt_data()`)
- Pattern: Fernet symmetric encryption with key management

**Dashboard Cache Pattern:**
- Purpose: Improve dashboard load performance
- Examples: `listarr/services/dashboard_cache.py`
- Pattern: In-memory cache with thread lock, lazy initialization, on-demand refresh

**Model-Service-Route Pattern:**
- Purpose: Separation of concerns
- Pattern: Models define data structure → Services provide business logic → Routes orchestrate

## Entry Points

**Development Server:**
- Location: `run.py`
- Triggers: `python run.py` command
- Responsibilities: Load Flask app factory, run development server on port 5000

**Setup Script:**
- Location: `setup.py`
- Triggers: First-time setup or manual invocation
- Responsibilities: Generate encryption key at `instance/.fernet_key`, create database at `instance/listarr.db`, initialize tables

**Docker Production:**
- Location: `Dockerfile`, `docker-compose.yml`
- Triggers: `docker-compose up` or container orchestration
- Responsibilities: Run `setup.py` on first start, start Gunicorn with 2 workers and 4 threads

**Flask App Factory:**
- Location: `listarr/__init__.py` (`create_app()`)
- Triggers: Imported by run.py or Gunicorn
- Responsibilities: Initialize Flask, SQLAlchemy, CSRF protection, load encryption key, register route blueprints, initialize dashboard cache

## Error Handling

**Strategy:** Exception bubbling to route-level handlers with database rollback

**Patterns:**
- Services throw exceptions on API failures (logged but not caught)
- Routes use try/except with `db.session.rollback()` on errors
- Flash messages display user-friendly errors
- AJAX endpoints return JSON with error messages

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging via `current_app.logger`
- Levels: DEBUG, INFO, WARNING, ERROR
- Pattern: Log at service boundaries and error conditions

**Validation:**
- Framework: WTForms validators in form classes
- Pattern: Validate at route layer before processing
- URL validation: `_is_valid_url()` helper in `config_routes.py`

**CSRF Protection:**
- Framework: Flask-WTF
- Pattern: Automatic CSRF tokens in all forms, AJAX requests include tokens

**Encryption:**
- Framework: Fernet (cryptography library)
- Pattern: Encrypt before database save, decrypt on read
- Key management: `instance/.fernet_key` or `FERNET_KEY` env var

---

*Architecture analysis: 2026-01-12*
*Update when major patterns change*
