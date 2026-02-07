# Project State

**Project:** Listarr
**Milestone:** v1.0 - Automated Media Discovery
**Last Updated:** 2026-02-07

## Current Status

**Phase:** 9.1 - Config & JS Deduplication
**Plan:** 3 of 3 (Complete)
**Status:** Complete
**Last activity:** 2026-02-07 - Completed 09.1-03-PLAN.md (Config.js & Utils.js Consolidation)

## Phase Progress

| Phase | Status | Plans Complete | Verification |
|-------|--------|----------------|--------------|
| 1. List Management System | Complete | 2/2 | Verified |
| 2. List Creation Wizard | Complete | 5/5 + FIX | Verified |
| 3. TMDB Caching Layer | Complete | 2/2 | Verified |
| 3.1 Update Config Page Tags | Complete | 1/1 | Verified |
| 4. Import Automation Engine | Complete | 3/3 + FIX | Verified |
| 5. Manual Trigger UI | Complete | 2/2 + FIX | Verified |
| 6. Job Execution Framework | Complete | 6/6 | Verified |
| 6.1 Bug Fixes | Complete | 2/2 | Verified |
| 6.2 List Enhancements | Complete | 3/3 | Verified |
| 6.3 Update Testing | Complete | 4/4 | Verified |
| 7. Scheduler System | Complete | 6/6 | Verified |
| 8. Architecture & API Consolidation | Complete | 6/6 | Verified |
| 9. Code Quality & Refactoring | Complete | 6/6 | Verified |
| 9.1 Config & JS Deduplication | Complete | 3/3 | - |
| 10. UI/UX Simplification | Not started | 0/? | - |
| 11. Security Hardening | Not started | 0/? | - |
| 12. Release Readiness | Not started | 0/? | - |

## Recent Activity

- 2026-02-07: Completed 09.1-03-PLAN (Config.js & Utils.js Consolidation)
  - Consolidated config.js from 746 to 322 lines (57% reduction)
  - Created utils.js with shared formatTimestamp and generateStatusHTML
  - Replaced 12 duplicate JS functions with 6 parameterized versions
  - Phase 9.1 complete (3/3 plans)
  - Commits: 70d9bdb, 07111c9
- 2026-02-07: Completed 09.1-02-PLAN (Test Mock Path Updates)
  - Updated mock paths in 115 config tests (route + integration)
  - Replaced service-specific mock paths with arr_service shared functions
  - Collapsed dual validate patches into single validate_api_key mock
  - 453 tests pass, 0 failures
  - Commit: 962ba33
- 2026-02-06: Completed 09.1-01-PLAN (Config Routes Deduplication)
  - Refactored config_routes.py from 897 to 404 lines (55% reduction)
  - Parameterized 8 duplicate Radarr/Sonarr routes into 4 shared endpoints
  - Replaced 18 service-specific imports with 5 arr_service shared functions
  - Extracted _save_service_config helper to eliminate 108 lines of duplication
  - Commit: 29545f6
  - Phase 9.1 progress (1/3 plans complete)
- 2026-02-05: Phase 9.1 inserted after Phase 9: Config & JS Deduplication (URGENT)
  - Source: 09-SLOP-REVIEW.md (flask-slop-refactor agent findings)
  - Target: config_routes.py (897→~350 lines), config.js (747→~350 lines)
  - ~950 lines of Radarr/Sonarr horizontal duplication to eliminate
- 2026-02-05: Phase 9 UAT complete (6/6 passed, 0 issues)
- 2026-02-05: Completed 08-06-PLAN (Documentation Update)
  - Created 08-ARCHITECTURE-CONCERNS.md with 6 prioritized technical debt items
  - Updated README.md with direct API architecture, 88% development status
  - Updated CHANGELOG.md with Phase 8 entry
  - Phase 8 complete (6/6 plans)
  - Commits: c0f3560, a5678ae, 3a855da
- 2026-02-05: Completed 08-05-PLAN (Dependency Removal)
  - Removed pyarr and tmdbv3api from requirements.txt
  - Verified all 423 tests pass without legacy dependencies
- 2026-02-05: Completed 08-04-PLAN (TMDB Service Migration)
  - Replaced tmdbv3api with direct HTTP calls using http_session
  - All 14 tmdb_service functions now use TMDB API v3 endpoints directly
  - Updated 52 tests to mock http_session instead of tmdbv3api classes
  - Maintained backward compatibility with identical function signatures
  - tmdb_cache.py continues to work without modification
  - 87 TMDB-related tests pass, 423 total tests pass
  - Commit: c35b275
  - Phase 8 progress (4/? plans complete)
