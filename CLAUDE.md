# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Listarr is a single-user, self-hosted Flask application for discovering content via TMDB (The Movie Database) and importing curated lists into Radarr/Sonarr media servers. Designed for homelab environments with Docker deployment.

**Design Philosophy**: Read-only + Push Actions

- View stats from Radarr/Sonarr
- Generate curated lists from TMDB
- Push imports to media servers
- **No full media management** (view-only dashboard, no edit/delete of existing media)

## Development Commands

```bash
# First-time setup: Generate encryption key and create database
python setup.py

# Run development server (debug off by default)
python run.py

# Enable debug mode
FLASK_DEBUG=true python run.py

# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=listarr --cov-report=html tests/

# Run specific test file
pytest tests/routes/test_config_routes.py -v
```

The app runs on `http://localhost:5000` by default.

## Design Principles & Scope

### Purpose & Deployment

- **Single-user application** - no multi-user support, roles, or permissions
- **Self-hosted homelab utility** - not designed for open internet exposure
- **Docker-first** with persistent volume support (container rebuild must not lose data)

### Core Behavior Model

1. **Dashboard** (`/`): Read-only stats from Radarr/Sonarr with auto-refresh
2. **Lists** (`/lists`): Stepper/wizard UI for discovering and previewing TMDB content
3. **Import**: Queue-based push to Radarr/Sonarr via background jobs
4. **Jobs** (`/jobs`): Central activity monitoring
5. **Schedule** (`/schedule`): Per-list cron automation with global pause/resume
6. **Config** (`/config`): Radarr/Sonarr connection and import settings
7. **Settings** (`/settings`): TMDB API key management

### Import Logic

- **Global Import Settings** configured on Config page (quality profile, root folder, monitor, search on add, tags)
- **Per-list overrides** available in wizard Step 3 (fall back to global defaults when not set)
- **Conflict handling**: Already exists → skip; Movies → Radarr; TV → Sonarr
- **Queue-based execution**: No immediate add, no dry-run; Jobs track all activity

### Security Design

- **API keys encrypted at rest** (Fernet symmetric encryption)
- **API keys masked in UI** (toggle eye icon to reveal)
- **CSRF protection** (Flask-WTF) on all forms and AJAX requests
- **Logs sanitized** (no secrets, API keys, or tokens)
- **URL validation** before saving or testing connections

## Architecture

### Directory Structure

```
listarr/
├── __init__.py          # Application factory (create_app)
├── models/              # SQLAlchemy models
├── routes/              # Flask blueprint route handlers
├── services/            # Business logic and external API clients
├── forms/               # WTForms form classes
├── utils/               # Shared utilities (time formatting)
├── templates/           # Jinja2 HTML templates
└── static/
    └── js/              # Page-specific JavaScript modules
tests/
├── unit/                # Unit tests for services and utilities
├── routes/              # Route handler tests
└── integration/         # End-to-end integration tests
instance/                # Runtime data (DB, encryption key) - NOT committed
```

### Application Factory

`create_app()` in `listarr/__init__.py`:

- Initializes SQLAlchemy with `db` instance and Flask-WTF CSRF
- Configures logging from `LOG_LEVEL` environment variable
- Loads Fernet encryption key (fails if missing)
- Registers the main blueprint from `listarr/routes`
- Sets SQLite WAL mode with DELETE fallback (for network filesystems)
- Initializes dashboard cache at startup
- Recovers interrupted jobs (marks stale "running" jobs as "failed")
- Initializes APScheduler in designated worker

### Database Models

Located in `listarr/models/`:

- **ServiceConfig** (`service_config_model.py`): Encrypted API keys and connection details for TMDB, Radarr, Sonarr. Tracks `last_tested_at`/`last_test_status`. `scheduler_paused` flag for global pause.
- **MediaImportSettings** (`service_config_model.py`): Default import settings per service (root folder, quality profile, monitored, search on add, tags, season folder for Sonarr)
- **List** (`lists_model.py`): TMDB list definitions with target_service, tmdb_list_type, filters_json, cache settings, schedule_cron, and per-list import overrides
- **Job** & **JobItem** (`jobs_model.py`): Execution tracking with status (pending/running/failed/completed), metrics (items_found/added/skipped), error details, and per-item results. Job has relationship to List.
- **CustomTypes** (`custom_types.py`): `TZDateTime` TypeDecorator — ensures timezone-aware UTC datetimes in SQLite
- **User** (`user_model.py`): User model (authentication not yet implemented)

### Routing Structure

