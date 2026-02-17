# Changelog

All notable changes to the Listarr project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned (Phase 13)

- **Phase 13: Release Readiness** - Final polish and v1.0 release

---

## Phase 12 - Security Hardening (2026-02-17)

### Added

- **Security Headers** - Production-ready HTTP security headers
  - `Content-Security-Policy` with `default-src 'self'`, Tailwind CDN, TMDB images
  - `X-Frame-Options: SAMEORIGIN` - Clickjacking protection
  - `X-Content-Type-Options: nosniff` - MIME sniffing prevention
  - HSTS conditionally enabled only over HTTPS

- **Session Security** - Hardened session cookie configuration
  - `SESSION_COOKIE_SECURE` enabled over HTTPS
  - `SESSION_COOKIE_HTTPONLY=True` - Prevents JS access to session cookie
  - `SESSION_COOKIE_SAMESITE=Lax` - CSRF protection at browser level
  - `REMEMBER_COOKIE_SECURE`, `REMEMBER_COOKIE_HTTPONLY`, `REMEMBER_COOKIE_SAMESITE`
  - `MAX_CONTENT_LENGTH=16MB` - DoS prevention

- **SECRET_KEY Management** - Automatic secure key generation
  - Auto-generates 64-character hex key via `secrets.token_hex(32)`
  - Persists to `instance/.secret_key` with 0600 permissions
  - Rejects weak default `dev_key_change_me` value
  - Environment variable override available (`LISTARR_SECRET_KEY`)

- **Health Endpoint** - Dedicated `/health` for Docker HEALTHCHECK
  - Returns `{"status": "ok"}` without authentication
  - No sensitive information exposed

- **Password Validation** - Minimum 8 character requirement
  - Enforced via `Length(min=8)` validator in auth forms

### Changed

- **Route Protection Audit** - All routes now require authentication
  - Added missing `@login_required` to dashboard routes (`/`, `/api/dashboard/stats`, `/api/dashboard/recent-jobs`)
  - Only exceptions: `/login`, `/setup`, `/health`, static files

- **CSRF Audit** - Removed all `@csrf.exempt` decorators
  - All POST endpoints now require valid CSRF tokens

- **Ignore Files Cleanup** - Cleaner repository structure
  - `.dockerignore` now tracked in git for consistent Docker builds
  - Added `instance/.secret_key` to explicit secrets in `.gitignore`
  - Added missing exclusions to `.dockerignore` (dev files, test configs)
  - Removed unused framework sections from `.gitignore` (Scrapy, Jupyter, Celery, Node.js)
  - Untracked `.planning/` files from git (local development only)

### Security

- **Open Redirect Prevention** - `is_safe_redirect_url()` validates login redirects
- **Generic Login Errors** - "Invalid credentials" prevents username enumeration
- **POST-only Logout** - Prevents CSRF via GET requests
- **Docker Security** - Non-root user with gosu privilege drop
- **No Secrets in Logs** - API keys and passwords never logged

### Technical

- Security review verified all Flask-WTF CSRF, Flask-Login, Fernet encryption implementations
- Error handlers return generic messages without stack traces or internal details
- JavaScript global 401 handler redirects to login on session expiry

---

## Phase 11 - User Authentication (2026-02-14)

### Added

- **Flask-Login Integration** - Session-based authentication with remember me support
  - Login page with username/password form
  - First-run setup wizard for initial account creation
  - Logout functionality with POST-only route
  - 30-day persistent sessions with remember me option

- **User Model Enhancement** - Secure password handling
  - Password hashing using werkzeug.security scrypt
  - `set_password()` and `check_password()` methods
  - `is_authenticated`, `is_active`, `is_anonymous` properties for Flask-Login

- **Auth Routes** (`listarr/routes/auth_routes.py`)
  - `GET/POST /login` - Login page with form validation
  - `GET/POST /setup` - First-run setup wizard (blocked if user exists)
  - `POST /logout` - Logout with redirect to login
  - `@before_app_request` - Auto-redirect to setup if no users exist

- **Route Protection** - Login required on protected pages
  - Config, Settings, Lists, Jobs, Schedule pages require authentication
  - Dashboard remains publicly accessible (read-only stats)
  - AJAX endpoints return 401 for unauthenticated requests

- **Password Management**
  - Password change form on Settings page
  - CLI password reset: `python setup.py --reset-password`
  - Current password verification before allowing change

