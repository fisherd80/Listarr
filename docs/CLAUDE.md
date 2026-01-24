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

### Setup and Initialization

```bash
# First-time setup: Generate encryption key and create database
python setup.py

# Run development server
python run.py
```

The setup script creates:

- Fernet encryption key at `instance/.fernet_key`
- SQLite database at `instance/listarr.db`

### Running the Application

```bash
# Development mode (debug mode controlled by FLASK_DEBUG environment variable)
python run.py

# Enable debug mode explicitly
FLASK_DEBUG=true python run.py
```

The app runs on `http://localhost:5000` by default (Docker-ready, no reverse proxy required).

**Note**: Debug mode is disabled by default for safety. Set `FLASK_DEBUG=true` to enable debug mode during development.

## Design Principles & Scope

### Purpose & Deployment

- **Single-user application** - no multi-user support, roles, or permissions
- **Self-hosted homelab utility** - not designed for open internet exposure
- **Optional HTTP Basic Auth** for local credential protection
- **Docker-first** with persistent volume support (container rebuild must not lose data)

### Core Behavior Model

1. **Dashboard**: Read-only summary with stats from Radarr/Sonarr (live refresh, manual refresh button)
2. **List Generation**: Stepper/wizard UI for discovering and previewing TMDB content
3. **Import**: Queue-based push to Radarr/Sonarr (no immediate add, no dry-run)
4. **Jobs**: Central activity monitoring (the primary observability interface)
5. **Scheduling**: Per-list cron automation

### List Architecture (Critical)

**Two List Types**:

1. **LIVE Lists**

   - TMDB API called on every execution
   - No items stored in DB
   - Subject to rate limits
   - Use for real-time queries

2. **CACHED Lists**
   - TMDB results cached with TTL
   - Items stored in DB (sanitized + Radarr/Sonarr-mapped fields only)
   - Refresh interval defined per-list
   - Cron-friendly
   - **Cache expiry handling**: If expired during execution, hard block → refresh first → then import

**List Configuration** (always saved regardless of type):

- Target service (Radarr or Sonarr)
- TMDB source type (Trending, Popular, Custom)
- Filters (genre, year, language, etc.)
- Limits
- Refresh strategy (for cached lists)
- Schedule (cron expression)
- Enabled/disabled state

### Import Logic

**Global Import Settings** (configured on Config page, no per-list overrides):

- Quality profile
- Root folder
- Monitoring toggle
- Settings pulled dynamically from Radarr/Sonarr APIs

**Conflict Handling**:

- Already exists → skip
- Mixed content (movies + TV) → blocked
- Movies only → Radarr
- TV only → Sonarr

**Queue-based execution**:

- No immediate add
- No dry-run mode
- Jobs track all import activity

### IMDB Integration Strategy

**Decision**: Use TMDB as the sole data source for list generation, with IMDB ID mapping for reference.

**Rationale**:

- IMDB does not provide a public API
- Web scraping IMDB (via cinemagoer/IMDbPY) violates IMDB Terms of Service
- Legal and compliance risks for production deployment
- TMDB provides official IMDB ID mapping via `external_ids` endpoint

**Implementation**:

- **Primary Source**: TMDB API for all list generation (trending, popular, discover)
- **IMDB IDs**: Retrieved via TMDB's `external_ids` endpoint
  - Function: `get_imdb_id_from_tmdb(tmdb_id, api_key, media_type='movie')`
  - Returns IMDB ID format: `tt1234567`
- **UI Display**: IMDB links shown to users for reference (e.g., "View on IMDB")
- **No IMDB Scraping**: cinemagoer library explicitly NOT used

**Benefits**:

- Legal compliance (no TOS violations)
- Fast and reliable (single API call)
- Official data from TMDB
- No additional API keys required
- Maintains single source of truth (TMDB)

**Rejected Alternatives**:

- ❌ `cinemagoer` (2023.5.1): Web scraping, violates IMDB TOS
- ❌ OMDb API: Paid service ($10-300/month), unnecessary for use case
- ❌ Direct IMDB API: Does not exist publicly

### Security Design

- **API keys encrypted at rest** (Fernet symmetric encryption)
- **API keys masked in UI** (toggle eye icon to reveal)
- **CSRF protection enabled** (Flask-WTF)
  - CSRF meta tag in base.html: `<meta name="csrf-token" content="{{ csrf_token() }}" />`
  - All form submissions include CSRF token via `{{ form.hidden_tag() }}`
  - All AJAX requests include `X-CSRFToken` header from meta tag
  - JavaScript helper: `document.querySelector('meta[name="csrf-token"]').getAttribute('content')`
- **Proper encryption key handling** with instance_path parameter
- **Logs sanitized** (no secrets, API keys, or tokens)
- **No debug UI in production**
- **Optional Basic Auth** for local network access protection

## Current Implementation Status

### ✅ Recent Code Quality Improvements (Latest)

**Error Handling & Database Management**:

- ✅ Database session management with proper rollback on all database operations
- ✅ Try/except blocks with `db.session.rollback()` prevent partial commits
- ✅ Comprehensive error logging with full exception traces
- ✅ User-friendly error messages via flash messages

**Logging Improvements**:

- ✅ Replaced all `print()` statements with proper Python `logging` module
- ✅ Service layer uses module-level loggers (`logger = logging.getLogger(__name__)`)
- ✅ Route handlers use Flask's `current_app.logger`
- ✅ Error logging includes `exc_info=True` for full exception traces
- ✅ Basic logging configuration in application factory

**Input Validation**:

