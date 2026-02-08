# Roadmap

**Project:** Listarr
**Milestone:** v1.0 - Automated Media Discovery
**Created:** 2026-01-12

## Objective

Build automated media discovery and import that just works - fresh content flows into Radarr/Sonarr automatically based on TMDB lists, running reliably 24/7 without intervention.

## Phases

### Phase 1: List Management System

**Goal:** Create UI and backend for managing TMDB lists with full CRUD operations

**Deliverable:** Users can create, view, edit, delete, and enable/disable lists through the web interface

**Verification:**
- Create a new TMDB trending list through the UI
- Edit the list configuration
- Disable and re-enable the list
- Delete the list
- All operations persist correctly in the database

---

### Phase 2: List Creation Wizard

**Goal:** Replace basic list form with multi-step wizard featuring presets, discovery filters, per-list import settings, and live TMDB preview

**Deliverable:** Users can create lists through a guided 4-step wizard with preset templates, see live preview of TMDB results, and configure per-list import settings that override service defaults

**Wizard Steps:**
1. **Type** - Movies (->Radarr) or TV Shows (->Sonarr)
2. **Filters** - Genre, year range, min rating with live TMDB preview
3. **Import Settings** - Quality profile, root folder, tags, monitored, search on add (pre-filled from service defaults, all editable)
4. **Schedule** - Run frequency

**Presets:** Trending Movies, Trending TV, Popular Movies, Popular TV (populate wizard for review)

**Verification:**
- Create a list using "Trending Movies" preset, verify wizard pre-populates correctly
- Create a custom discovery list with genre + year filters, verify live preview shows matching TMDB results
- Override import settings on a list, verify they differ from service defaults
- Create list without overriding import settings, verify it uses service defaults
- Edit an existing list through the wizard, verify all fields load correctly

---

### Phase 3: TMDB Caching Layer (Complete)

**Goal:** Implement smart caching to respect TMDB API rate limits and improve performance

**Deliverable:** TMDB API responses are cached with appropriate TTLs, preventing rate limit violations

**Status:** Complete (2026-01-18) - 2/2 plans executed
- 03-01: TMDB cache service with TTL-based caching
- 03-02: Integrated caching into wizard preview

**Verification:**
- Fetch the same list twice within cache window and verify only one API call is made
- Wait for cache expiration and verify fresh data is fetched
- Check logs to confirm cache hit/miss behavior
- Verify rate limiting protection prevents API overuse

---

### Phase 3.1: Update Config Page Tags (Complete)

**Goal:** Add tag storage to the Config page with create-if-missing pattern for Radarr/Sonarr tags

**Deliverable:** Config page allows users to configure and persist tags for both Radarr and Sonarr services using text input (not dropdown)

**Status:** Complete (2026-01-24) - 1/1 plans executed
- 03.1-01: Tag storage with create-if-missing pattern

**Verification:**
- Tags can be configured on the Config page for Radarr
- Tags can be configured on the Config page for Sonarr
- Tag selections persist correctly in the database
- Tags are created in Radarr/Sonarr if they don't exist

---

### Phase 4: Import Automation Engine

**Goal:** Build reliable import system that sends TMDB items to Radarr/Sonarr with proper error handling

**Deliverable:** System can import movies to Radarr and TV shows to Sonarr with configured quality profiles and root folders, handling errors gracefully

**Plans:** 3 plans in 2 waves

Plans:
- [x] 04-01-PLAN.md — TVDB translation + Radarr import methods
- [x] 04-02-PLAN.md — Sonarr import methods + ImportResult dataclass
- [ ] 04-03-PLAN.md — Import orchestration service + test endpoint

**Verification:**
- Import a movie to Radarr and verify it appears with correct quality profile
- Import a TV show to Sonarr and verify it appears with correct settings
- Test import of already-existing item and verify graceful handling
- Test import with invalid settings and verify error reporting
- Check error logs for proper error capture

---

### Phase 5: Manual Trigger UI (Complete)

**Goal:** Add manual trigger capability to run any list on-demand from the UI

**Deliverable:** Users can click a button to immediately execute any list import job using the existing `/lists/<id>/run` endpoint

**Status:** Complete (2026-01-25) - 2/2 plans executed + FIX
- 05-01: Run button UI with toast feedback
- 05-02: Async endpoint + localStorage polling
- FIX: Result toast reads correct summary fields

**Verification:**
- Click "Run Now" button on a list and verify job executes immediately
- Verify UI shows job status feedback (running -> completed)
- Check that results are displayed to the user
- Verify UI prevents duplicate triggers while job is running