- **Security Features**
  - Open redirect prevention via `is_safe_redirect_url()` validation
  - CSRF protection on all auth forms
  - Session-based authentication (no JWT tokens)

- **Auth Forms** (`listarr/forms/auth_forms.py`)
  - `LoginForm` - Username, password, remember me checkbox
  - `SetupForm` - Username, password, confirm password with validation

- **Templates**
  - `auth/login.html` - Centered login form with error display
  - `auth/setup.html` - First-run setup wizard

- **43 New Tests** - Comprehensive auth test coverage
  - Login success/failure scenarios
  - Setup wizard flow and blocking
  - Logout functionality
  - Route protection verification
  - Password change validation
  - Open redirect prevention

### Changed

- **Navigation** - Shows Login/Logout based on authentication state
- **Settings Page** - Added password change section for authenticated users
- **Test Fixtures** - Added `authenticated_client` fixture for protected route tests
- **Test Count** - Increased from 493 to 536 tests (+43)

### Technical

- Flask-Login 0.6.3 for session management
- User loader registered in application factory
- Login view configured as `main.login_page`
- Remember cookie duration: 30 days

---

## Phase 10.5 - UI Performance & State Consolidation (2026-02-08)

### Added

- **Skeleton Loading States** - Added animated skeleton loaders to config import settings and dashboard service cards
- **Server-Rendered Status Badges** - Status badges now rendered server-side via `_render_status_badge()` helper
- **Timeout Handling** - Added `API_TIMEOUT_MS` (10 seconds) with `AbortSignal.timeout` to wizard.js and config.js

### Changed

- **formatTimestamp Consolidation** - Consolidated 3 overlapping date functions into unified `formatTimestamp(iso, mode)` with 'relative', 'absolute', 'utc' modes
- **fetchWithTimeout** - Added shared fetch wrapper with timeout support to utils.js
- **schedule.js** - Removed duplicate `updateStatusBadge()` (-36 lines), now uses server-rendered HTML

### Fixed

- **Dashboard Recent Jobs** - Fixed stuck loading state (formatDate → formatTimestamp)
- **Wizard Preview** - Fixed stuck "Loading Preview..." (.results attribute check for native API)
- **Schedule Page** - Fixed formatRelativeTime undefined error
- **Import Service** - Removed dead code branch for .results attribute

---

## Phase 10.4 - Bulk Import API (2026-02-08)

### Added

- **Bulk Import Functions** - Added `bulk_add_movies()` and `bulk_add_series()` for batch operations
- **BULK_TIMEOUT** - 300 second timeout for bulk operations (5 minutes)
- **Batch Accumulation** - Import service now batches items (50 per batch) for bulk API calls
- **17 New Tests** - Comprehensive unit and integration tests for bulk import functionality

### Changed

- **Import Performance** - ~8x faster for 100 items (240s → 31s expected)
- **Duplicate Handling** - Bulk endpoints silently skip duplicates (simpler than per-item error parsing)

### Removed

- Single-item add calls during batch import
- HTTPError duplicate handling (bulk endpoint handles duplicates)

---

## Phase 10.3 - Import & Schedule Bug Fixes (2026-02-08)

### Added

- **Exclusion List Support** - Added `get_exclusions()` to radarr_service and sonarr_service
- **Schedule Edit Modal** - Inline schedule editing on schedule page with preset dropdown
- **7 New Tests** - Tests for exclusion list integration

### Fixed

- **Radarr 400 Bad Request** - Replaced unsafe `movie_data.copy()` with explicit 9-field payload
- **Sonarr Payload** - Replaced `series_data.copy()` with explicit 11-field payload
- **Weekly Cron Preset** - Fixed from "0 0 * * 0" to "0 0 * * SUN"

---

## Phase 10.2 - Schedule Bug Fixes (2026-02-08)

### Added

- **Pre-flight Health Check** - Scheduler validates service reachability before submitting jobs
- **Activity-Based Timeout** - Replaced fixed job timeout with idle detection (5 minutes idle = timeout)
- **ActivityTracker Class** - Thread-safe activity tracking for long-running imports
- **22 New Tests** - Tests for health check, activity tracking, and idle timeout

### Changed

- **Timeout Behavior** - Jobs timeout after 5 minutes of inactivity, not 10 minutes total runtime

---

## Phase 10.1 - UI Review Fixes (2026-02-08)

### Added

- **error_state() Macro** - Standardized error display in macros/ui.html
- **generateServiceBadge()** - Consistent service badges (Radarr=amber, Sonarr=blue) in utils.js
- **Preset Metadata** - PRESET_METADATA constant dict for wizard label/description management