- ✅ URL validation for Radarr/Sonarr base URLs
- ✅ `_is_valid_url()` helper function using `urllib.parse.urlparse`
- ✅ Validation in both form submissions and AJAX endpoints
- ✅ Clear error messages for invalid URLs

**Development Configuration**:

- ✅ Debug mode controlled via `FLASK_DEBUG` environment variable
- ✅ Defaults to `False` for safety (no hardcoded `debug=True`)
- ✅ Can be enabled with `FLASK_DEBUG=true python run.py`

### ✅ Implemented (Phase 1 Complete)

- Flask application factory pattern (`listarr/__init__.py`)
- Fernet encryption system (`listarr/services/crypto_utils.py`) with dynamic instance path resolution
- Database models for core entities (`listarr/models/`)
- **Settings page** with TMDB API key management (`/settings`, `/settings/test_tmdb_api`)
  - API key encryption/decryption with instance_path parameter
  - AJAX test connection functionality with CSRF protection
  - Last test timestamp tracking (displays success/failure status and time)
  - Field preservation during test operations
  - Helper function `_test_and_update_tmdb_status()` for reusable test logic
  - **Proper error handling** with database rollback on failures
- **Config page** with Radarr/Sonarr API key management (`/config`) ✅
  - URL and API key configuration for both services
  - **URL validation** - Validates URL format before saving or testing connections
  - AJAX test connection endpoints (`/config/test_radarr_api`, `/config/test_sonarr_api`)
  - Helper functions: `_test_and_update_radarr_status()`, `_test_and_update_sonarr_status()`
  - Conditional display of Import Settings (hidden until service configured)
  - Last test timestamp tracking per service
  - CSRF token protection on all AJAX requests
  - API key toggle visibility (eye icon)
  - **Proper error handling** with database rollback on failures
  - **FULLY FUNCTIONAL Import Settings** ✅
    - Dynamic dropdowns populated from Radarr/Sonarr APIs
    - Root Folder and Quality Profile fetched in real-time
    - Monitor, Search on Add, Season Folder (Sonarr only) dropdowns
    - Tags field (placeholder, not yet functional)
    - Save/load functionality with database persistence
    - Client-side and server-side validation
    - Flag-based data caching to prevent redundant API calls
- **Service integration** (`listarr/services/`) ✅
  - `tmdb_service.py` - **COMPLETE tmdbv3api integration**:
    - `test_tmdb_api_key()` - Tests TMDB API key
    - `get_imdb_id_from_tmdb()` - Retrieves IMDB IDs from TMDB
    - `get_trending_movies()`, `get_trending_tv()` - Fetches trending content
    - `get_popular_movies()`, `get_popular_tv()` - Fetches popular content
    - `discover_movies()`, `discover_tv()` - Advanced discovery with filters
    - `get_movie_details()`, `get_tv_details()` - Detailed information retrieval
  - `radarr_service.py` - **COMPLETE PyArr integration**:
    - `test_radarr_api_key()` - Uses PyArr for system status check
    - `get_quality_profiles()` - Fetches quality profiles via PyArr
    - `get_root_folders()` - Fetches root folders via PyArr
  - `sonarr_service.py` - **COMPLETE PyArr integration**:
    - `test_sonarr_api_key()` - Uses PyArr for system status check
    - `get_quality_profiles()` - Fetches quality profiles via PyArr
    - `get_root_folders()` - Fetches root folders via PyArr
- **PyArr library** ✅ - Fully integrated in `requirements.txt` and used throughout
- **tmdbv3api library** ✅ - Fully integrated for TMDB API access
- **IMDB Integration Strategy** ✅ - Uses TMDB's external_ids for legal IMDB ID mapping (no web scraping)
- **Security features**
  - CSRF meta tag in base.html for JavaScript access
  - All AJAX requests include X-CSRFToken header
  - Encrypted API keys with proper instance_path handling
  - Field validation on both frontend and backend
- Blueprint-based routing structure
- Setup script for initialization
- Consolidated instance folder at project root

### ✅ Implemented (Phase 2 Complete)

- **Dashboard** with cached stats from Radarr/Sonarr ✅
  - `GET /api/dashboard/stats` - Cached stats endpoint (fast page loads)
  - `GET /api/dashboard/stats?refresh=true` - Force cache refresh
  - `GET /api/dashboard/recent-jobs` - Recent jobs endpoint
  - In-memory caching system for performance
  - "Added by Listarr" counter (sum of items_added from completed jobs)
  - Manual and auto-refresh functionality (5-minute interval)
  - Service status indicators (online/offline/not_configured)
  - Total movies/series counts
  - Missing movies/series counts
  - Manual refresh button
  - Auto-refresh (5-minute interval)
  - Recent jobs table (last 5 executed jobs)
  - Parallel API execution with ThreadPoolExecutor
  - Comprehensive error handling and graceful degradation
- **Radarr/Sonarr dashboard service functions** ✅
- **Dashboard caching system** (`dashboard_cache.py`) ✅
  - In-memory cache with thread-safe locking
  - Startup initialization for fast page loads
  - On-demand refresh capability
  - `get_system_status()` - System version and status
  - `get_movie_count()` / `get_series_count()` - Total media counts
  - `get_missing_movies_count()` / `get_missing_series_count()` - Missing media counts
  - All functions include proper error handling and logging

### ⚠️ Not Yet Implemented (Phase 3+)

- **Radarr/Sonarr advanced API integration**:
  - Tags fetching (`/api/v3/tag`)
  - Movie/series addition functionality (`add_movie()`, `add_series()`)