All routes registered under a single blueprint `bp` in `listarr/routes/__init__.py`:

- **`dashboard_routes.py`**: `GET /`, `GET /api/dashboard/stats`, `GET /api/dashboard/recent-jobs`
- **`lists_routes.py`**: `GET /lists`, `GET/POST /lists/create`, `GET/POST /lists/<id>/edit`, `POST /lists/<id>/delete`, `POST /lists/<id>/execute`, `GET /api/lists/preview`
- **`jobs_routes.py`**: `GET /jobs`, `GET /api/jobs`
- **`schedule_routes.py`**: `GET /schedule`, `POST /schedule/pause`, `POST /schedule/resume`, `GET /api/schedule/status`
- **`config_routes.py`**: Parameterized routes using `<service>` variable:
  - `GET/POST /config` - Main config page with Radarr/Sonarr forms
  - `POST /config/test_radarr_api`, `POST /config/test_sonarr_api` - AJAX test connections
  - `GET /config/<service>/quality-profiles` - Fetch quality profiles
  - `GET /config/<service>/root-folders` - Fetch root folders
  - `GET /config/<service>/import-settings` - Retrieve saved settings
  - `POST /config/<service>/import-settings` - Save import settings
  - Helper functions: `_is_valid_url()`, `_save_service_config()`, `_test_service_api()`, `_test_and_update_service_status()`
- **`settings_routes.py`**: `GET/POST /settings`, `POST /settings/test_tmdb_api`

### Services Layer

Business logic in `listarr/services/`:

- **`http_client.py`**: Shared HTTP session with connection pooling and retry logic
  - Module-level `http_session` (requests.Session) used by all external API calls
  - Retry strategy: 3 retries with exponential backoff on 429/5xx
  - Connection pool: 10 connections
  - `normalize_url(base_url)` - Strips trailing slashes
  - `API_BASE_TMDB` constant for TMDB base URL
  - `DEFAULT_TIMEOUT` = 30 seconds, `BULK_TIMEOUT` = 300 seconds for bulk operations

- **`arr_service.py`**: Shared Radarr/Sonarr API helpers (eliminates duplication)
  - `arr_api_get(base_url, api_key, endpoint)` - GET request to *arr API v3
  - `arr_api_post(base_url, api_key, endpoint, data)` - POST request to *arr API v3
  - `validate_api_key(base_url, api_key)` - Test connection via system/status
  - `get_quality_profiles(base_url, api_key)` - Fetch quality profiles
  - `get_root_folders(base_url, api_key)` - Fetch root folders
  - `get_system_status(base_url, api_key)` - System version/status info
  - `get_tags(base_url, api_key)` - Fetch tags
  - `create_or_get_tag_id(base_url, api_key, tag_label)` - Create-if-missing tag pattern

- **`radarr_service.py`**: Radarr-specific functions (delegates shared ops to arr_service)
  - `get_movie_count()`, `get_missing_movies_count()` - Dashboard stats
  - `get_existing_movie_tmdb_ids()`, `get_exclusions()` - Pre-flight checks
  - `lookup_movie(base_url, api_key, tmdb_id)` - TMDB ID lookup for import
  - `add_movie(...)` - Add single movie with quality profile, root folder, tags
  - `bulk_add_movies(base_url, api_key, movies)` - Batch import via /api/v3/movie/import

- **`sonarr_service.py`**: Sonarr-specific functions (delegates shared ops to arr_service)
  - `get_series_count()`, `get_missing_series_count()` - Dashboard stats
  - `get_existing_series_tvdb_ids()`, `get_exclusions()` - Pre-flight checks
  - `lookup_series(base_url, api_key, tvdb_id)` - TVDB ID lookup for import
  - `add_series(...)` - Add single series with quality profile, root folder, tags, season folder
  - `bulk_add_series(base_url, api_key, series)` - Batch import via /api/v3/series/import

- **`tmdb_service.py`**: TMDB API integration using direct HTTP calls
  - `validate_tmdb_api_key(api_key)` - Test API key validity
  - `get_trending_movies/tv()`, `get_popular_movies/tv()`, `get_top_rated_movies/tv()` - List sources
  - `discover_movies/tv(api_key, filters, page)` - Advanced discovery with filters
  - `get_movie_details/tv_details()` - Detailed information retrieval
  - `get_imdb_id_from_tmdb()` - Legal IMDB ID mapping via external_ids

- **`tmdb_cache.py`**: In-memory caching layer for TMDB API results
  - TTL-based cache with region filtering support
  - Cached variants: `get_trending_movies_cached()`, `get_popular_movies_cached()`, `get_top_rated_movies_cached()`, `discover_movies_cached()`, etc.

