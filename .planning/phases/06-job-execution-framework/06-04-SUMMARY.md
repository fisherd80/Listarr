---
phase: 06-job-execution-framework
plan: 04
subsystem: api
tags: [flask, sqlalchemy, pagination, jobs-api, rest]

# Dependency graph
requires:
  - phase: 06-01
    provides: Job and JobItem models with to_dict() methods
provides:
  - Jobs API with paginated listing, filtering, detail view
  - Recent jobs endpoint for dashboard widget
  - Job rerun capability for failed jobs
  - Job history clearing (global and per-list)
  - Running jobs polling endpoint
affects: [06-05, 06-06, dashboard-widget, jobs-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Paginated API responses with total, pages, current_page"
    - "Query parameter filtering (list_id, status)"
    - "CSRF exempt for API POST endpoints"

key-files:
  created:
    - tests/routes/test_jobs_routes.py
  modified:
    - listarr/routes/jobs_routes.py

key-decisions:
  - "Max 50 per_page enforced to prevent large result sets"
  - "Clear endpoints preserve running jobs"
  - "Rerun only allowed for failed jobs"
  - "target_service included in recent jobs for display"

patterns-established:
  - "API pagination: page/per_page params, max limit enforced"
  - "Job API filters: list_id and status query params"
  - "CSRF exempt for API mutation endpoints"

# Metrics
duration: 24min
completed: 2026-01-30
---

# Phase 6 Plan 04: Jobs API Endpoints Summary

**Full Jobs API with paginated listing, filtering, detail view, rerun, and clear capabilities**

## Performance

- **Duration:** 24 min
- **Started:** 2026-01-30T10:10:03Z
- **Completed:** 2026-01-30T10:33:56Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Implemented complete Jobs API with 7 endpoints
- Added pagination with configurable page size (max 50)
- Built filtering by list_id and status
- Created recent jobs endpoint for dashboard widget
- Enabled job rerun for failed jobs with validation
- Added job history clearing with running job protection
- Created 22 comprehensive unit tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement Jobs API endpoints** - `1057647` (feat)
2. **Task 2: Add unit tests for Jobs API** - `7410dbd` (test)

## Files Created/Modified

- `listarr/routes/jobs_routes.py` - Full Jobs API implementation (224 lines)
  - GET /api/jobs - Paginated job list with filters
  - GET /api/jobs/recent - 5 most recent for dashboard
  - GET /api/jobs/<id> - Job detail with items
  - POST /api/jobs/<id>/rerun - Rerun failed job
  - POST /api/jobs/clear - Clear all non-running jobs
  - POST /api/jobs/clear/<list_id> - Clear per-list jobs
  - GET /api/jobs/running - Running jobs for polling

- `tests/routes/test_jobs_routes.py` - 22 unit tests covering all endpoints
  - TestGetJobs: pagination, status/list_id filters, per_page limit
  - TestGetRecentJobs: max 5 jobs, target_service inclusion
  - TestGetJobDetail: 404 handling, items array
  - TestRerunJob: failed-only, list validation, inactive rejection
  - TestClearJobs: preserve running, per-list clearing
  - TestGetRunningJobs: metadata in response

## Decisions Made

- **Max per_page of 50:** Prevents large result sets from overwhelming the UI or server
- **Clear preserves running jobs:** Avoids orphaned in-progress state
- **Rerun requires failed status:** Prevents duplicate job creation for completed jobs
- **target_service in recent jobs:** Dashboard widget needs service for icon display

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **List model field names:** Tests initially used wrong field names (media_type, source_type instead of tmdb_list_type, filters_json). Fixed by checking actual List model schema.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Jobs API ready for UI consumption (06-05: Jobs page)
- Recent jobs endpoint ready for dashboard widget (06-06)
- All 415 tests passing

---
*Phase: 06-job-execution-framework*
*Completed: 2026-01-30*