- Job execution engine (background task runner)
- Scheduling system (cron jobs)
- Cache management for cached lists (with TTL)
- Import queue logic
- List generation wizard UI (route stub exists)
- Jobs page UI (route stub exists)
- Global blacklist system
- Tag functionality for import settings

## Architecture

### Application Factory Pattern

The app uses Flask's application factory pattern with `create_app()` in `listarr/__init__.py`:

- Initializes SQLAlchemy with `db` instance
- Configures logging with Python's `logging` module
- Loads encryption key (will fail if key is missing)
- Registers the main blueprint from `listarr/routes`
- Uses instance folder for database and encryption key

### Data Storage Strategy

| Purpose          | Storage                              |
| ---------------- | ------------------------------------ |
| App config       | YAML / JSON (planned)                |
| Credentials      | Encrypted file-based secret (Fernet) |
| Application data | SQLite                               |
| Logs             | Plain text files (planned)           |

### Data Encryption

All sensitive data (API keys) are encrypted using Fernet symmetric encryption:

- **Key Management**: `listarr/services/crypto_utils.py`
  - Key stored in `instance/.fernet_key` (at project root) or `FERNET_KEY` environment variable
  - Uses Flask's `app.instance_path` for dynamic path resolution
  - Helper function `_get_key_path(instance_path)` handles path construction
  - Functions: `encrypt_data()`, `decrypt_data()`, `load_encryption_key()`, `generate_key()`
  - All crypto functions accept optional `instance_path` parameter for explicit path control
  - Key must exist before app starts (created by `setup.py`)

### Database Models

Located in `listarr/models/`, all inherit from `db.Model`:

- **ServiceConfig** (`service_config_model.py`): Stores encrypted API keys and connection details for external services (TMDB, Radarr, Sonarr)
  - Tracks connection test status with `last_tested_at` (DateTime) and `last_test_status` (String: "success"/"failed")
- **MediaImportSettings** (`service_config_model.py`): Default import settings (root folder, quality profile, tags) per service
- **List** (`lists_model.py`): Defines TMDB lists to sync, with filters, overrides, caching, and scheduling
  - Contains: target_service, tmdb_list_type, filters_json, cache settings, schedule_cron
  - **Cache fields**: cache_enabled, cache_ttl_hours, last_tmdb_fetch_at, cache_valid_until
  - Override fields for import settings (optional per-list overrides)
- **Job** & **JobItem** (`jobs_model.py`): Tracks sync job execution with status, metrics, and individual item results
  - Job status: pending/running/failed/completed
  - Metrics: items_found, items_added, items_skipped
  - JobItem tracks per-item status (added/skipped/failed)
- **Tag** (`tag_model.py`): Tags for organizing media
- **User** (`user_model.py`): User accounts (authentication not yet implemented)

All models are imported via `listarr/models/__init__.py`.

### Routing Structure

All routes are registered under a single blueprint `bp` in `listarr/routes/__init__.py`:

- `dashboard_routes.py`: Home page (`/`) - read-only stats cards ✅ **COMPLETE**
  - `GET /` - Dashboard page template
  - `GET /api/dashboard/stats` - Cached stats from Radarr/Sonarr (with refresh parameter)
  - `GET /api/dashboard/recent-jobs` - Recent job execution history
- `dashboard_cache.py`: In-memory caching service ✅ **COMPLETE**
  - Startup cache initialization
  - Thread-safe cache updates
  - On-demand cache refresh
  - "Added by Listarr" calculation from completed jobs
- `lists_routes.py`: List management (`/lists`) - wizard UI for list creation (not yet implemented)
- `jobs_routes.py`: Job monitoring (`/jobs`) - central activity view (not yet implemented)
- `config_routes.py`: Service configuration (`/config`) - Radarr/Sonarr setup ✅ **COMPLETE**
  - POST handlers for `save_radarr_api` and `save_sonarr_api`
  - AJAX endpoints: `/config/test_radarr_api`, `/config/test_sonarr_api`
  - **Radarr Import Settings routes** ✅:
    - `GET /config/radarr/quality-profiles` - Fetch quality profiles
    - `GET /config/radarr/root-folders` - Fetch root folders
    - `GET /config/radarr/import-settings` - Retrieve saved settings
    - `POST /config/radarr/import-settings` - Save import settings
  - **Sonarr Import Settings routes** ✅:
    - `GET /config/sonarr/quality-profiles` - Fetch quality profiles
    - `GET /config/sonarr/root-folders` - Fetch root folders
    - `GET /config/sonarr/import-settings` - Retrieve saved settings
    - `POST /config/sonarr/import-settings` - Save import settings
  - Helper functions for reusable test logic
  - Conditional rendering based on `radarr_configured` and `sonarr_configured` flags
- `settings_routes.py`: TMDB API settings ✅
  - `/settings` - GET/POST for API key management
  - `/settings/test_tmdb_api` - AJAX endpoint for testing TMDB connection

Routes use Flask templates from `listarr/templates/` with a shared `base.html`.

- **base.html** includes CSRF meta tag: `<meta name="csrf-token" content="{{ csrf_token() }}" />`

### Services Layer

Business logic in `listarr/services/`:

- **crypto_utils.py** ✅ COMPLETE: Encryption/decryption utilities for API keys
  - `encrypt_data(data, instance_path)` - Encrypts sensitive data
  - `decrypt_data(encrypted_data, instance_path)` - Decrypts sensitive data
  - `load_encryption_key(instance_path)` - Loads Fernet key from file or env
  - `generate_key()` - Generates new Fernet key