- **`import_service.py`**: Import orchestration with bulk API
  - `import_list(list_id)` - Full import flow: fetch TMDB → deduplicate → batch add to *arr
  - `BATCH_SIZE = 50` - Items per bulk import batch
  - Uses `ImportResult` dataclass for structured results
  - Applies per-list overrides or global import settings
  - Bulk import via `bulk_add_movies()`/`bulk_add_series()` for 8x faster execution

- **`job_executor.py`**: Background job execution
  - ThreadPoolExecutor with configurable max workers (default: 3)
  - Activity-based idle timeout (`IDLE_TIMEOUT_SECONDS = 300`) - jobs timeout after 5 min of inactivity
  - `ActivityTracker` class for thread-safe last-activity tracking
  - Thread-safe stop event management
  - Creates Job/JobItem records in database

- **`dashboard_cache.py`**: In-memory dashboard stats caching
  - Thread-safe with `threading.Lock` and startup initialization
  - Sequential API calls to Radarr/Sonarr for stats
  - "Added by Listarr" counter from completed jobs

- **`scheduler.py`**: APScheduler integration for cron automation
  - Singleton BackgroundScheduler instance
  - `schedule_list()`, `unschedule_list()`, `pause_scheduler()`, `resume_scheduler()`
  - `get_next_runs()`, `validate_cron_expression()`
  - Loads existing schedules from database on startup
  - Single-worker pattern: only one Gunicorn worker runs scheduler

- **`crypto_utils.py`**: Fernet encryption/decryption for API keys
  - `encrypt_data(data, instance_path)`, `decrypt_data(encrypted_data, instance_path)`
  - `load_encryption_key(instance_path)`, `generate_key()`

### Static JavaScript

- **`utils.js`**: Shared utilities (`formatTimestamp()`, `fetchWithTimeout()`, `generateStatusHTML()`, `escapeHtml()`, `getCsrfToken()`, `formatRelativeTime()`, `debounce()`)
- **`toast.js`**: Toast notification system (`showToast(message, type, duration)`)
- **`config.js`**: Config page handlers (parameterized fetch/save for both services)
- **`settings.js`**: Settings page handlers
- **`dashboard.js`**: Dashboard auto-refresh (5-minute interval), stats display, skeleton loading
- **`lists.js`**: List table operations, manual execution, delete confirmation
- **`wizard.js`**: Multi-step list creation wizard with live TMDB preview, timeout handling
- **`jobs.js`**: Job monitoring with pagination, filtering, auto-refresh, visibility-based polling
- **`schedule.js`**: Schedule page with pause/resume, status polling, server-rendered badges

### Jinja Macros

Located in `listarr/templates/macros/`:

- **`status.html`**: `status_badge(status)`, `service_badge(service)` - Consistent badge rendering
- **`ui.html`**: `loading_spinner()`, `empty_state()`, `error_state()` - Reusable UI components
- **`forms.html`**: `import_settings_form(service)` - Config page form macro (47% reduction)

## UI/UX Patterns

### Toast Notifications

Use JavaScript toast notifications (not Flask flash messages) for user feedback.

**Location**: `listarr/static/js/toast.js`

```javascript
showToast("Operation successful!", "success");  // green
showToast("Something failed.", "error");         // red
showToast("Partial result.", "warning");          // yellow
showToast("Processing...", "info");               // blue
```

Auto-dismisses after 3 seconds. Fixed position top-right. Dark mode support. XSS-safe.

### AJAX Pattern

All AJAX requests must include the CSRF token:

```javascript
const csrfToken = getCsrfToken(); // from utils.js
fetch("/endpoint", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
  body: JSON.stringify({ data: value }),
})
  .then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(data => {
    if (data.success) showToast(data.message, "success");
    else showToast(data.message || "Operation failed", "error");
  })
  .catch(error => showToast("Network error. Please try again.", "error"));
```

### Global Styles

- Tailwind CSS with system-based dark mode
- Single-page feel with top navigation
- Skeleton loading states for initial load
- Buttons disabled during actions

## Development Notes

### Error Handling

- **Routes**: Try/except with `db.session.rollback()` on database errors, `current_app.logger.error()` with `exc_info=True`
- **Services**: Module-level loggers (`logger = logging.getLogger(__name__)`), return empty lists/dicts on errors
- **Frontend**: HTTP status checks on all fetch calls, toast notifications for errors

### Architecture Patterns