### Changed

- **config.js** - Replaced 4 alert() calls with showToast()
- **Dashboard Upcoming** - Uses generateServiceBadge() for consistent colors
- **Jobs Filter** - Added py-2 for consistent dropdown height
- **Wizard Template** - Reduced from 658 to 616 lines via preset_info variables
- **Lists Badges** - Simplified from 9-line if/else to 4-line compact Jinja pattern

---

## Phase 10 - UI/UX Simplification (2026-02-07/08)

### Added

- **Jinja2 Macro Library** - Created macros/status.html and macros/ui.html with reusable components
- **Global utils.js** - Expanded from 2 to 9 shared functions (escapeHtml, getCsrfToken, formatDate, formatRelativeTime, formatDuration, capitalize, debounce)
- **import_settings_form Macro** - Config form macro reduced config.html from 510 to 270 lines

### Changed

- **dashboard.js** - Parameterized service functions, reduced from 876 to 539 lines (38% reduction)
- **config.js** - Consolidated from 746 to 322 lines (57% reduction)
- **jobs.js/schedule.js/lists.js** - Removed duplicate functions, 107 lines removed total
- **Visibility-Based Polling** - Jobs polling pauses when tab is hidden

### Removed

- Duplicate getCsrfToken, escapeHtml, formatDuration, formatRelativeTime from individual JS files
- Redundant script tags from config.html and settings.html

---

## Phase 9.1 - Config & JS Deduplication (2026-02-06/07)

### Changed

- **config_routes.py** - Refactored from 897 to 404 lines (55% reduction)
- **Parameterized Routes** - 8 duplicate Radarr/Sonarr routes consolidated to 4 using `<service>` URL parameter
- **arr_service.py** - Single source of truth for Radarr/Sonarr operations
- **config.js** - Consolidated from 746 to 322 lines (57% reduction)
- **utils.js** - Created with shared formatTimestamp and generateStatusHTML

### Removed

- 18 service-specific imports replaced with 5 arr_service shared functions
- 12 duplicate JS functions replaced with 6 parameterized versions

---

## Phase 9 - Code Quality & Refactoring (2026-02-05/06)

### Changed

- **format_relative_time()** - Consolidated to utils module
- **Dashboard Stats** - Fixed N+1 query pattern
- **HTTP Status Checks** - Added to all JavaScript fetch calls
- **arr_service.py** - Created shared module for Radarr/Sonarr common code

### Technical

- All 6 plans executed successfully
- 453 tests passing after refactoring

---

## Phase 8 - Architecture & API Consolidation (2026-02-05)

### Changed

- Replaced pyarr library with direct Radarr API calls
- Replaced pyarr library with direct Sonarr API calls
- Replaced tmdbv3api library with direct TMDB API calls
- Consolidated HTTP client with shared session, retry logic, and connection pooling

### Removed

- Removed pyarr dependency (inactive since July 2023)
- Removed tmdbv3api dependency

### Technical

- Created `listarr/services/http_client.py` for shared HTTP session
- All API calls now use `urllib3.Retry` for exponential backoff (retry on 429, 500, 502, 503, 504)
- Consistent 30-second timeout on all external requests
- Connection pooling enabled (10 connections) for better performance
- URL normalization helper (`normalize_url()`) for consistent API endpoint construction

### Documentation

- Created `08-ARCHITECTURE-CONCERNS.md` documenting technical debt for Phase 9 review
- Updated README.md with direct API architecture
- Updated development status to 88% complete

---

## Phase 7 - Scheduler System (2026-02-05)

### Added

- **APScheduler Integration** - Cron-based job scheduling for automated list execution
  - APScheduler 3.11.2 with BackgroundScheduler
  - cronsim 2.7 for next run calculations
  - cron-descriptor 2.0.5 for human-readable cron descriptions
  - Single-worker scheduler pattern (Gunicorn post_fork hook)

- **Scheduler Service** (`listarr/services/scheduler.py`)
  - `schedule_list()` - Register lists with APScheduler using cron expressions
  - `unschedule_list()` - Remove scheduled jobs
  - `pause_scheduler()` / `resume_scheduler()` - Global pause toggle
  - `validate_cron_expression()` - Cron syntax validation
  - `get_next_runs()` - Calculate upcoming execution times
  - Singleton pattern for scheduler instance
  - Loads existing schedules from database on startup