- 2026-02-05: Completed 08-03-PLAN (Sonarr Service Migration)
  - Replaced pyarr with direct HTTP calls using http_session
  - All 12 sonarr_service functions now use Sonarr API v3 endpoints directly
  - Updated 29 tests to mock http_session instead of SonarrAPI
  - Maintained backward compatibility with identical function signatures
  - Full test suite passes (400 tests)
  - Commit: ad5b54b
  - Phase 8 progress (3/? plans complete)
- 2026-02-05: Completed 08-02-PLAN (Radarr Service Migration)
  - Replaced pyarr with direct HTTP calls using http_session
  - All 11 radarr_service functions now use Radarr API v3 endpoints directly
  - Updated 26 tests to mock http_session instead of RadarrAPI
  - Maintained backward compatibility with identical function signatures
  - Full test suite passes (400 tests)
  - Commit: 6d1309c
  - Phase 8 progress (2/? plans complete)
- 2026-02-05: Completed 08-01-PLAN (HTTP Client Module)
  - Created listarr/services/http_client.py with shared session
  - Configured retry strategy for 429, 500, 502, 503, 504 with exponential backoff
  - Added connection pooling (10 connections), 30-second timeout
  - Added normalize_url() helper for URL construction
  - Commits: f1a8601, a1d7eb6
  - Phase 8 started (1/? plans complete)
- 2026-02-05: Roadmap restructured for quality-focused finish
  - Phases 8-11 replaced with: Architecture & API Consolidation, Code Quality & Refactoring, UI/UX Simplification, Security Hardening, Release Readiness
  - pyarr and tmdbv3api removal consolidated into Phase 8
  - User Authentication deferred to Release Readiness decision point
  - Service Settings Caching evaluated during Architecture phase
- 2026-02-05: Phase 7 (Scheduler System) complete and verified
  - All 6 plans executed successfully
  - APScheduler 3.11.2 integration with cron-based scheduling
  - Schedule page with global pause/resume toggle
  - Lists UI shows next run times
  - Dashboard upcoming widget shows next 5 scheduled jobs
  - All documentation updated
- 2026-02-05: Completed 07-06-PLAN (Documentation Update)
  - Updated README.md with scheduler features, environment variables, and usage instructions
  - Added comprehensive Phase 7 entry to CHANGELOG.md
  - Updated CLAUDE.md with scheduler service documentation and workflow patterns
  - Development status updated (80% → 85%, Phase 7 complete)
  - Commits: 6f91938, 284e3c1, f72f236
  - Phase 7 complete (6/6 plans)
- 2026-02-05: Completed 07-04-PLAN (Lists UI Scheduler Integration)
  - Added next run subtitle to Lists page with format_relative_time helper
  - Updated edit form to sync schedule changes with APScheduler
  - Updated wizard save to register schedules on list creation
  - Toggle/delete routes now update scheduler state
  - Graceful error handling for scheduler operations
  - Commits: b456956, e26777d, 2ca0080
  - Phase 7 progress (6/? plans complete)
- 2026-02-05: Completed 07-05-PLAN (Dashboard Upcoming Widget)
  - Added GET /api/dashboard/upcoming endpoint
  - Created Upcoming widget in 2-column layout with Recent Jobs
  - Implemented JavaScript with fetchUpcomingJobs(), updateUpcomingWidget(), loadUpcoming()
  - Widget shows next 5 scheduled jobs with relative times
  - Integrated polling refresh (2-second interval when jobs running)
  - Paused badge displays when scheduler globally paused
  - Fixed missing scheduler_paused column in database (Rule 2 deviation)
  - Commits: 2236a2c, 0c1c12c, a2bf2bb
  - All endpoints verified working
  - Phase 7 progress (5/? plans complete)
- 2026-02-05: Completed 07-03-PLAN (Schedule Management Page)
  - Created schedule routes with 4 endpoints (/schedule, pause, resume, status)
  - Built schedule.html template with status badges and global pause toggle
  - Implemented schedule.js with auto-refresh polling and relative time formatting
  - Added Schedule link to navigation menu
  - Status hierarchy: Running > Paused > Scheduled > Manual only
  - 5-second polling when jobs running
  - Commits: 589e3e3, 5f391bf, c037246
  - All 444 tests passing
  - Phase 7 complete (3/3 plans)
