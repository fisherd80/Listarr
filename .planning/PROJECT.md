# Listarr

## What This Is

Listarr is a homelab-quality Flask application that automatically discovers and imports movies and TV shows into Radarr and Sonarr. It generates curated lists from TMDB (trending, popular, discovery filters) and imports them automatically via scheduled jobs or manual triggers, eliminating the tedium of manual media discovery and ensuring fresh content flows into your media library without intervention.

## Core Value

Automated media discovery and import that just works - fresh content flows into Radarr/Sonarr automatically based on TMDB lists, running reliably 24/7 without intervention.

## Requirements

### Validated

- ✓ TMDB API integration (trending, popular, discovery) — existing
- ✓ Radarr API integration (quality profiles, root folders, system status, import) — existing
- ✓ Sonarr API integration (quality profiles, root folders, system status, import) — existing
- ✓ Dashboard with cached service statistics — existing
- ✓ Configuration management with encrypted API key storage — existing
- ✓ Docker containerization with docker-compose support — existing
- ✓ SQLite database with models for Lists, Jobs, ServiceConfig, MediaImportSettings — existing
- ✓ Comprehensive test suite (363 tests, 100% pass rate) — existing

### Active

- [ ] Automated list generation from TMDB sources (trending, popular, custom filters)
- [ ] Scheduled job execution system (cron-based automation for list refreshes)
- [ ] Manual trigger capability (run any list on-demand from UI)
- [ ] Reliable import automation to Radarr/Sonarr with proper error handling
- [ ] Smart TMDB caching to respect API rate limits
- [ ] Job execution tracking and history with success/failure reporting
- [ ] List management UI (create, edit, delete, enable/disable lists)
- [ ] Rock-solid error handling and logging for 24/7 reliability

### Out of Scope

- User authentication and multi-user support — single-user homelab deployment only
- Advanced analytics and complex dashboards — basic stats are sufficient
- Custom integrations beyond Radarr/Sonarr — no Plex, Jellyfin, Emby direct integration
- Mobile-specific app — responsive web UI is sufficient

## Context

### Current State

Listarr has a solid foundation with working TMDB, Radarr, and Sonarr integrations. The configuration system, dashboard, and encrypted secrets management are operational. The codebase has comprehensive test coverage and Docker deployment ready.

### Key Problems Being Solved

1. **Manual discovery is tedious** - Eliminating the need to manually search TMDB and add items to Radarr/Sonarr one by one
2. **Missing new releases** - Automatically discovering new movies/shows as they become available
3. **Library stagnation** - Keeping media library fresh with automated content discovery based on preferences

### Known Technical Debt

- Duplicate code between Radarr and Sonarr services (~326 lines of duplication)
- Oversized config_routes.py (592 lines handling both services)
- N+1 query pattern in dashboard recent jobs
- Missing HTTP status checks in frontend AJAX calls
- Bare exception clauses masking errors in service validation

### Codebase Map

Comprehensive codebase documentation exists in `.planning/codebase/`:
- STACK.md - Python 3.11, Flask 3.0, SQLAlchemy, Docker
- ARCHITECTURE.md - Layered MVC pattern, service abstractions
- STRUCTURE.md - Directory organization and conventions
- CONVENTIONS.md - Code style, naming, patterns
- TESTING.md - pytest framework, 363 tests
- INTEGRATIONS.md - TMDB, Radarr, Sonarr API clients
- CONCERNS.md - Technical debt, known bugs, security considerations

## Constraints

- **Docker Deployment**: Must be fully containerized with docker-compose support — non-negotiable homelab requirement
- **Tech Stack**: Must maintain existing Flask + Python 3.11 + SQLite stack — no rewrites
- **TMDB API Rate Limits**: Must implement smart caching and throttling to respect TMDB API limits
- **Reliability**: Must handle errors gracefully and run 24/7 without intervention — homelab quality standard

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Docker-first deployment | Homelab standard, ensures consistent environment | — Pending |
| Single-user design | Homelab use case, reduces complexity | — Pending |
| SQLite database | Embedded, no external dependencies, sufficient for homelab scale | — Pending |
| Encrypted API key storage | Security best practice for sensitive credentials | — Pending |

---
*Last updated: 2026-01-12 after initialization*