- **Schedule Management Page** (`/schedule`)
  - View all lists with schedule status
  - Status hierarchy: Running > Paused > Scheduled > Manual only
  - Global pause/resume toggle for maintenance
  - Relative time display for next runs ("in 2 hours", "in 3 days")
  - Auto-refresh polling (5-second interval when jobs running)

- **Lists UI Scheduler Integration**
  - Next run subtitle on Lists page with relative times
  - Edit form syncs schedule changes with APScheduler
  - Wizard save registers schedules on list creation
  - Toggle/delete routes update scheduler state
  - Graceful error handling for scheduler operations

- **Dashboard Upcoming Widget**
  - Shows next 5 scheduled jobs with relative times
  - Displays "Paused" badge when scheduler globally paused
  - Integrated polling refresh (2-second interval when jobs running)
  - Two-column layout with Recent Jobs widget

### Changed

- **ServiceConfig Model** - Added `scheduler_paused` boolean column for global pause toggle
- **Gunicorn Configuration** - Added post_fork hook for single-worker scheduler pattern

### Technical

- **Dependencies**:
  - APScheduler 3.11.2 - Cron-based scheduling
  - cronsim 2.7 - Next run calculations
  - cron-descriptor 2.0.5 - Human-readable cron descriptions
- **Scheduler Worker Pattern**: Only one Gunicorn worker runs scheduler (age==1) to prevent duplicate job execution
- **Database Integration**: Schedules stored in List model, loaded on startup
- **Error Handling**: Non-blocking operations allow list management in non-scheduler workers

---

## Phase 6.3 - Test Coverage Enhancement (2025-02-01)

### Added

- **29 new tests** for Phase 6.2 features (415 to 444 tests, +7%)
- **test_tmdb_cache.py** - 15 unit tests for TMDB caching layer
  - Cache hit/miss scenarios
  - Region filtering validation
  - Cache key generation
- **test_import_integration.py** - 7 integration tests for import flows
  - Top Rated import flow testing
- **TEST_SUMMARY.md** - Comprehensive test documentation with full breakdown

### Changed

- **Test coverage improved** from 52% to 56% (+4%)
- **tmdb_cache.py coverage** increased from 14% to 40% (+26%)
- **tmdb_service.py coverage** increased from 71% to 83% (+12%)
- **import_service.py coverage** increased from 9% to 22% (+13%)

---

## Test Suite Updates (2025-01-XX)

### Added - Comprehensive Test Coverage

- **Full Test Suite**: 363 tests covering all application components
- **Dashboard Tests**: 56 tests (38 route + 18 integration)
- **Config Tests**: 170+ tests (140+ route + 30+ integration)
- **Settings Tests**: 85+ tests (50+ route + 35+ integration)
- **Unit Tests**: 145+ tests (services, models, utilities)

### Improved - Test Quality

- **100% Pass Rate**: All 363 tests passing
- **Error Handling**: Comprehensive coverage of all error scenarios
- **Cache Testing**: Tests for dashboard cache initialization and refresh
- **Recent Jobs**: Tests for job querying, formatting, and edge cases
- **Missing Fields**: Tests for graceful handling of missing data fields

### Fixed - Test Issues

- **Decryption Error Handling**: Added proper error handling in config endpoints (4 tests)
- **Missing Fields**: Fixed missing `hasFile` field handling in missing movies count (1 test)
- **HTML Content**: Updated test expectations to match actual HTML
- **Recent Jobs Query**: Fixed to use outerjoin for inclusive querying
- **Cache Initialization**: Added graceful handling for missing database tables

### Documentation

- Added `TEST_STATUS.md` - Current test suite status
- Added `DASHBOARD_FEATURES.md` - Comprehensive dashboard documentation
- Updated `TEST_SUMMARY.md` - Updated test statistics
- Updated `tests/README.md` - Added dashboard test coverage
- Updated `FULL_TEST_RESULTS_VALIDATION.md` - Complete test validation

---

## Dashboard Enhancements (2025-01-XX)

### Added - Dashboard Features

- **"Added by Listarr" Counter**
  - Displays total items added by Listarr from completed jobs
  - Separate counters for Radarr and Sonarr
  - Calculated from `Job.items_added` field for completed jobs only
  - Updates automatically on cache refresh

- **In-Memory Caching System**
  - Dashboard statistics cached at application startup
  - Fast page loads without API calls on every request
  - Thread-safe cache updates with `threading.Lock`
  - On-demand refresh via `?refresh=true` query parameter
  - Graceful handling of missing database tables during initialization