- 2026-02-05: Completed 07-02-PLAN (Scheduler Service)
  - Created scheduler.py with APScheduler integration (346 lines)
  - Implemented schedule_list, unschedule_list, pause/resume, validate_cron_expression
  - Integrated scheduler initialization into create_app()
  - Scheduler loads existing schedules from database on startup
  - Fixed cronsim next_runs calculation and Flask app proxy detection
  - Commits: ccdf760, cc72ceb
  - All 444 tests passing
  - Phase 7 progress (2/? plans complete)
- 2026-02-05: Completed 07-01-PLAN (Scheduler Foundation)
  - Installed APScheduler 3.11.2, cronsim 2.7, cron-descriptor 2.0.5
  - Added scheduler_paused boolean column to ServiceConfig model
  - Configured Gunicorn post_fork hook for single-worker scheduler pattern
  - Commits: 7cfb17c, 051cb9d, 28de602
  - Phase 7 started (1/? plans complete)
- 2026-02-01: Fixed two Docker deployment bugs (hotfixes)
  - SQLite WAL mode: Added graceful fallback for FUSE/network filesystems
  - Gunicorn logging: Configured error-only access logging (4xx/5xx only)
  - Commits: 3d5ae5c, ade102d (pushed to ai branch)
- 2026-02-01: Completed 06.3-04-PLAN (Final Coverage Analysis and Documentation)
  - Generated final coverage report: 444 tests, 56% overall coverage
  - Improvement from baseline: +29 tests, +4% coverage
  - Created TEST_SUMMARY.md with comprehensive test breakdown
  - Updated README.md with Phase 6.2 test structure
  - Verified 100% test pass rate (444 passed, 0 failed)
  - Phase 6.2 module improvements: tmdb_cache 14%→40%, tmdb_service 71%→83%, import_service 9%→22%
  - Commits: a12d83d, 6bb885b, 430585b
  - Phase 6.3 complete (4/4 plans)
- 2026-02-01: Completed 06.3-02-PLAN (TMDB Top Rated Test Coverage)
  - Added 15 comprehensive unit tests for Phase 6.2 top_rated functions
  - TestGetTopRatedMovies: 4 tests for get_top_rated_movies()
  - TestGetTopRatedTV: 4 tests for get_top_rated_tv()
  - TestGetTopRatedMoviesCached: 4 tests for cached movies with cache hit/miss scenarios
  - TestGetTopRatedTVCached: 3 tests for cached TV shows with cache hit/miss scenarios
  - Created tests/unit/test_tmdb_cache.py with clear_cache fixture for test isolation
  - Extended tests/unit/test_tmdb_service.py with top_rated test classes
  - All 444 tests pass (↑15 from 429)
  - Coverage: tmdb_cache improved from 14% to ~45%
  - Commits: 84704ac, ec9b731
- 2026-02-01: Completed 06.3-03-PLAN (Region Filtering and Top Rated Test Coverage)
  - Added 21 comprehensive tests for Phase 6.2 features
  - TestGetTMDBRegion: 4 tests for _get_tmdb_region() function
  - TestRegionAwareCacheKeys: 3 tests for cache key segregation by region
  - TestFetchTMDBItemsTopRated: 5 tests for top_rated import flow
  - TestFetchTMDBItemsLimitBehavior: 2 tests for multi-page fetching
  - Created tests/integration/test_import_integration.py
  - Extended tests/unit/test_tmdb_cache.py (coordinated with Plan 02)
  - All 21 new tests pass
  - Commits: 0997682, 896c799
- 2026-02-01: Completed 06.3-01-PLAN (Coverage Baseline and Gap Analysis)
  - Ran pytest-cov coverage analysis: 52% overall (415 tests passing)
  - Created coverage baseline report: tests/coverage-baseline.txt
  - Created prioritized gap analysis: tests/coverage-gaps.md
  - Phase 6.2 module coverage: 28% avg (lists_routes 16%, tmdb_cache 14%, import_service 9%, tmdb_service 71%)
  - Identified 4 test generation groups (Plans 02-03 for TMDB service/cache)
  - Commits: 1b844f8, 67c7b19