---

### Phase 6: Job Execution Framework (Complete)

**Goal:** Create background job processing system with execution tracking and history

**Deliverable:** Jobs can be queued, executed, tracked, and their history (success/failure) is recorded and displayed

**Status:** Complete (2026-01-30) - 6/6 plans executed
- 06-01: Enhanced Job model + WAL mode + tenacity
- 06-02: Job executor service with timeout/retry
- 06-03: Migrated lists_routes to job_executor
- 06-04: Jobs API endpoints (7 endpoints)
- 06-05: Jobs page UI (paginated table, filters, expandable rows)
- 06-06: Dashboard recent jobs widget

**Verification:**
- Queue a list import job and verify it executes
- View job execution history in the dashboard
- Verify failed jobs are logged with error details
- Check that job status updates correctly (pending -> running -> completed/failed)
- Confirm job history persists across application restarts

---

### Phase 6.1: Bug Fixes (Complete)

**Goal:** Fix bugs discovered during manual testing of Phases 1-6

**Deliverable:** All identified bugs resolved, application stable for continued development

**Status:** Complete (2026-01-31) - 2/2 plans executed
- 06.1-01: Tag override logic + logging configuration
- 06.1-02: UI feedback bugs verification and fix

**Verification:**
- Create list with override tag, verify only override tag applied (not default + override)
- Set LOG_LEVEL environment variable, verify logs respect it
- Run a list, verify status shows "Running" throughout execution
- Run multiple lists, verify result toasts appear consistently
- Edit a list and save, verify redirect to lists page with success notification

---

### Phase 6.2: List Enhancements (Complete)

**Goal:** Enhance list creation with additional presets, expanded options, and region filtering

**Deliverable:** Wizard supports Top/Popular/Trending presets, larger list limits, and TMDB region filtering

**Status:** Complete (2026-01-31) - 3/3 plans executed
- 06.2-01: Top Rated presets backend (TMDB service, cache, routes, import)
- 06.2-02: Limit options update and TMDB region setting
- 06.2-03: Preset UI layout and region integration

**Verification:**
- Create list using "Top Movies" preset, verify TMDB Top Rated endpoint used
- Verify wizard UI displays all 3 preset categories clearly
- Create new list, verify default limit is 100
- Select MAX (1000) limit, verify warning text appears
- Set region in Settings, verify TMDB API calls include region parameter
- Create list with region set, verify results are region-appropriate

---

### Phase 6.3: Update Testing with Comprehensive Test Generator (Complete)

**Goal:** Enhance test coverage using pytest-cov analysis and systematic test generation to ensure robust testing across all Phase 6.2 features

**Deliverable:** Updated and expanded test suite with comprehensive coverage for Phase 6.2 functionality (top_rated presets, region filtering, cache keys)

**Status:** Complete (2026-02-01) - 4/4 plans executed
- 06.3-01: Coverage baseline (52%) and gap analysis
- 06.3-02: TMDB top_rated tests (15 tests added)
- 06.3-03: Region filtering and import tests (14 tests added)
- 06.3-04: Final coverage verification (56%, +4% improvement)

**Results:**
- Test count: 415 -> 444 (+29 tests)
- Overall coverage: 52% -> 56%
- tmdb_cache.py: 14% -> 40% (+26%)
- tmdb_service.py: 71% -> 83% (+12%)

**Verification:**
- Run full test suite and verify all tests pass (430+)
- Check test coverage metrics have improved from baseline
- Verify Phase 6.2 critical paths have dedicated test coverage
- Confirm edge cases are tested (region filtering, cache keys, error handling)

---

### Phase 7: Scheduler System (Complete)

**Goal:** Implement cron-based scheduler for automated list refresh on schedule

**Deliverable:** Lists can be configured with cron schedules and execute automatically without manual intervention

**Status:** Complete (2026-02-05) - 6/6 plans executed
- 07-01: Scheduler dependencies and Gunicorn worker config
- 07-02: Scheduler service (APScheduler wrapper)
- 07-03: Schedule page (routes + UI)
- 07-04: Lists/Wizard scheduler integration
- 07-05: Dashboard upcoming widget
- 07-06: Documentation updates

**Verification:**
- Configure a list to run every 5 minutes
- Wait and verify the job executes automatically at the scheduled time
- Check job history shows scheduled executions
- Disable the list and verify scheduled jobs stop
- Re-enable and verify scheduling resumes