- **Recent Jobs Display**
  - Shows last 5 executed jobs with formatted dates
  - Relative time formatting ("2 hours ago", "3 days ago")
  - Status-based color coding (completed/failed/running/pending)
  - Conditional summary formatting (only shows non-zero values)
  - Handles jobs without associated lists gracefully

- **Enhanced Error Handling**
  - Graceful degradation when services are offline
  - Defensive checks for missing data fields
  - Proper error states displayed in UI
  - Database error handling for cache initialization

### Improved

- **Performance**: Dashboard loads instantly using cached data
- **User Experience**: Manual refresh button with loading states
- **Auto-Refresh**: 5-minute interval with page visibility optimization
- **Error Recovery**: Better handling of decryption errors in config endpoints
- **Data Integrity**: Missing field handling in missing movies count

### Technical

- **Dashboard Cache Service** (`listarr/services/dashboard_cache.py`)
  - Centralized caching logic for dashboard statistics
  - Calculates stats at startup and on-demand
  - Thread-safe operations with locking mechanism
  - Handles missing database tables gracefully

- **Recent Jobs Query Optimization**
  - Uses `outerjoin` to include jobs without lists
  - Filters for finished jobs only (`finished_at.isnot(None)`)
  - Improved fallback logic for missing list data

### Fixed

- **Test Suite Updates** (363 tests total, 100% passing)
  - Updated dashboard tests to reflect cache-based implementation
  - Fixed HTML content test expectations
  - Fixed recent jobs query to handle missing lists
  - Fixed cache initialization error handling
  - Fixed decryption error handling in config endpoints (4 tests)
  - Fixed missing fields handling in missing movies count (1 test)

### Documentation

- Added `TEST_UPDATE_SUMMARY.md` - Dashboard test updates
- Added `TEST_RESULTS_ANALYSIS.md` - Test failure analysis
- Added `TEST_FIXES_SUMMARY.md` - Summary of test fixes
- Added `FULL_TEST_RESULTS_VALIDATION.md` - Complete test validation
- Updated `tests/README.md` - Added dashboard test coverage
- Updated `tests/TEST_SUMMARY.md` - Updated test statistics

---

## Test Suite Improvements (2025-01-09)

### Added - Comprehensive Test Coverage

- **Config Routes Test Suite Enhancement** - Expanded from 65+ to 84+ tests
  - Added decryption error handling tests for quality profiles and root folders endpoints (4 tests)
  - Added database error handling tests for helper functions (2 tests)
  - Added missing field validation tests for import settings (3 tests)
  - Added API failure handling tests for root folders endpoints (2 tests)
  - Added URL validation edge cases with parameterized tests (9 scenarios)
  - Added concurrent operations test (saving both services in one POST)
  - Added type validation tests for import settings
  - Added missing Sonarr import settings tests to match Radarr coverage (3 tests)

### Improved - Test Quality

- **Error Handling Coverage** - Comprehensive tests for all error scenarios

  - Decryption failures in API endpoints
  - Database commit failures in helper functions
  - API service failures and empty responses
  - Missing required field validation
  - Invalid data type handling

- **Test Organization** - Better structured test classes
  - New `TestConcurrentOperations` class for concurrent operation tests
  - Parameterized tests for URL validation edge cases
  - Consistent test patterns across all test classes

### Technical - Test Metrics

- **Test Count**: Increased from 65+ to 84+ tests (+19 new tests)
- **Coverage**: Improved from ~85% to ~95%
- **File Size**: `test_config_routes.py` now ~1500+ lines (comprehensive coverage)

### Documentation

- Added `CONFIG_ROUTES_TEST_REVIEW.md` - Comprehensive test review and recommendations
- Added `CONFIG_ROUTES_TEST_IMPLEMENTATION.md` - Implementation summary of test improvements
- Updated `TEST_REVIEW.md` - Reflects completed test improvements

---

## Phase 2 - Dashboard & Stats (Complete)

### Added - Dashboard Implementation

- **Dashboard page** (`/`) with live stats from Radarr/Sonarr

  - Service status indicators (online/offline/not_configured)
  - Total movies/series counts
  - Missing movies/episodes counts
  - **"Added by Listarr"** counter (sum of items_added from completed jobs)
  - Manual refresh button with loading state
  - Auto-refresh functionality (5-minute interval)
  - Recent jobs table showing last 5 executed jobs with formatted dates and status colors

