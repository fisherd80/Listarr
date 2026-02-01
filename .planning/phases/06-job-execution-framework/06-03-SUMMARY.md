---
phase: "06"
plan: "03"
subsystem: job-execution
tags: [lists, routes, job-executor, migration]
depends_on: ["06-01", "06-02"]
provides: ["database-backed-job-tracking", "lists-routes-migration"]
affects: ["06-05", "06-06"]
tech-stack:
  added: []
  patterns: ["service-layer-integration"]
key-files:
  modified:
    - listarr/routes/lists_routes.py
  created:
    - tests/routes/test_lists_routes.py
decisions:
  - id: preserve-response-format
    choice: "Maintained backward-compatible response format for frontend"
    rationale: "Frontend JavaScript already polls with expected response structure"
metrics:
  duration: "~15 minutes"
  completed: "2026-01-30"
---

# Phase 06 Plan 03: Lists Routes Migration Summary

Migrated lists_routes.py from in-memory job tracking to database-backed job_executor service with full test coverage.

## What Was Built

### Lists Routes Migration

**Removed in-memory tracking:**
- `_running_jobs = {}` dictionary
- `_jobs_lock = threading.Lock()`
- `_executor = None` and `get_executor()` function
- `_run_import_job()` helper function
- `from concurrent.futures import ThreadPoolExecutor` import

**Added job_executor integration:**
- Import: `from listarr.services.job_executor import submit_job, is_list_running, get_job_status`
- `run_list_import()` now uses `submit_job()` with proper error handling
- `get_list_status()` now reads from Job table via `get_job_status()`

### Response Format Compatibility

Status endpoint maintains backward-compatible response:
```json
{
  "list_id": 1,
  "status": "running|completed|failed|idle",
  "last_run_at": "2026-01-30T10:00:00+00:00",
  "result": {
    "summary": {
      "total": 10,
      "added_count": 5,
      "skipped_count": 3,
      "failed_count": 2
    }
  },
  "error": "Error message if failed"
}
```

### Test Coverage

Created `tests/routes/test_lists_routes.py` with 14 tests:

**POST /lists/<id>/run tests (6):**
- Returns 404 for missing list
- Returns 400 for inactive list
- Returns 400 when job already running
- Returns 202 on successful submission
- Handles ValueError from submit_job
- Handles unexpected exceptions

**GET /lists/<id>/status tests (8):**
- Returns 404 for missing list
- Returns idle when no jobs exist
- Returns running when job in progress
- Returns completed with result summary
- Returns failed with error message
- Includes last_run_at timestamp
- Returns most recent job status
- Maps unknown status to idle

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 4f3c840 | feat | Migrate lists routes to database-backed job executor |
| 97747bb | test | Add unit tests for lists routes job endpoints |

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| listarr/routes/lists_routes.py | Modified | -119, +54 |
| tests/routes/test_lists_routes.py | Created | +313 |

## Verification

All verification criteria met:
- [x] lists_routes.py no longer has `_running_jobs`, `_jobs_lock`, or `get_executor()`
- [x] Run endpoint creates Job record in database via `submit_job()`
- [x] Status endpoint reads from Job table via `get_job_status()`
- [x] Frontend polling still works (same response format)
- [x] All 415 tests pass (379 original + 14 new + 22 existing)

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Prerequisites satisfied for Wave 2 completion:**
- 06-03 complete: Lists routes migrated to job_executor
- 06-04 already executed: Jobs API endpoints available

**Ready for Wave 3:**
- Jobs page UI (06-05)
- Dashboard widget (06-06)