- 2026-01-31: Completed 06.2-03-PLAN (Preset UI Layout and Region Wiring)
  - Updated Lists page with 6 preset cards grouped by media type (Movies/TV)
  - Added Top Rated preset handling to wizard (labels, descriptions, default names)
  - Wired region setting into TMDB API calls for supported endpoints
  - Region filtering works for: movie popular, top_rated, discover/movie, discover/tv
  - Cache keys include region suffix (:US, :GB, or :WW for worldwide)
  - All 415 tests pass
  - Commits: b14a658, aecadaa, 4d1ba39
  - Phase 6.2 complete (3/3 plans)
- 2026-01-31: Completed 06.2-02-PLAN (TMDB Region and Limit Options)
  - Added tmdb_region column to ServiceConfig model (nullable String(2))
  - Added region dropdown to Settings page with top 5 + 19 extended countries
  - Updated wizard limit options: 25, 50, 100 (default), 250, 500, MAX (1000)
  - Added warning message for 500+ limit selections
  - Implemented legacy limit migration (10/20 -> 25) in edit mode
  - All 415 tests pass
  - Commits: 75988ec, 48d851d, 4c39eca
- 2026-01-31: Completed 06.2-01-PLAN (Top Rated Presets)
  - Added get_top_rated_movies() and get_top_rated_tv() to tmdb_service.py
  - Added get_top_rated_movies_cached() and get_top_rated_tv_cached() to tmdb_cache.py
  - Updated list_wizard() and wizard_preview() to handle top_rated presets
  - Updated _fetch_tmdb_items() for top_rated_movies and top_rated_tv list types
  - All 415 tests pass
  - Commits: 85c333f, d05982e, 59728fe
- 2026-01-31: Fixed movie edit form validation bug (post-6.1 hotfix)
  - Root cause: WTForms SelectField validated override_season_folder for all list types
  - Fix: Added validate_choice=False to allow missing field for Radarr lists
  - Verified: Both Radarr and Sonarr list editing now works correctly
  - Commit: 6cf1cfe
- 2026-01-31: Completed 06.1-02-PLAN (UI Bug Verification and Fix)
  - Verified Bug #4 (Run status) and Bug #5 (Toast notifications) working
  - Fixed Bug #6 (Edit navigation) - schedule choice mismatch between wizard and form
  - Synced SCHEDULE_CHOICES in ListForm with wizard template options
  - Added validation error flash message in edit_list route
  - All 415 tests pass
  - Phase 6.1 complete (2/2 plans)
- 2026-01-31: Completed 06.1-01-PLAN (Backend Bug Fixes)
  - Fixed tag override logic: if/elif pattern (override replaces, not merges)
  - Fixed logging: LOG_LEVEL env var configuration
  - Removed unused Tags table (deleted tag_model.py, removed FK constraint)
  - All 415 tests pass
- 2026-01-30: Phase 6 verification passed (6/6 must-haves)
  - Job model, executor, API, UI all verified against codebase
  - WAL mode, recovery, polling, filters all working
  - No stub patterns or placeholders found
- 2026-01-30: Completed 06-06-PLAN (Dashboard Recent Jobs Widget)
  - Updated dashboard.js to fetch from /api/jobs/recent
  - Added loadRecentJobs(), formatJobSummary(), formatDate(), escapeHtml() helpers
  - Added 2-second polling for running jobs
  - Running jobs show animated spinner
  - Completed jobs show "X added, Y skipped"
  - Failed jobs show truncated error message
  - Updated dashboard.html with loading state
  - All 415 tests pass
  - Phase 6 complete (6/6 plans)

## Next Steps

1. Start Phase 9 (Code Quality & Refactoring)
   - Review 08-ARCHITECTURE-CONCERNS.md for prioritized technical debt
   - Address duplicate code consolidation (HIGH priority)
   - Standardize error handling (HIGH priority)
2. Remaining phases: UI/UX (10), Security (11), Release (12)

## Blockers

None

## Session Continuity

Last session: 2026-02-07
Stopped at: Phase 9.1 complete (3/3 plans). Next: Phase 10 (UI/UX Simplification)
Resume file: None

## Notes