---

### Phase 8: Architecture & API Consolidation (Complete)

**Goal:** Remove third-party API wrapper libraries (pyarr, tmdbv3api), consolidate to direct HTTP calls, and review architecture for over-engineering

**Deliverable:** All external API interactions use direct `requests` calls with shared HTTP sessions, reducing dependencies and improving consistency

**Status:** Complete (2026-02-05) - 6/6 plans executed
- 08-01: HTTP Client module (shared session, retry, timeout, connection pooling)
- 08-02: Radarr direct API (replaced pyarr with http_session)
- 08-03: Sonarr direct API (replaced pyarr with http_session)
- 08-04: TMDB direct API (replaced tmdbv3api with http_session)
- 08-05: Dependency cleanup (removed pyarr, tmdbv3api from requirements.txt)
- 08-06: Architecture documentation (6 concerns documented for Phase 9)

**Verification:**
- All Radarr functionality works (test connection, profiles, folders, tags, add movie)
- All Sonarr functionality works (test connection, profiles, folders, tags, add series)
- All TMDB functionality works (trending, popular, top_rated, discover, details)
- Dependency count reduced (pyarr, tmdbv3api removed from requirements.txt)
- All existing tests pass with new implementations (452 tests)
- Architecture concerns documented for Phase 9

---

### Phase 9: Code Quality & Refactoring

**Goal:** Address technical debt, remove redundant code, optimize database models, and simplify abstractions

**Deliverable:** Cleaner codebase with reduced duplication, optimized queries, and simplified patterns

**Plans:** 6 plans in 2 waves

Plans:
- [ ] 09-01-PLAN.md — Consolidate format_relative_time() to utils module
- [ ] 09-02-PLAN.md — Fix N+1 query in dashboard recent jobs
- [ ] 09-03-PLAN.md — Consolidate dashboard stats calculation functions
- [ ] 09-04-PLAN.md — Add HTTP status checks to JavaScript fetch calls
- [ ] 09-05-PLAN.md — Create shared arr_service.py for Radarr/Sonarr common code
- [ ] 09-06-PLAN.md — Consolidate config route status functions + clean List model

**Scope:**
- Database model review and optimization
- Remove redundant/dead code identified in Phase 8
- Fix N+1 query patterns (e.g., dashboard recent jobs)
- Consolidate duplicate code between Radarr/Sonarr services
- Remove hallucinated patterns or over-abstractions
- Simplify oversized modules (e.g., config_routes.py at 592 lines)

**Verification:**
- No dead code or unused imports remain
- Database queries are efficient (no N+1 patterns)
- Code duplication reduced measurably
- All tests pass after refactoring
- Module sizes are reasonable (< 400 lines preferred)

---

### Phase 9.1: Config & JS Deduplication (Complete)

**Goal:** Eliminate Radarr/Sonarr horizontal duplication in config routes and JavaScript by parameterizing service-specific code

**Depends on:** Phase 9
**Source:** 09-SLOP-REVIEW.md (flask-slop-refactor agent findings, verified with line numbers)

**Deliverable:** config_routes.py reduced from 897 to 404 lines, config.js reduced from 746 to 322 lines (~920 lines removed total)

**Status:** Complete (2026-02-07) - 3/3 plans executed
- 09.1-01: Parameterize config_routes.py (8 duplicate routes to 4, extract helpers)
- 09.1-02: Update test mock paths for parameterized routes (115 tests updated)
- 09.1-03: Consolidate config.js + extract shared utils.js

Plans:
- [x] 09.1-01-PLAN.md — Parameterize config_routes.py (8 duplicate routes to 4, extract helpers, clean docstrings)
- [x] 09.1-02-PLAN.md — Update test_config_routes.py mock paths and function references
- [x] 09.1-03-PLAN.md — Consolidate config.js fetch functions + extract shared utils.js

**Scope (from 09-SLOP-REVIEW.md):**

| # | Finding | Priority | Lines Saved |
|---|---------|----------|------------:|
| 1 | Parameterize 8 duplicate config routes with `<service>` | HIGH | ~550 |
| 2 | Consolidate duplicate JS fetch functions into parameterized helpers | HIGH | ~400 |
| 3 | Delete redundant wrapper functions (lines 90-97) | MEDIUM | 7 |
| 4 | Extract shared JS utilities (formatTimestamp, generateStatusHTML) | MEDIUM | ~40 |
| 5 | Extract `_save_service_config()` from 177-line config_page() | MEDIUM | ~100 |
| 6 | Simplify verbose AI-generated docstrings | LOW | ~30 |
| 7 | Remove obvious comments | LOW | ~5 |