- **Dashboard API endpoints**

  - `GET /api/dashboard/stats` - Cached stats from all configured services
  - `GET /api/dashboard/stats?refresh=true` - Force cache refresh
  - `GET /api/dashboard/recent-jobs` - Recent job execution history

- **Dashboard caching system** (`listarr/services/dashboard_cache.py`)
  - In-memory cache for dashboard statistics
  - Calculated at application startup for fast page loads
  - Thread-safe cache updates with locking
  - On-demand refresh via query parameter
  - Graceful handling of missing database tables

- **Service functions for dashboard data**
  - `get_system_status()` - System version and status for Radarr/Sonarr
  - `get_movie_count()` - Total movie count from Radarr
  - `get_series_count()` - Total series count from Sonarr
  - `get_missing_movies_count()` - Missing movie count
  - `get_missing_episodes_count()` - Missing episodes count (uses `get_wanted()` totalRecords)

### Improved

- **Performance**: In-memory caching eliminates API calls on every page load
- **Error handling**: Graceful degradation with defensive checks for missing data
- **Recent jobs**: Conditional summary formatting (only shows non-zero values)
- **Database queries**: Uses outerjoin to include jobs without associated lists
- HTML escaping for security in dashboard UI

### Technical

- Dashboard routes implemented in `dashboard_routes.py`
- Dashboard JavaScript in `dashboard.js` with auto-refresh logic
- Dashboard template in `dashboard.html` with responsive card layout

---

## Phase 1 - Config & API Integration (Complete)

### Added - Core Application

- **Flask application factory** pattern with SQLAlchemy ORM
- **Fernet encryption system** for API keys with dynamic instance path resolution
- **Database models** for all core entities:

  - `ServiceConfig` - Stores encrypted API keys and connection details
  - `MediaImportSettings` - Default import settings per service
  - `List` - TMDB list definitions with filters and scheduling
  - `Job` & `JobItem` - Job execution tracking
  - `Tag` - Tags for organizing media
  - `User` - User accounts (authentication not yet implemented)

- **Blueprint-based routing** structure
- **Setup script** (`setup.py`) for first-time initialization
- **Docker configuration** with production-ready containerization

### Added - Settings Page (`/settings`)

- TMDB API key management
- AJAX test connection functionality with CSRF protection
- Last test timestamp tracking (displays success/failure status and time)
- Field preservation during test operations
- Helper function `_test_and_update_tmdb_status()` for reusable test logic
- Proper error handling with database rollback on failures

### Added - Config Page (`/config`)

- **Radarr/Sonarr API key management**

  - URL and API key configuration for both services
  - URL validation before saving or testing connections
  - AJAX test connection endpoints (`/config/test_radarr_api`, `/config/test_sonarr_api`)
  - Helper functions: `_test_and_update_radarr_status()`, `_test_and_update_sonarr_status()`
  - Conditional display of Import Settings (hidden until service configured)
  - Last test timestamp tracking per service
  - API key toggle visibility (eye icon)

- **Import Settings** (fully functional)

  - Dynamic dropdowns populated from Radarr/Sonarr APIs
  - Root Folder and Quality Profile fetched in real-time
  - Monitor, Search on Add, Season Folder (Sonarr only) dropdowns
  - Tags field (placeholder, not yet functional)
  - Save/load functionality with database persistence
  - Client-side and server-side validation
  - Flag-based data caching to prevent redundant API calls

- **Import Settings API endpoints**
  - `GET /config/radarr/quality-profiles` - Fetch Radarr quality profiles
  - `GET /config/radarr/root-folders` - Fetch Radarr root folders
  - `GET /config/radarr/import-settings` - Retrieve saved Radarr settings
  - `POST /config/radarr/import-settings` - Save Radarr import settings
  - `GET /config/sonarr/quality-profiles` - Fetch Sonarr quality profiles
  - `GET /config/sonarr/root-folders` - Fetch Sonarr root folders
  - `GET /config/sonarr/import-settings` - Retrieve saved Sonarr settings
  - `POST /config/sonarr/import-settings` - Save Sonarr import settings

### Added - Service Integration

- **TMDB Service** (`tmdb_service.py`) - Complete tmdbv3api integration

  - `test_tmdb_api_key()` - Tests TMDB API key
  - `get_imdb_id_from_tmdb()` - Retrieves IMDB IDs from TMDB (legal, no web scraping)
  - `get_trending_movies()`, `get_trending_tv()` - Fetches trending content (day/week)
  - `get_popular_movies()`, `get_popular_tv()` - Fetches popular content
  - `discover_movies()`, `discover_tv()` - Advanced discovery with filters (genre, year, rating, language)
  - `get_movie_details()`, `get_tv_details()` - Detailed information retrieval