- Phase 2 wizard fully functional with all 4 steps
- Phase 3 TMDB caching layer complete
- Phase 3.1 tag storage complete - Config page tags functional
- Phase 4 import automation complete - Radarr and Sonarr imports working
- Phase 5: Run button with async import and status polling complete
- Phase 6 Wave 1: Job model enhanced, job_executor.py created
- Phase 6 Wave 2: Lists routes migrated, Jobs API complete
- Phase 6 Wave 3: Jobs page UI + Dashboard widget complete
- Jobs page: Paginated table, filters, expandable rows, rerun, clear, polling
- Dashboard widget: Recent jobs from DB, polling for running jobs
- Jobs API: Paginated listing, filtering, detail, rerun, clear
- Tag normalization: lowercase, hyphens, auto-create if missing
- Wizard preview uses cached calls for all TMDB operations
- Caches: trending (1h), popular (4h), discover (6h), details (24h)
- Debug endpoint available at /lists/debug/cache-stats
- Import endpoint: POST /lists/<id>/run (async, returns 202, now uses job_executor)
- Status endpoint: GET /lists/<id>/status (now reads from Job table)
- Job executor: submit_job(), is_list_running(), get_job_status()
- **Phase 6.2** Top rated presets: top_rated_movies, top_rated_tv (full UI and backend)
- **Phase 6.2** TMDB region setting in Settings page (ISO 3166-1 Alpha-2 codes)
- **Phase 6.2** Wizard limit options: 25, 50, 100 (default), 250, 500, MAX (1000)
- **Phase 6.2** 6 preset cards grouped by media type on Lists page
- **Phase 6.2** Region filtering wired into TMDB API calls for supported endpoints
- **Phase 7** Scheduler system: APScheduler integration with cron schedules
- **Phase 7** Scheduler service: schedule_list, unschedule_list, pause/resume, validate_cron
- **Phase 7** Schedule page: UI for managing scheduled lists with status display
- **Phase 7** Global pause toggle: Pause/resume all scheduled jobs from UI
- **Phase 7** Auto-refresh polling: 5-second updates when jobs running
- **Phase 8** HTTP client module: Shared session with connection pooling and retry strategy
- **Phase 8** Radarr service: pyarr replaced with direct HTTP calls via http_session
- **Phase 8** Sonarr service: pyarr replaced with direct HTTP calls via http_session
- **Phase 8** TMDB service: tmdbv3api replaced with direct HTTP calls via http_session

## Git Workflow

### Branches
- **`ai` branch:** All Claude/AI commits go here — MUST verify branch before committing
- **`develop` branch:** Integration branch — manual merge/squash from `ai` after phase completion
- **`main` branch:** Production — not used until near end of project

### Pre-commit Hooks (Enforced)
Commits are **rejected** if not complying with:
- **ruff** — Python linting
- **ruff-format** — Code formatting
- **black** — Code formatting

### Commit Process
1. Verify on `ai` branch (or switch to it) before committing
2. Stage changes and commit — pre-commit hooks run automatically
3. Fix any lint/format issues if commit rejected
4. Push to remote when ready

### Phase Completion Process
1. Complete all plans in phase
2. Resolve any bugs/fixes discovered during phase
3. Update documentation (see Documentation Standard below)
4. Commit and push documentation updates
5. **Manual merge/squash** from `ai` → `develop` (done by user)
6. GitHub Actions will validate — may require fixes

## Documentation Standard

**Update at phase completion** (after bugs/fixes resolved):
- **README.md** — Current features and capabilities
- **tests/README.md** — Test structure and coverage
- **CHANGELOG.md** — Document changes made in the phase
- **CLAUDE.md** — AI assistant context (if patterns/conventions changed)

## Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| Service-parameterized Flask routes with <service> URL parameter | Eliminate horizontal duplication between Radarr/Sonarr routes - same logic, different service names | 2026-02-06 |
| arr_service.py as single source of truth for Radarr/Sonarr operations | Phase 9 created shared functions (validate_api_key, get_quality_profiles, etc.) working for both services | 2026-02-06 |
| Direct HTTP calls in tmdb_service.py | Replace tmdbv3api dependency with http_session for consistent retry/timeout behavior | 2026-02-05 |
| Architecture concerns documentation | Document 6 technical debt items for Phase 9 review (duplicate code, error handling, module size, cache async, rate limiting, service layer value) | 2026-02-05 |
| Development status 88% | Phase 8 complete, reflects 12 of 13 phases done | 2026-02-05 |
| Direct HTTP calls in sonarr_service.py | Replace pyarr dependency with http_session for consistent retry/timeout behavior | 2026-02-05 |
| Direct HTTP calls in radarr_service.py | Replace pyarr dependency with http_session for consistent retry/timeout behavior | 2026-02-05 |
| 30-second default timeout for HTTP requests | Sufficient for slow API responses while preventing indefinite hangs | 2026-02-05 |
| Retry on 429, 500, 502, 503, 504 errors | Handles common transient errors (rate limits, server errors) | 2026-02-05 |
| Connection pool size of 10 | Matches typical service count (Radarr, Sonarr, TMDB) | 2026-02-05 |
| Module-level singleton http_session | Ensures all services share connection pool for efficiency | 2026-02-05 |
| Lists page shows next run subtitles for scheduled lists | At-a-glance visibility of next scheduled run without navigating to schedule page | 2026-02-05 |
| Scheduler sync after DB commit in routes | Ensures database consistency before registering/updating APScheduler jobs | 2026-02-05 |
| Graceful scheduler error handling in routes | Non-blocking operations allow list management in non-scheduler workers | 2026-02-05 |
| format_relative_time helper uses minute/hour/day units | Human-readable upcoming job times (in 2 hours, in 3 days) | 2026-02-05 |
| Upcoming widget limited to 5 jobs | At-a-glance visibility without overwhelming dashboard | 2026-02-05 |
| Upcoming widget refreshes during job polling | Ensures relative times stay current when jobs are running | 2026-02-05 |
| Status badge hierarchy: Running > Paused > Scheduled > Manual only | Prioritizes most actionable state for users | 2026-02-05 |
| 5-second polling for schedule page when jobs running | Fast updates for active jobs without excessive server load | 2026-02-05 |
| Relative time formatting for schedule page | More intuitive UX than absolute timestamps | 2026-02-05 |
| Singleton scheduler instance (module-level) | Prevents multiple scheduler instances, simplifies access from other modules | 2026-02-05 |
| cronsim advance() + tick() for next_runs | advance() finds next match, tick() moves forward 1s to find subsequent matches | 2026-02-05 |
| hasattr check for Flask app vs proxy | Direct Flask app instances don't have _get_current_object, only proxies do | 2026-02-05 |
| APScheduler 3.11.2 for cron scheduling | Latest stable release with proven reliability for job scheduling | 2026-02-05 |
| First worker scheduler pattern (age==1) | Only one Gunicorn worker runs scheduler to prevent duplicate job execution | 2026-02-05 |
| scheduler_paused in ServiceConfig table | Reuses existing config table for global pause toggle, applies via first record | 2026-02-05 |
| Pre-commit hooks enforce code quality | ruff, ruff-format, black run on every commit — rejects non-compliant code | 2026-02-01 |
| Manual merge/squash to develop | User controls integration timing, GitHub Actions validate before acceptance | 2026-02-01 |
| Documentation updated at phase completion | README, tests/README, CHANGELOG, CLAUDE.md kept current after bugs resolved | 2026-02-01 |
| Create TEST_SUMMARY.md as single source of truth | Consolidates test metrics, distribution, and Phase 6.2 coverage documentation in one place | 2026-02-01 |
| Track module-level coverage improvements | Validates ROI of test generation efforts - shows 26%, 12%, 13% gains for Phase 6.2 modules | 2026-02-01 |
| Coverage baseline before test generation | Prevents writing tests for already-covered code, identifies exact gaps | 2026-02-01 |
| Prioritize tests by dependency order | TMDB service -> cache -> import -> routes ensures foundation is solid | 2026-02-01 |
| Target 90%+ coverage for Phase 6.2 modules | Customer-facing features need higher coverage to reduce regression risk | 2026-02-01 |
| Region only on supported TMDB endpoints | TMDB API limitation - trending/TV top_rated don't support region | 2026-01-31 |
| Cache keys include region suffix | Proper cache segregation when region changes | 2026-01-31 |
| Grouped preset layout (Movies then TV) | Visual organization by media type with color coding | 2026-01-31 |
| Default limit changed from 20 to 100 | More useful default for users | 2026-01-31 |
| Limit options: 25, 50, 100, 250, 500, 1000 | Broader range for different use cases | 2026-01-31 |
| Legacy 10/20 limits migrate to 25 | Closest available option in new dropdown | 2026-01-31 |
| Warning for 500+ limit selections | Inform users of performance impact | 2026-01-31 |
| Region stored as ISO 3166-1 Alpha-2 | International standard, 2-char codes | 2026-01-31 |
| Use _popular_cache for top rated | Top rated lists change slowly like popular lists (4-hour TTL) | 2026-01-31 |
| Override tag replaces default (not merges) | if/elif pattern matches expected behavior | 2026-01-31 |
| LOG_LEVEL defaults to INFO | Sensible default, DEBUG for verbose output | 2026-01-31 |
| Library logs suppressed at WARNING | Reduce noise from httpx/httpcore/urllib3/werkzeug | 2026-01-31 |
| Remove unused Tags table | Dead code cleanup, FK constraint was incorrect | 2026-01-31 |
| Sync form choices with wizard template | Prevents validation failures when editing wizard-created lists | 2026-01-31 |
| Always flash on validation failure | Users need feedback when form submission fails | 2026-01-31 |
| 2-second polling for dashboard jobs | Faster updates for small widget vs full page | 2026-01-30 |
| 50-char error truncation in dashboard | Keep table rows clean, full details on Jobs page | 2026-01-30 |
| 3-second polling interval for Jobs page | Balance between responsiveness and server load | 2026-01-30 |
| Client-side row expansion | Load job details on-demand to reduce initial page load | 2026-01-30 |
| /api/lists in lists_routes.py | Simple endpoint for filter dropdown, co-located with list management | 2026-01-30 |
| Max per_page of 50 for Jobs API | Prevents large result sets from overwhelming UI or server | 2026-01-30 |
| Clear endpoints preserve running jobs | Avoids orphaned in-progress state | 2026-01-30 |
| Rerun requires failed status | Prevents duplicate job creation for completed jobs | 2026-01-30 |
| Preserve status response format | Frontend JavaScript already polls with expected response structure | 2026-01-30 |
| Module-level SQLAlchemy event listener | Avoids app context issues with db.engine | 2026-01-25 |
| Renamed finished_at to completed_at | Consistency with terminology used throughout | 2026-01-25 |
| Cooperative timeout via threading.Event | Allows graceful cancellation, partial results preserved | 2026-01-25 |
| Lazy executor initialization | Singleton pattern avoids multiple executor instances | 2026-01-25 |
| Store JobItem records for each result | Enables detailed job history and debugging | 2026-01-25 |
| ThreadPoolExecutor for background jobs | Stdlib solution, no new dependencies, max 3 workers | 2026-01-25 |
| In-memory job tracking | Simple for MVP, jobs lost on restart is acceptable | 2026-01-25 |
| localStorage for client state | Persists across tabs and navigation | 2026-01-25 |
| 5-minute polling timeout | Long enough for imports, short enough to detect stuck | 2026-01-25 |
| 2-second polling interval | Balance between responsiveness and server load | 2026-01-25 |

