# Changelog

All notable changes to Listarr are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

## [2.0.0] - 2026-04-30

### Added

- Semantic CSS token system (22 design tokens) enabling full dark/light mode across all templates and JS
- Live service status badge in the navigation header showing Radarr/Sonarr connectivity at a glance
- Activity Run Detail page with expandable task output and Back to Activity navigation
- Last Run and Result columns on the Lists page with formatted relative timestamps
- Editable list size field on the edit page with backend persistence
- Genre filter with three-state pill/chip toggles (include / exclude / neutral) on the creation wizard
- Unraid Community App template for simplified homelab deployment

### Changed

- Redesigned navigation to a 3-link structure (Lists, Activity, Settings), removing the Dashboard
- Redesigned Lists page with a dense data table, sortable/filterable columns, toggle, and overflow action menu
- Redesigned Settings to a 3-tab UI (Services, General, Account) with connection testing per service
- Reworked Activity page with numbered pagination, overflow menu, and No Change status display
- API keys now populate into Settings form fields to support visibility toggle
- All templates and JavaScript files migrated from hardcoded palette classes to semantic colour tokens
- Project restructured for public release with updated README and Docker documentation

### Fixed

- Database-level unique constraint preventing duplicate concurrent job execution per list
- TOCTOU race condition that could trigger duplicate Sonarr import jobs
- Overflow dropdown clipping on Lists page fixed with fixed positioning
- Cron expression pre-population on the edit page
- Numeric tag IDs rejected in wizard submit; TMDB items deduplicated within import batch
- Flask catch-all error handler now passes through Werkzeug `HTTPException` responses (preserving 405 etc.)
- Various UI consistency fixes: pagination padding, breadcrumb redundancy, hover tokens, table header backgrounds
- Account tab activates correctly when navigating directly to `/settings#account`

### Security

- Removed dead `POST /lists/create` endpoint; route now correctly returns 405 before auth or CSRF handling
- Escaped service badge labels before `innerHTML` insertion to prevent XSS
- Regression test suite locks the 405 contract and preserves all GET creation routes

## [1.0.0] - 2026-02-21

Initial release.

### Added

- TMDB integration for discovering movies and TV shows (Trending, Popular, Top Rated, Discover with filters)
- Radarr import with configurable quality profiles, root folders, tags, and monitoring
- Sonarr import with configurable quality profiles, root folders, tags, season folders, and monitoring
- Bulk import API for batch operations (50 items per batch)
- Multi-step list creation wizard with preset templates and live TMDB preview
- Per-list import setting overrides (fall back to global defaults)
- Cron-based scheduling with preset intervals and custom expressions
- Global scheduler pause/resume for maintenance
- Pre-flight health checks before scheduled job execution
- Background job execution with activity-based idle timeout
- Job monitoring page with filtering, pagination, and expandable details
- Dashboard with read-only Radarr/Sonarr stats and recent job activity
- Region filtering for TMDB results
- Single-user authentication with setup wizard
- Password management (change via Settings, CLI reset)
- Dark mode with persistent toggle

### Security

- API keys encrypted at rest (Fernet symmetric encryption)
- CSRF protection on all forms and AJAX requests
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options)
- Secure session cookies (HttpOnly, SameSite=Lax, configurable Secure flag)
- Open redirect prevention on login
- Non-root Docker container

### Technical

- Direct HTTP integration with Radarr, Sonarr, and TMDB APIs (no third-party wrappers)
- SQLite with WAL mode for concurrent access
- Locally compiled Tailwind CSS (no CDN dependency)
- Docker-first deployment with health checks
- 596 automated tests