- **Radarr Service** (`radarr_service.py`) - Complete PyArr integration

  - `test_radarr_api_key()` - Uses PyArr for system status check
  - `get_quality_profiles()` - Fetches quality profiles via PyArr
  - `get_root_folders()` - Fetches root folders via PyArr
  - `get_system_status()` - System version and status
  - `get_movie_count()` - Total movie count
  - `get_missing_movies_count()` - Missing movie count

- **Sonarr Service** (`sonarr_service.py`) - Complete PyArr integration
  - `test_sonarr_api_key()` - Uses PyArr for system status check
  - `get_quality_profiles()` - Fetches quality profiles via PyArr
  - `get_root_folders()` - Fetches root folders via PyArr
  - `get_system_status()` - System version and status
  - `get_series_count()` - Total series count
  - `get_missing_series_count()` - Missing series count

### Added - Security Features

- **CSRF protection** on all forms and AJAX requests
  - CSRF meta tag in base.html for JavaScript access
  - All AJAX requests include X-CSRFToken header
  - All form submissions include CSRF token via `{{ form.hidden_tag() }}`
- **API key encryption** at rest using Fernet symmetric encryption
- **Field validation** on both frontend and backend
- **URL validation** for Radarr/Sonarr base URLs using `urllib.parse.urlparse`

### Added - Dependencies

- **PyArr** (`>=5.0.0`) - Radarr/Sonarr API client classes
- **tmdbv3api** (`1.9.0`) - TMDB API client
- **cryptography** (`41.0.7`) - Fernet encryption for API keys
- **Flask-WTF** - CSRF protection and forms
- **gunicorn** (`21.2.0`) - Production WSGI server for Docker deployment

### Improved - Code Quality

- **Error Handling & Database Management**

  - Database session management with proper rollback on all database operations
  - Try/except blocks with `db.session.rollback()` prevent partial commits
  - Comprehensive error logging with full exception traces
  - User-friendly error messages via flash messages

- **Logging Improvements**

  - Replaced all `print()` statements with proper Python `logging` module
  - Service layer uses module-level loggers (`logger = logging.getLogger(__name__)`)
  - Route handlers use Flask's `current_app.logger`
  - Error logging includes `exc_info=True` for full exception traces
  - Basic logging configuration in application factory

- **Input Validation**

  - URL validation for Radarr/Sonarr base URLs
  - `_is_valid_url()` helper function using `urllib.parse.urlparse`
  - Validation in both form submissions and AJAX endpoints
  - Clear error messages for invalid URLs

- **Development Configuration**
  - Debug mode controlled via `FLASK_DEBUG` environment variable
  - Defaults to `False` for safety (no hardcoded `debug=True`)
  - Can be enabled with `FLASK_DEBUG=true python run.py`

### Technical - Database

- **Timezone-aware DateTime columns** - All DateTime columns use `TZDateTime` custom type
  - Ensures timezone information is preserved when storing and retrieving datetime objects
  - Models updated: ServiceConfig, List, Job, Tag, User
  - Custom type implementation in `custom_types.py`

### Technical - Architecture

- **Application Factory Pattern** - Flask app created via `create_app()` function
- **Instance folder** at project root for runtime data (database, encryption key)
- **Blueprint-based routing** - All routes registered under single blueprint
- **Services layer** - Business logic separated from routes

### UX Improvements

- "Select X" placeholders for all dropdowns (better UX)
- Client-side validation before save (alerts for missing selections)
- Server-side validation (400 errors with descriptive messages)
- Loading states ("Loading...", "Select X" placeholders)
- Disabled inputs during operations
- Season Folder field for Sonarr (TV-specific setting)

---

## Design Decisions

### IMDB Integration Strategy

- **Decision**: Use TMDB as the sole data source with legal IMDB ID mapping
- **Rationale**:
  - IMDB does not provide a public API
  - Web scraping IMDB violates Terms of Service
  - TMDB provides official IMDB ID mapping via `external_ids` endpoint
- **Implementation**: IMDB IDs retrieved via TMDB's `external_ids` endpoint
- **Rejected Alternatives**:
  - ❌ `cinemagoer` - Web scraping, violates IMDB TOS
  - ❌ OMDb API - Paid service, unnecessary for use case
  - ❌ Direct IMDB API - Does not exist publicly