- **tmdb_service.py** ✅ COMPLETE: TMDB API integration using tmdbv3api library
  - ✅ `test_tmdb_api_key(api_key)` - Tests TMDB API key
  - ✅ `get_imdb_id_from_tmdb(tmdb_id, api_key, media_type)` - Retrieves IMDB ID for TMDB movie/TV show
  - ✅ `get_trending_movies(api_key, time_window, page)` - Fetches trending movies (day/week)
  - ✅ `get_trending_tv(api_key, time_window, page)` - Fetches trending TV shows (day/week)
  - ✅ `get_popular_movies(api_key, page)` - Fetches popular movies
  - ✅ `get_popular_tv(api_key, page)` - Fetches popular TV shows
  - ✅ `discover_movies(api_key, filters, page)` - Discovers movies with filters (genre, year, rating, etc.)
  - ✅ `discover_tv(api_key, filters, page)` - Discovers TV shows with filters
  - ✅ `get_movie_details(tmdb_id, api_key)` - Fetches detailed movie information
  - ✅ `get_tv_details(tmdb_id, api_key)` - Fetches detailed TV show information
  - ✅ **Proper logging** - Uses Python's `logging` module instead of `print()` statements
- **radarr_service.py** ✅ COMPLETE PyArr integration:
  - ✅ `test_radarr_api_key(base_url, api_key)` - Uses PyArr `RadarrAPI` for system status check
  - ✅ `get_quality_profiles(base_url, api_key)` - Fetches quality profiles via PyArr
  - ✅ `get_root_folders(base_url, api_key)` - Fetches root folders via PyArr
  - ✅ **Proper logging** - Uses Python's `logging` module instead of `print()` statements
  - ✅ `get_system_status()` - System status and version info
  - ✅ `get_movie_count()` - Total movie count
  - ✅ `get_missing_movies_count()` - Missing movie count
  - ⚠️ Needs: `get_tags()`, `add_movie()`
- **sonarr_service.py** ✅ COMPLETE PyArr integration:
  - ✅ `test_sonarr_api_key(base_url, api_key)` - Uses PyArr `SonarrAPI` for system status check
  - ✅ `get_quality_profiles(base_url, api_key)` - Fetches quality profiles via PyArr
  - ✅ `get_root_folders(base_url, api_key)` - Fetches root folders via PyArr
  - ✅ **Proper logging** - Uses Python's `logging` module instead of `print()` statements
  - ✅ `get_system_status()` - System status and version info
  - ✅ `get_series_count()` - Total series count
  - ✅ `get_missing_series_count()` - Missing series count
  - ⚠️ Needs: `get_tags()`, `add_series()`
- **job_runner.py** (planned): Background job execution engine
- **cache_manager.py** (planned): Cache expiry and refresh logic

**PyArr Usage Pattern** (implemented in services):

```python
from pyarr import RadarrAPI, SonarrAPI

# Initialize client
radarr = RadarrAPI(host_url=base_url, api_key=api_key)

# Fetch data (✅ IMPLEMENTED)
quality_profiles = radarr.get_quality_profile()
root_folders = radarr.get_root_folder()
system_status = radarr.get_system_status()

# Future implementation (⚠️ NOT YET IMPLEMENTED)
tags = radarr.get_tag()
radarr.add_movie(db_id=tmdb_id, quality_profile_id=profile_id, root_dir=root_path)
```

## Key Workflows

### Service Configuration Flow (Implemented)

**TMDB Configuration** (`/settings`):

1. User enters API key in settings form
2. Optional: Click "Test Connection" button
   - JavaScript reads CSRF token from `<meta name="csrf-token">` tag
   - AJAX POST to `/settings/test_tmdb_api` with `X-CSRFToken` header
   - Helper function `_test_and_update_tmdb_status()` tests key and updates DB
   - Updates `ServiceConfig.last_tested_at` and `last_test_status`
   - Returns timestamp for immediate UI update
   - **Field contents preserved** (no page reload)
3. Click "Save API Key"
   - Form submits with CSRF token
   - Key tested automatically before encryption
   - Key encrypted via `crypto_utils.encrypt_data(instance_path=current_app.instance_path)`
   - Stored in `ServiceConfig.api_key_encrypted` with test metadata
4. Page reloads with success/error flash message
5. UI displays last test timestamp with color-coded status indicator (✓ green for success, ✗ red for failure)

**Radarr/Sonarr Configuration** (`/config`):

1. User enters base URL and API key in config form
2. Optional: Click "Test Connection" button
   - JavaScript reads CSRF token from meta tag
   - AJAX POST to `/config/test_radarr_api` or `/config/test_sonarr_api` with `X-CSRFToken` header
   - **URL validation** - Validates URL format before testing connection
   - Helper function `_test_and_update_radarr_status()` or `_test_and_update_sonarr_status()` tests connection
   - Tests via `/api/v3/system/status` endpoint
   - Updates database with test results (with proper error handling and rollback)
   - Returns timestamp for immediate UI update
   - **Field contents preserved** (no page reload)
3. Click "Save API"
   - Form submits with CSRF token (via `{{ form.hidden_tag() }}`)
   - **URL validation** - Validates URL format before processing
   - URL and API key tested automatically before encryption
   - API key encrypted with proper instance_path
   - Stored in `ServiceConfig` with base_url and encrypted API key
   - **Error handling** - Database rollback on failures with user-friendly error messages