**Verification:**
- config_routes.py < 400 lines
- config.js < 400 lines
- No duplicate Radarr/Sonarr fetch functions remain
- No wrapper functions that only delegate to another function
- All 453 tests pass after refactoring
- Settings page test connection works for both services
- Config page quality profiles, root folders, import settings all load correctly

---

### Phase 10: UI/UX Simplification

**Goal:** Simplify Jinja templates, status indicators, warnings, and frontend state management

**Deliverable:** Cleaner, more consistent UI with simplified template logic and better user feedback

**Plans:** 5 plans in 3 waves

Plans:
- [x] 10-01-PLAN.md — Jinja2 macros for status badges, loading spinners, empty states
- [x] 10-02-PLAN.md — JavaScript utility consolidation into shared utils.js
- [x] 10-03-PLAN.md — Dashboard.js parameterization and cleanup
- [x] 10-04-PLAN.md — Jobs.js, schedule.js, lists.js cleanup and performance fixes
- [x] 10-05-PLAN.md — Config.html form macro and full verification

**Scope:**
- Audit Jinja templates for complexity and duplication
- Standardize status bars and indicators across pages
- Review and consolidate warning/error messaging patterns
- Simplify template state management (reduce JavaScript complexity)
- Ensure consistent styling and component patterns

**Verification:**
- Templates use consistent patterns and partials
- Status indicators behave consistently across pages
- Warning/error messages follow single pattern
- JavaScript state management is straightforward
- UI responds correctly to all states (loading, success, error, empty)

---

### Phase 10.1: UI Review Fixes (INSERTED)

**Goal:** Address remaining UI/UX inconsistencies identified by flask-ui-state-reviewer audit of Phase 10

**Depends on:** Phase 10
**Source:** 10-REVIEW-REPORT.md (flask-ui-state-reviewer agent findings)

**Deliverable:** Consistent status indicators, error feedback patterns, and service badge rendering across all pages

**Plans:** 3 plans in 1 wave

Plans:
- [x] 10.1-01-PLAN.md — Replace alert() with showToast(), add generateServiceBadge() utility, fix jobs dropdown heights
- [x] 10.1-02-PLAN.md — Add error_state() macro, simplify lists.html status badges, standardize wizard error states
- [x] 10.1-03-PLAN.md — Extract wizard preset metadata to Python PRESET_METADATA constant

**Scope (from 10-REVIEW-REPORT.md):**

| # | Finding | Priority | Effort |
|---|---------|----------|--------|
| 1 | Replace 4 alert() calls with showToast() in config.js | HIGH | 30 min |
| 2 | Expand status_badge() macro to lists.html inline badges | HIGH | 1 hour |
| 3 | Add error_state() macro for consistent error boundaries | MEDIUM | 1 hour |
| 4 | Add generateServiceBadge() JS utility for color consistency | MEDIUM | 30 min |
| 5 | Wizard preset metadata extraction to Python constants | MEDIUM | 2 hours |
| 6 | Jobs page filter dropdown height fix (cosmetic) | LOW | 15 min |

**Excluded (low value / high effort):**
- Schedule page UI state model (4 hours, triple-render works acceptably)
- Wizard server-side validation (6 hours, not needed for single-user app)
- Dashboard UI state model (3 hours, current JS state management is appropriate)

**Verification:**
- No alert() dialogs remain in JavaScript (all use showToast())
- All server-rendered status badges use status_badge() macro
- error_state() macro exists and is used for API failure conditions
- Radarr/Sonarr badge colors consistent across server and client rendering
- Wizard template reduced by ~100 lines via preset metadata extraction
- All 453 tests pass after changes

---

### Phase 10.2: Schedule Bug Fixes (INSERTED)

**Goal:** Fix two scheduler/job execution bugs: (1) scheduled jobs run without validating target service is reachable, causing massive error cascades; (2) static 10-minute wall-clock timeout incorrectly marks completed jobs as failed instead of using activity-based idle detection

**Depends on:** Phase 10.1
**Source:** Debug investigation `.planning/debug/schedule-health-and-timeout.md`

**Deliverable:** Robust scheduled job execution with pre-flight service health checks and activity-based timeout that only triggers on idle (no progress), not on large jobs that are actively processing items

**Plans:** 2 plans in 1 wave