### Caching Strategy

- **Decision**: Simple flag-based caching for Import Settings
- **Rationale**:
  - Single-user, self-hosted application
  - Config page accessed infrequently
  - Simple solution sufficient for use case
- **Implementation**: Boolean flags (`radarrDataLoaded`, `sonarrDataLoaded`) prevent redundant API calls
- **Rejected**: TTL-based caching, request debouncing, exponential backoff (over-engineered for homelab use)

### Project Philosophy

- **Read-only + Push Actions**: View stats from Radarr/Sonarr, generate lists from TMDB, push imports to media servers
- **No full media management**: View-only dashboard, no edit/delete of existing media
- **Single-user design**: No multi-user support, roles, or permissions
- **Self-hosted homelab utility**: Not designed for open internet exposure

---

## Technology Stack

### Backend

- **Flask 3.0.0** - Web framework
- **SQLAlchemy 2.0.44** - ORM and database management
- **Flask-WTF** - CSRF protection and forms
- **cryptography 44.0.1** - Fernet encryption for API keys
- **requests 2.32.4** - Direct HTTP client for all external APIs
- **APScheduler 3.11.2** - Cron-based job scheduling
- **gunicorn 22.0.0** - Production WSGI server

### Frontend

- **Tailwind CSS** - Utility-first styling
- **Vanilla JavaScript** - Dynamic UI interactions with shared utils.js
- **Jinja2** - Server-side templating with macro library

### Database

- **SQLite** - Embedded database with WAL mode

---

## Development Status

**Current Completion: ~98%** (12 of 13 main phases complete, plus 8 sub-phases)

### Completed Phases
- ✅ **Phase 1**: List Management System - CRUD operations for TMDB lists
- ✅ **Phase 2**: List Creation Wizard - Multi-step wizard with presets and live preview
- ✅ **Phase 3**: TMDB Caching Layer - Smart caching to respect rate limits
- ✅ **Phase 3.1**: Config Page Tags - Tag storage with create-if-missing pattern
- ✅ **Phase 4**: Import Automation Engine - Radarr/Sonarr import with error handling
- ✅ **Phase 5**: Manual Trigger UI - Run lists on-demand from UI
- ✅ **Phase 6**: Job Execution Framework - Background processing with history
- ✅ **Phase 6.1**: Bug Fixes - Tag override, logging, UI feedback
- ✅ **Phase 6.2**: List Enhancements - Top Rated, region filtering, larger limits
- ✅ **Phase 6.3**: Test Coverage - 444 → 493 tests
- ✅ **Phase 7**: Scheduler System - Cron-based automated list execution
- ✅ **Phase 8**: Architecture & API Consolidation - Direct HTTP calls, removed pyarr/tmdbv3api
- ✅ **Phase 9**: Code Quality & Refactoring - Consolidated duplicate code
- ✅ **Phase 9.1**: Config & JS Deduplication - 55% route reduction, 57% JS reduction
- ✅ **Phase 10**: UI/UX Simplification - Jinja macros, JS consolidation
- ✅ **Phase 10.1**: UI Review Fixes - Alert→toast, consistent badges
- ✅ **Phase 10.2**: Schedule Bug Fixes - Health checks, activity-based timeout
- ✅ **Phase 10.3**: Import & Schedule Bug Fixes - Exclusion lists, schedule edit modal
- ✅ **Phase 10.4**: Bulk Import API - 8x faster imports
- ✅ **Phase 10.5**: UI Performance & State - Skeleton loading, timeout handling
- ✅ **Phase 11**: User Authentication - Login, setup wizard, password management (536 tests)
- ✅ **Phase 12**: Security Hardening - Security headers, session security, route protection audit

### Planned Phases
- 🔮 **Phase 13**: Release Readiness - Final polish and v1.0 release

---

## Notes

- All API keys are encrypted at rest using Fernet symmetric encryption
- CSRF protection enabled on all forms and AJAX requests
- Debug mode is disabled by default for safety
- Instance folder contains runtime data (database, encryption key)
- Docker-first deployment with persistent volume support
- Comprehensive documentation in `CLAUDE.md`
- Test suite: 536 tests
- Direct HTTP API calls (no third-party wrappers)
- Bulk import API for 8x faster list execution
- User authentication with Flask-Login

---

**Last Updated:** 2026-02-17