4. Page reloads with success/error flash message
5. **Import Settings dropdown appears** (was hidden before configuration)
6. UI displays last test timestamp with status indicator

**Key Features**:

- All API keys encrypted at rest with Fernet
- **URL validation** - Ensures valid URL format before saving or testing
- Test operations update database regardless of success/failure
- **Proper error handling** - Database rollback on failures with logging
- CSRF protection on all AJAX and form submissions
- Field preservation during AJAX test operations
- Helper functions eliminate code duplication
- Conditional UI based on configuration state

### List Execution Flow (Planned)

1. **Trigger**: Manual execution or cron schedule
2. **Validation**: Check target service configuration exists
3. **Cache Check** (if cached list):
   - If expired: Block execution → trigger refresh job → wait → continue
   - If valid: Use cached items
4. **TMDB Fetch** (if live list or cache refresh):
   - Apply filters and limits
   - Apply global blacklist
   - Sanitize and map to Radarr/Sonarr fields
5. **Import Queue**:
   - Check for existing items in target service (skip if exists)
   - Queue remaining items for import
   - Create Job record with pending status
6. **Execution**:
   - Process queue sequentially
   - Create JobItem for each item
   - Update Job metrics (items_added, items_skipped)
   - Handle errors gracefully
7. **Completion**: Update Job status, log results

### Job Monitoring Flow (Planned)

- Jobs Page displays all jobs in a table
- Columns: Job ID/Name, Target Service, Status, Start/End Time, Items Processed
- Actions: Retry failed jobs, Cancel running jobs, Delete job history
- Per-job logs visible inline (collapsible), downloadable

## UI/UX Design Guidelines

### Toast Notifications (Standard Pattern)

**IMPORTANT**: Use JavaScript toast notifications instead of Flask flash messages for all user feedback. This provides a consistent, modern UX with auto-dismissing notifications in the top-right corner.

**Implementation Location**: `listarr/static/js/lists.js` exports the `showToast()` function.

**Usage**:
```javascript
// Success notification (green)
showToast("List created successfully!", "success");

// Error notification (red)
showToast("Failed to delete list. Please try again.", "error");

// Warning notification (yellow)
showToast("Some items could not be imported.", "warning");

// Info notification (blue)
showToast("Refreshing data...", "info");

// Custom duration (default is 3000ms)
showToast("Processing complete!", "success", 5000);
```

**Supported Types**:
| Type | Color | Icon | Use Case |
|------|-------|------|----------|
| `success` | Green | Checkmark | Successful operations (create, update, delete) |
| `error` | Red | X | Failed operations, validation errors |
| `warning` | Yellow | Triangle | Partial failures, deprecation notices |
| `info` | Blue | Info circle | Status updates, neutral information |

**Key Features**:
- Auto-dismisses after 3 seconds (configurable)
- Fade-out animation
- Fixed position top-right (`fixed top-4 right-4`)
- Dark mode support
- XSS-safe (uses `escapeHtml()`)

**Pattern for AJAX Operations**:
```javascript
fetch("/endpoint", { method: "POST", ... })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      showToast(data.message || "Operation successful!", "success");
    } else {
      showToast(data.message || "Operation failed", "error");
    }
  })
  .catch(error => {
    showToast("Network error. Please try again.", "error");
  });
```

**Pattern for URL Parameter Messages** (after redirects):
```javascript
// In initPage() function
const urlParams = new URLSearchParams(window.location.search);
const successAction = urlParams.get("success");
if (successAction === "created" || successAction === "updated") {
  showToast(`List ${successAction} successfully!`, "success");
  // Clean URL
  const url = new URL(window.location);
  url.searchParams.delete("success");
  window.history.replaceState({}, "", url);
}
```

**DO NOT USE**: Flask flash messages (`flash()`) for user feedback. Toast notifications provide better UX.

### Global Styles

- Single-page feel with top navigation
- System-based dark mode
- Fully responsive
- Tailwind CSS
- Toast notifications for user feedback (not flash messages)

### Loading States

- **Initial load**: Full skeletons matching final layout
- **Live refresh**: Subtle shimmer on affected components
- **Buttons**: Disabled during actions
- **Tables**: Simplified skeletons

### Page Specifications

**Dashboard**:

- Service cards with stats (Radarr: total movies, missing movies; Sonarr: total series, missing series)
- Status icons (online / offline / not_configured)
- Manual refresh button with loading state
- Auto-refresh (5-minute interval)
- Recent Jobs table (enhancement - shows last 5 executed jobs)
- Note: Last-updated timestamp available in API but not yet displayed in UI

**Settings Page**:

- TMDB API key configuration
- Test connection button (AJAX, no page reload)
- API key masked with toggle reveal (eye icon)
- Last test timestamp display with success/failure indicators
- JavaScript helpers in `settings.js`:
  - `formatTimestamp(isoTimestamp)` - Consistent timestamp formatting
  - `generateStatusHTML(success, timestamp)` - Status indicator generation
  - `toggleTMDBKey()` - Show/hide TMDB API key

**Config Page**:

- Single page with per-service sections (Radarr and Sonarr side-by-side)
- Test connection per service (AJAX, no page reload)
- API keys masked with toggle reveal (eye icon)
- Import Settings collapsible sections (hidden until service configured)
- Last test timestamp display with success/failure indicators
- JavaScript helpers in `config.js`:
  - `formatTimestamp(isoTimestamp)` - Consistent timestamp formatting
  - `generateStatusHTML(success, timestamp)` - Status indicator generation
  - `toggleApiKey(inputId, button)` - Show/hide API key
  - `toggleImportSettings(id, button)` - Collapse/expand import settings