Plans:
- [x] 10.2-01-PLAN.md — Pre-flight service health check in scheduler
- [x] 10.2-02-PLAN.md — Activity-based idle timeout replacing fixed wall-clock timer

**Verification:**
- Scheduled jobs validate target service is reachable before submitting job
- Jobs that take >10 minutes with active progress complete successfully (not marked as timed out)
- Jobs that stall (no progress for N seconds) are correctly timed out
- Import loops check stop_event for early termination when timeout triggers
- All existing tests pass after changes

---

### Phase 10.3: Import & Schedule Bug Fixes (Complete)

**Goal:** Fix three issues found during testing: (1) Radarr add_movie 400 Bad Request due to unsafe payload construction, (2) missing exclusion/blocklist validation before import, (3) no dedicated schedule edit form on schedule page

**Depends on:** Phase 10.2
**Source:** Debug investigations `.planning/debug/import-400-and-blocklist.md` and `.planning/debug/resolved/schedule-edit-and-nextrun.md`

**Deliverable:** Movies add successfully to Radarr with clean payload, import skips items on exclusion lists, schedule page has dedicated edit form with granular controls (cron input, day/hour selectors)

**Status:** Complete (2026-02-08) - 2/2 plans executed
- 10.3-01: Fix add_movie/add_series payload, error logging, and exclusion list validation
- 10.3-02: Schedule edit modal and weekly cron preset fix

Plans:
- [x] 10.3-01-PLAN.md -- Fix add_movie/add_series payload, error logging, and exclusion list validation
- [x] 10.3-02-PLAN.md -- Schedule edit modal and weekly cron preset fix

**Verification:**
- Movies add to Radarr without 400 errors (clean payload with explicit field mapping)
- Radarr error responses logged before raise_for_status
- Items on Radarr exclusion list skipped with reason "on_exclusion_list"
- Items on Sonarr exclusion list skipped with reason "on_exclusion_list"
- Schedule page has edit button that opens dedicated schedule edit form
- Schedule edit form supports native cron input, weekly day/hour, daily hour
- All existing tests pass after changes (476 total)

---

### Phase 10.4: Bulk Import API (INSERTED)

**Goal:** Replace sequential single-item POST `/api/v3/movie` and `/api/v3/series` calls with bulk import endpoints (`POST /api/v3/movie/import` for Radarr, equivalent for Sonarr) to dramatically improve import speed and reliability

**Depends on:** Phase 10.3
**Source:** Kometa comparison analysis — Kometa uses arrapi's `add_multiple_movies()` which calls bulk `POST /api/v3/movie/import` endpoint, batching up to 100 items per request. Listarr currently adds items one at a time with 200ms delays.

**Deliverable:** Import service uses bulk API endpoints for both Radarr and Sonarr, sending batches of items in single API calls. Results are categorized (added/exists/invalid/excluded) from the bulk response.

**Plans:** 2 plans in 2 waves

Plans:
- [ ] 10.4-01-PLAN.md -- Bulk service functions + batch-based import rewrite
- [ ] 10.4-02-PLAN.md -- Tests for bulk functions and batch import flow

**Scope:**
- Replace `add_movie()` individual POST with bulk `POST /api/v3/movie/import` in radarr_service
- Replace `add_series()` individual POST with bulk Sonarr endpoint in sonarr_service
- Update import_service to batch items and parse categorized bulk responses
- Maintain existing pre-flight duplicate/exclusion checks as optimization layer
- Handle partial failures within bulk responses gracefully

**Verification:**
- Radarr import uses bulk endpoint (single API call for multiple movies)
- Sonarr import uses bulk endpoint (single API call for multiple series)
- Bulk response correctly categorizes: added, already exists, invalid, excluded
- Import speed significantly improved (no 200ms per-item delay)
- Existing pre-flight checks still skip known duplicates before bulk call
- All existing tests pass after changes

---

### Phase 10.5: UI Performance & State Consolidation (Complete)

**Goal:** Address critical UI/UX issues identified by flask-ui-state-reviewer: timeout handling for external APIs, config page loading optimization, date formatter consolidation, status badge deduplication, and loading skeleton states

**Depends on:** Phase 10.4
**Source:** flask-ui-state-reviewer audit of phases 10-10.4

**Status:** Complete (2026-02-08) - 4/4 plans executed

**Deliverable:** Responsive UI with timeout handling (no 30s+ hangs), optimized loading (parallel API calls + skeletons), consolidated utilities (single date formatter, backend-rendered badges)