- **Blueprint pattern**: `from listarr.routes import bp` → `@bp.route()`
- **Parameterized routes**: Config routes use `<service>` URL variable to eliminate Radarr/Sonarr duplication
- **Service delegation**: `radarr_service.py` and `sonarr_service.py` delegate shared operations to `arr_service.py`
- **Shared HTTP session**: All external API calls go through `http_client.http_session`
- **Helper functions**: `_save_service_config()`, `_test_service_api()` eliminate duplication in routes

### Security & Encryption

- **Encryption key required**: App will not start without it. Run `setup.py` first.
- **Instance path**: Always pass `current_app.instance_path` when calling crypto functions from routes
- **CSRF**: Meta tag in base.html (`<meta name="csrf-token">`), `{{ form.hidden_tag() }}` in forms, `X-CSRFToken` header in AJAX
- **URL validation**: `_is_valid_url()` in config_routes.py validates format before saving/testing

### Testing

- **493 tests** across unit, route, and integration test files
- Proper isolation with fixtures (`temp_instance_path`, `app`, `client`)
- External API calls mocked; in-memory SQLite for speed
- Comprehensive coverage: error handling, validation, edge cases, security, caching, bulk imports

### Instance Folder

`instance/` at project root stores runtime data:

- `listarr.db`: SQLite database
- `.fernet_key`: Encryption key (NEVER commit)

Created automatically by `create_app()` and `setup.py`. Flask's `app.instance_path` resolves to this location.

## Dependencies

<!-- GENERATED:START:dependencies -->
Defined in `requirements.txt`:

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | ==3.0.0 | Web framework |
| Flask-SQLAlchemy | ==3.1.1 | ORM |
| SQLAlchemy | ==2.0.44 | Database toolkit |
| Flask-WTF | ==1.2.1 | Forms + CSRF protection |
| WTForms | ==3.1.1 | Form validation |
| cachetools | >=5.3.0 | Caching utilities |
| cryptography | ==44.0.1 | Fernet encryption for API keys |
| requests | ==2.32.4 | HTTP client for all external APIs |
| gunicorn | ==22.0.0 | Production WSGI server |
| APScheduler | ==3.11.2 | Cron-based job scheduling |
| cronsim | ==2.7 | Cron expression parsing |
| cron-descriptor | ==2.0.5 | Human-readable cron descriptions |

**No third-party API wrappers** - all Radarr, Sonarr, and TMDB API calls use direct HTTP via the shared `http_session`.
<!-- GENERATED:END:dependencies -->

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LISTARR_SECRET_KEY` | `dev_key_change_me` | Flask secret key |
| `FERNET_KEY` | (from file) | Override encryption key (otherwise loaded from `instance/.fernet_key`) |
| `FLASK_DEBUG` | `False` | Enable Flask debug mode |
| `LOG_LEVEL` | `INFO` | Python logging level (DEBUG, INFO, WARNING, ERROR) |
| `TZ` | UTC | Server timezone for cron schedule interpretation |
| `SCHEDULER_WORKER` | `true` | Internal Gunicorn flag (auto-managed, do not set manually) |

## Current Development Status

**Completed phases** (1-10.5): List management, wizard UI, TMDB caching, tags, import automation, manual triggers, job execution framework, bug fixes, list enhancements (top rated, regions), comprehensive testing (493 tests), scheduler system with health checks, architecture consolidation (removed pyarr/tmdbv3api), code quality refactoring, config & JS deduplication, UI/UX simplification (Jinja macros, utils.js), bulk import API (8x faster), skeleton loading states, activity-based timeout.

**Next phase**: 11 (Security Hardening)

**Remaining phases**: 11 (Security Hardening), 12 (Release Readiness)

See `.planning/ROADMAP.md` for full phase details.

## Developer Tooling

Scripts in `_ai/scripts/` (gitignored, local only):

- **`squash_ai.py`**: Squash-merge workflow — auto-detects feature branch, runs pre-commit, squash merges to develop, pushes, updates CLAUDE.md via Claude CLI as milestone checkpoint
- **`sync_claude_md.py`**: Auto-syncs generated sections (dependencies table) between `<!-- GENERATED -->` markers from `requirements.txt`
- **`guard_claude_md.py`**: Pre-commit hook — non-blocking warning when structural files change without CLAUDE.md update (updated at squash-merge milestones)

### Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:

- **ruff** + **ruff-format**: Python linting and formatting
- **black**: Python code formatting
- **sync-claude-md**: Syncs generated sections on `requirements.txt` changes
- **guard-claude-md**: Warning when structural files change (non-blocking)