**List Generation Page**:

- Stepper / wizard interface
- Preview before import with pagination (client-side slicing)
- Bulk select/deselect
- Custom list naming required
- Lists immutable after creation

**Jobs Page**:

- Central activity monitoring
- Table with pagination (10/25/50 rows)
- Filtering by status and service
- Retry/cancel support
- Inline collapsible logs
- Downloadable full logs

## Error Handling

### Centralized Error Handler (Planned)

- Standardized error objects
- Maps errors to:
  - UI alerts
  - Log entries
  - HTTP status codes
- Error severity controls:
  - Inline validation
  - Dismissible alerts
  - Navigation blocking (critical errors)

### Logging

- **Structured logging** - Uses Python's `logging` module throughout the codebase
- Service layer uses module-level loggers (e.g., `logger = logging.getLogger(__name__)`)
- Route handlers use Flask's `current_app.logger` for application-level logging
- Error logging includes full exception traces with `exc_info=True`
- Logs exportable per job (planned)
- No runtime debug controls
- All logs sanitized (no API keys, tokens)
- Jobs page is the sole operational visibility

## Instance Folder

The `instance/` directory at the project root stores all runtime data:

- `listarr.db`: SQLite database
- `.fernet_key`: Encryption key (NEVER commit this)

**Important**: Both files are in the same directory at `<project_root>/instance/`

- Flask's `app.instance_path` automatically resolves to this location
- The crypto utilities use `app.instance_path` dynamically (no hardcoded paths)
- This folder is created automatically by `create_app()` and `setup.py`

## Important Development Notes

### Error Handling & Database Management

- **Database Rollback**: Always wrap database operations in try/except blocks
  - Use `db.session.rollback()` on exceptions to prevent partial commits
  - Log errors with `current_app.logger.error()` including `exc_info=True` for full traces
  - Provide user-friendly error messages via flash messages
  - Example pattern:
    ```python
    try:
        # Database operations
        db.session.commit()
        flash("Operation successful", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error message: {e}", exc_info=True)
        flash("User-friendly error message", "error")
    ```
- **Service Layer Error Handling**: Service functions use Python's `logging` module
  - Module-level loggers: `logger = logging.getLogger(__name__)`
  - Log errors with full exception traces: `logger.error("message", exc_info=True)`
  - Return empty lists/dicts on errors (consider raising exceptions for critical failures)

### Security & Encryption

- **Encryption Key Required**: The app will not start without a valid encryption key. Run `setup.py` first.
- **API Key Security**: All API keys are stored encrypted in the database using Fernet symmetric encryption.
- **Instance Path Usage**: Always pass `current_app.instance_path` when calling crypto functions from routes to ensure correct path resolution.
  - Example: `encrypt_data(api_key, instance_path=current_app.instance_path)`
  - Example: `decrypt_data(encrypted_key, instance_path=current_app.instance_path)`
- **Input Validation**: URL validation is performed before saving or testing connections
  - Helper function `_is_valid_url()` uses `urllib.parse.urlparse` to validate URL format
  - Validates both in form submissions and AJAX endpoints
  - Provides clear error messages for invalid URLs
- **CSRF Token Requirements**: All AJAX requests MUST include the CSRF token:
  ```javascript
  const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
  fetch("/endpoint", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({ data: value }),
  });
  ```
- **Form CSRF Protection**: All forms must include `{{ form.hidden_tag() }}` for CSRF token

### Architecture Patterns

- **Blueprint Import Pattern**: Route modules use `from listarr.routes import bp` then register handlers with `@bp.route()`.
- **Database Initialization**: Use `db.create_all()` within app context to create tables.
- **Database Session Management**: All database operations use try/except blocks with `db.session.rollback()` on errors
  - Prevents partial commits and database inconsistencies
  - Errors are logged with `current_app.logger.error()` for debugging
  - User-friendly error messages via flash messages
- **Helper Functions**: Reusable test logic in helper functions (e.g., `_test_and_update_tmdb_status()`)
  - Eliminates code duplication between POST handlers and AJAX endpoints
  - Consistent database updates across all test operations
  - Includes proper error handling with rollback
- **Connection Test Tracking**: The `ServiceConfig` model tracks test attempts with `last_tested_at` and `last_test_status` fields, updated by both save and test operations.
- **Conditional UI Rendering**: Use flags like `radarr_configured` and `sonarr_configured` to show/hide UI elements based on configuration state
- **Input Validation**: URL validation helper function `_is_valid_url()` ensures valid URL format before processing

### Business Logic

- **No Per-List Import Overrides**: All import settings are global (configured once on Config page).
- **Cache Strategy**: Only sanitized + Radarr/Sonarr-mapped fields stored, never raw TMDB payloads.
- **Mixed Content Blocking**: Lists must be movies-only OR TV-only, never mixed.
- **Global Blacklist**: User-defined only (no defaults), supports ISO language codes, applied during list execution.

### Development & Debugging

- **Debug Mode**: Controlled via `FLASK_DEBUG` environment variable (defaults to `False`)
  - Development: `FLASK_DEBUG=true python run.py`
  - Production: Leave unset or set to `false` for safety
- **Logging Configuration**: Basic logging configured in `create_app()`
  - Uses Python's `logging` module with INFO level
  - Format: `'%(asctime)s %(name)s %(levelname)s: %(message)s'`
  - Service modules use module-level loggers
  - Route handlers use Flask's `current_app.logger`

### Testing