**Plans:** 4 plans in 3 waves

Plans:
- [x] 10.5-01-PLAN.md — fetchWithTimeout + consolidate formatTimestamp in utils.js
- [x] 10.5-02-PLAN.md — Timeout handling for wizard.js and config.js
- [x] 10.5-03-PLAN.md — Server-rendered status badges for schedule, jobs badge consolidation
- [x] 10.5-04-PLAN.md — Skeleton loading states for config and dashboard

**Scope:**

| # | Issue | Priority | Effort |
|---|-------|----------|--------|
| 1 | Add timeout handling for external APIs (wizard, config) | CRITICAL | 4h |
| 2 | Optimize config page loading (parallel calls + skeleton) | CRITICAL | 3h |
| 3 | Consolidate date formatters into single unified function | HIGH | 2h |
| 4 | Eliminate status badge duplication (backend-rendered HTML) | HIGH | 4h |
| 5 | Backend-derived UI state for schedule page status | MEDIUM | 6h |
| 6 | Add loading skeletons throughout (dashboard, config, wizard) | MEDIUM | 3h |

**Verification:**
- Wizard Step 3 and config page API calls have 10-second timeout with error handling
- Config import settings show loading skeleton, load in <3 seconds
- Single formatTimestamp() function replaces 3 separate formatters
- Status badges rendered server-side via macros, no JS badge rendering
- Schedule page uses backend-derived ScheduleUIState
- Loading skeletons appear during API calls (dashboard, config, wizard)
- All existing tests pass after changes

---

### Phase 11: Security Hardening

**Goal:** Fix Flask and Docker security foot-guns, validate inputs, secure configuration

**Deliverable:** Production-ready security posture with hardened Flask config and secure Docker deployment

**Scope:**
- Flask security configuration (SECRET_KEY, session config, CSRF)
- Docker security (non-root user, read-only filesystem where possible)
- Input validation audit (all user inputs, API parameters)
- Bare exception clause cleanup (mask errors -> specific handling)
- HTTP status code validation in frontend AJAX calls
- Environment variable security (secrets not logged, .env handling)

**Verification:**
- Flask runs with secure production configuration
- Docker container runs as non-root user
- All user inputs are validated before use
- No bare `except:` clauses remain
- Frontend handles HTTP errors appropriately
- No secrets exposed in logs or error messages

---

### Phase 12: Release Readiness

**Goal:** Final audit and polish before v1.0 release

**Deliverable:** Production-ready application with complete documentation and deployment confidence

**Scope:**
- User authentication decision (implement for v1.0 or defer to v1.1)
- Final test suite run and coverage review
- Documentation audit (README, CHANGELOG, deployment guide)
- Docker Compose production configuration
- Version tagging and release notes preparation
- Sanity check: full user workflow end-to-end

**Verification:**
- All tests pass (target: 95%+ pass rate)
- Documentation is accurate and complete
- Docker deployment works from fresh clone
- Full workflow succeeds: configure services -> create list -> schedule -> verify import
- No critical bugs or security issues remain
- Ready for v1.0.0 tag

---

## Milestone Complete When

All phases delivered and verified:
- List management UI fully functional
- List creation wizard with presets, filters, import settings, and live preview
- TMDB caching respects rate limits
- Import automation reliably sends items to Radarr/Sonarr
- Manual triggers allow on-demand execution from UI
- Job execution framework tracks all operations
- Bug fixes from manual testing resolved
- List enhancements (Top preset, expanded limits, region filtering) complete
- Scheduler runs lists automatically on cron schedules
- Direct API calls replace pyarr and tmdbv3api (reduced dependencies)
- Architecture reviewed and simplified
- Code quality improved (no dead code, optimized queries)
- UI/UX consistent and simplified
- Security hardened for production
- Release-ready with complete documentation

**Success criteria:** User can configure a trending movies list, schedule it to run daily, and verify that new movies automatically appear in Radarr without any manual intervention.

---

## Documentation Standard

**Effective from Phase 6 onwards:** At the completion of each phase, update:
- **README.md** - Reflect current features and capabilities
- **CHANGELOG.md** - Document changes made in the phase

This ensures documentation stays current with development progress.

---

*Roadmap created: 2026-01-12*
*Last updated: 2026-02-08*
*Phases: 12 (8 complete + 8 sub-phases, 4 remaining)*
*Depth: Standard (3-5 plans per phase)*
*Restructured: 2026-02-05 - Consolidated feature phases into quality/release phases*
