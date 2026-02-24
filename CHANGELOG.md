# Changelog

All notable changes to Listarr are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

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