- **Test Suite**: Comprehensive pytest-based test suite with ~95% coverage
  - **Test Organization**: Tests organized by component (unit, routes, integration)
  - **Test Count**: 84+ tests covering all critical functionality
  - **Test Files**: Located in `tests/` directory with clear separation of concerns
    - `tests/unit/` - Unit tests for services and utilities
    - `tests/routes/` - Route handler tests
    - `tests/integration/` - End-to-end integration tests
  - **Test Coverage**: Comprehensive coverage including:
    - Error handling (decryption errors, DB errors, API failures)
    - Validation (field validation, type validation, URL validation)
    - Edge cases (concurrent operations, special characters, Unicode)
    - Security (CSRF protection, encryption verification)
- **Running Tests**:

  ```bash
  # Run all tests
  pytest tests/ -v

  # Run with coverage
  pytest --cov=listarr --cov-report=html tests/

  # Run specific test file
  pytest tests/routes/test_config_routes.py -v
  ```

- **Test Patterns**:
  - Proper test isolation with fixtures (`temp_instance_path`, `app`, `client`)
  - External API calls properly mocked
  - Database operations use in-memory SQLite for speed
  - Comprehensive error scenario testing
  - Parameterized tests for similar scenarios
- **Test Documentation**: See `docs/TEST_REVIEW.md` and `docs/CONFIG_ROUTES_TEST_REVIEW.md` for detailed test coverage analysis

## Dependencies

### Python Requirements

The project uses several key Python libraries defined in `requirements.txt`:

- **Flask**: Web framework and application server
- **Flask-SQLAlchemy**: ORM for database management
- **Flask-WTF**: Forms with CSRF protection
- **cryptography**: Fernet encryption for API keys
- **requests**: HTTP client for API calls (used for general HTTP operations)
- **tmdbv3api** ✅: TMDB (The Movie Database) API client
  - Version: `1.9.0`
  - Status: Fully integrated in `requirements.txt` and used in `tmdb_service.py`
  - Provides access to TMDB API v3 for movie/TV discovery, trending, popular, and IMDB ID mapping
- **pyarr** ✅: Radarr/Sonarr API client classes
  - Version: `>=5.0.0`
  - Status: Fully integrated in `requirements.txt` and used throughout
  - Used in `radarr_service.py` and `sonarr_service.py`
- **gunicorn**: Production WSGI server for Docker deployment

## Environment Variables

- `LISTARR_SECRET_KEY`: Flask secret key (defaults to `dev_key_change_me`)
- `FERNET_KEY`: Optional override for encryption key (otherwise loaded from file)
- `FLASK_DEBUG`: Enable Flask debug mode (defaults to `False` for safety). Set to `true` for development debugging

## Next Implementation Priorities

### ✅ Phase 1: Complete Import Settings — **COMPLETE** ✅

**Goal**: Make Config page Import Settings fully functional with real API data

**Status**: All objectives achieved! Import Settings are now fully functional for both Radarr and Sonarr.

**What was completed**:

1. ✅ **PyArr library integrated**

   - Added `pyarr>=5.0.0` to `requirements.txt`
   - Fully integrated throughout codebase

2. ✅ **Radarr/Sonarr services refactored to use PyArr**

   - Replaced all `requests` calls with `RadarrAPI` and `SonarrAPI` classes
   - Migrated `test_radarr_api_key()` and `test_sonarr_api_key()` to use PyArr
   - Added comprehensive error handling

3. ✅ **API data fetching functions implemented**

   - `radarr_service.py`:
     - ✅ `get_quality_profiles(base_url, api_key)` - Returns quality profile dicts
     - ✅ `get_root_folders(base_url, api_key)` - Returns root folder dicts
   - `sonarr_service.py`:
     - ✅ `get_quality_profiles(base_url, api_key)` - Returns quality profile dicts
     - ✅ `get_root_folders(base_url, api_key)` - Returns root folder dicts

4. ✅ **Backend routes created for Import Settings**

   - `config_routes.py`:
     - ✅ `GET /config/radarr/quality-profiles` - Fetch Radarr quality profiles
     - ✅ `GET /config/radarr/root-folders` - Fetch Radarr root folders
     - ✅ `GET /config/radarr/import-settings` - Retrieve saved Radarr settings
     - ✅ `POST /config/radarr/import-settings` - Save Radarr import settings
     - ✅ `GET /config/sonarr/quality-profiles` - Fetch Sonarr quality profiles
     - ✅ `GET /config/sonarr/root-folders` - Fetch Sonarr root folders
     - ✅ `GET /config/sonarr/import-settings` - Retrieve saved Sonarr settings
     - ✅ `POST /config/sonarr/import-settings` - Save Sonarr import settings

5. ✅ **config.html template updated**

   - Replaced hardcoded dropdown options with proper form elements
   - Added IDs to all dropdowns for JavaScript access
   - Radarr fields: Root Folder, Quality Profile, Monitor, Search on Add, Tags (disabled)
   - Sonarr fields: Root Folder, Quality Profile, Monitor, Season Folder, Search on Add, Tags (disabled)
   - Loading states implemented ("Loading...", "Select X" placeholders)

6. ✅ **config.js fully implemented**

   - Data fetching functions: `fetchRadarrRootFolders()`, `fetchRadarrQualityProfiles()`, `fetchSonarrRootFolders()`, `fetchSonarrQualityProfiles()`
   - Dropdown population with real API data
   - Save handlers with full validation for both services
   - Load functions to restore saved settings: `loadRadarrSavedSettings()`, `loadSonarrSavedSettings()`
   - Flag-based caching (`radarrDataLoaded`, `sonarrDataLoaded`) to prevent redundant API calls
   - CSRF token included in all AJAX requests