## Roadmap Evolution

- 2026-02-05: Phase 9.1 inserted after Phase 9: Config & JS Deduplication (flask-slop-refactor review found ~950 lines of Radarr/Sonarr horizontal duplication in config_routes.py and config.js)
- 2026-02-05: Roadmap restructured for quality-focused finish:
  - Old Phase 8 (Service Settings Caching) → evaluated during new Phase 8
  - Old Phase 9 (User Authentication) → deferred to Phase 12 decision point
  - Old Phase 10 (pyarr Migration) → absorbed into new Phase 8
  - Old Phase 11 (Database Review) → absorbed into new Phase 9
  - New phases: Architecture & API (8), Code Quality (9), UI/UX (10), Security (11), Release (12)
  - tmdbv3api removal added alongside pyarr removal
- 2026-01-25: Roadmap reordered for optimal development flow:
  - Manual Trigger UI moved from 7->5 (quick win, endpoint exists)
  - Job Execution Framework moved from 5->6
  - Scheduler System moved from 6->7
  - Phase 9 added: User Authentication (users table exists)
  - pyarr Migration moved to Phase 10
- 2026-01-25: Phase 9 added: Migrate from pyarr to Direct API (for full feature support)
- 2026-01-23: Phase 3.1 inserted after Phase 3: Update Config Page Tags (URGENT - missed during original config page creation)
- 2026-02-01: Phase 6.3 inserted: Update Testing with Comprehensive Test Generator
- 2026-01-31: Phase 11 added: Database Review & Model Optimization (post-feature cleanup before v1.0)
- 2026-01-18: Phase 8 added: Service Settings Caching & Background Refresh

---

*State tracking started: 2026-01-12*