7. ✅ **End-to-end flow tested and working**
   - Dropdowns populate with real data from Radarr/Sonarr APIs
   - Settings save successfully to `MediaImportSettings` table
   - Settings persist across page reloads
   - Comprehensive error handling (frontend validation + backend validation)
   - Loading states and disabled inputs during operations

**Additional Features Implemented**:

- ✅ "Select X" placeholders for all dropdowns (better UX)
- ✅ Client-side validation before save (alerts for missing selections)
- ✅ Server-side validation (400 errors with descriptive messages)
- ✅ Season Folder field for Sonarr (TV-specific setting)
- ✅ Data caching to prevent API spam on toggle (simple flag-based caching)

**Success Criteria — ALL MET**:

- ✅ Import Settings dropdowns show real data from Radarr/Sonarr
- ✅ Settings save successfully to `MediaImportSettings` table
- ✅ Settings persist across page reloads
- ✅ Proper error handling for API failures
- ✅ No redundant API calls (flag-based caching)
- ✅ Clean, maintainable code following existing patterns

---

### ✅ Phase 2: Dashboard Stats — **COMPLETE** ✅

**Goal**: Implement dashboard with live stats from Radarr/Sonarr

**Status**: All objectives achieved! Dashboard is fully functional with live data.

**What was completed**:

8. ✅ **Extended service functions for dashboard data**
   - ✅ `get_missing_episodes_count()` - Uses `get_wanted()` totalRecords
   - ✅ Missing fields handling in `get_missing_movies_count()`

   - ✅ `get_system_status()` - Returns version, instance_name, is_production, is_debug
   - ✅ `get_movie_count()` - Returns total movie count from Radarr
   - ✅ `get_series_count()` - Returns total series count from Sonarr
   - ✅ `get_missing_movies_count()` - Returns missing movie count (enhancement)
   - ✅ `get_missing_series_count()` - Returns missing series count (enhancement)
   - ⚠️ Note: Disk space not available via PyArr system_status endpoint

9. ✅ **Created dashboard routes**

   - ✅ `GET /api/dashboard/stats` - Cached stats from all configured services
   - ✅ `GET /api/dashboard/stats?refresh=true` - Force cache refresh
   - ✅ `GET /api/dashboard/recent-jobs` - Recent job execution history

10. ✅ **Implemented dashboard caching system**

   - ✅ In-memory cache with thread-safe locking
   - ✅ Startup initialization for fast page loads
   - ✅ On-demand refresh via query parameter
   - ✅ Graceful handling of missing database tables

11. ✅ **Added "Added by Listarr" feature**

   - ✅ Calculates total items added from completed jobs
   - ✅ Separate counters for Radarr and Sonarr
   - ✅ Displayed in dashboard cards
   - ✅ Parallel execution using ThreadPoolExecutor (6 workers)
   - ✅ Comprehensive error handling with graceful degradation
   - ⚠️ Note: Relies on 5-minute auto-refresh for caching (no explicit cache layer)

12. ✅ **Implemented Dashboard UI**

   - ✅ Service status cards with indicators
   - ✅ "Added by Listarr" counters
   - ✅ Recent jobs table with formatted dates
   - ✅ Manual refresh button with loading states
   - ✅ Auto-refresh functionality (5-minute interval)
    - ✅ Replaced placeholder stats with real API data
    - ✅ Manual refresh button with loading state
    - ✅ Auto-refresh at 5-minute interval (within recommended range)
    - ✅ Status indicators with color coding (online/offline/not_configured)
    - ✅ Recent Jobs table (enhancement beyond original spec)

**Additional Features Implemented**:

- ✅ Recent Jobs section showing last 5 executed jobs
- ✅ Parallel API calls for better performance
- ✅ Graceful error handling (shows "—" or "Error" on failures)
- ✅ HTML escaping for security
- ✅ Separate timeouts for fast vs slow operations

**Success Criteria — ALL MET**:

- ✅ Dashboard displays real data from Radarr/Sonarr
- ✅ Manual and auto-refresh functionality working
- ✅ Status indicators display correctly
- ✅ Proper error handling for offline services
- ✅ Clean, maintainable code following existing patterns

See `docs/DASHBOARD_VALIDATION_REPORT.md` for detailed validation report.

---

### Phase 3: List Generation & Job Execution (NEXT PRIORITY)

11. ✅ **TMDB Service Expansion** — **COMPLETE**

    - ✅ Implemented trending, popular, and discover list fetching via tmdbv3api
    - ✅ IMDB ID mapping via TMDB external_ids endpoint
    - ✅ Filter support (genre, year, language, rating) in discover functions
    - ⚠️ Still needed: Sanitization and mapping to Radarr/Sonarr fields (in list execution logic)

12. **List Wizard UI** (NEXT)
    - Multi-step form for list creation
    - Preview with pagination
    - Bulk select/deselect
    - Integration with tmdb_service functions
    - Display IMDB links for reference

### Phase 4: Job Execution & Monitoring

13. **Job Execution Engine**

    - Background task runner
    - Import queue logic
    - Error handling and retries

14. **Jobs Page UI**
    - Activity monitoring
    - Inline logs
    - Retry/cancel support

### Phase 5: Advanced Features

15. **Scheduling System**: Cron integration
16. **Cache Management**: TTL tracking and refresh logic
17. **Global Blacklist**: User-defined content filtering
