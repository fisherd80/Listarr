---
phase: 08-architecture-api-consolidation
plan: 05
subsystem: api
tags: [pyarr, tmdbv3api, requests, http-client, dependencies]

# Dependency graph
requires:
  - phase: 08-02
    provides: Radarr service migrated to direct HTTP calls
  - phase: 08-03
    provides: Sonarr service migrated to direct HTTP calls
  - phase: 08-04
    provides: TMDB service migrated to direct HTTP calls
provides:
  - pyarr dependency removed from requirements.txt
  - tmdbv3api dependency removed from requirements.txt
  - Cleaner dependency manifest with only 10 core packages
  - Test documentation updated for http_session mocking
affects: [09-code-quality, 12-release]

# Tech tracking
tech-stack:
  added: []
  removed: [pyarr, tmdbv3api]
  patterns: [http_session mocking in tests]

key-files:
  created: []
  modified:
    - requirements.txt
    - tests/README.md

key-decisions:
  - "Remove pyarr and tmdbv3api now that direct HTTP calls are in place"
  - "Update test README to document http_session mocking pattern"

patterns-established:
  - "http_session mock pattern: patch service module, mock response.json()"

# Metrics
duration: 12min
completed: 2026-02-05
---

# Phase 8 Plan 5: Remove Dependencies Summary

**Removed pyarr and tmdbv3api from requirements.txt - API consolidation complete with 10 core dependencies remaining**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-05T17:42:53Z
- **Completed:** 2026-02-05T17:55:18Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Removed pyarr>=5.0.0 from requirements.txt (replaced by http_client)
- Removed tmdbv3api==1.9.0 from requirements.txt (replaced by http_client)
- Updated test README with new http_session mocking pattern
- Applied ruff formatting to 4 service modules
- Verified all 452 tests pass without removed libraries

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove dependencies from requirements.txt** - `a0e637b` (chore)
2. **Task 2: Update test mocks** - `82ef2b0` (docs)
3. **Task 3: Full test suite verification** - `dbbdbaa` (style)

## Files Created/Modified
- `requirements.txt` - Removed pyarr and tmdbv3api dependencies
- `tests/README.md` - Updated API mocking pattern documentation
- `listarr/services/crypto_utils.py` - Ruff formatting applied
- `listarr/services/http_client.py` - Ruff formatting applied
- `listarr/services/import_service.py` - Ruff formatting applied
- `listarr/services/job_executor.py` - Ruff formatting applied

## Decisions Made
- Removed both dependencies in single plan since all services migrated in prior plans (08-02, 08-03, 08-04)
- Test mocks already updated in prior plans; only documentation needed updating

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Applied ruff formatting to service modules**
- **Found during:** Task 3 (Full test suite verification)
- **Issue:** 4 service files had minor formatting inconsistencies
- **Fix:** Ran `ruff format .` to apply consistent formatting
- **Files modified:** crypto_utils.py, http_client.py, import_service.py, job_executor.py
- **Verification:** `ruff format --check .` passes, all 452 tests pass
- **Committed in:** dbbdbaa (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Formatting fix required for pre-commit hooks. No scope creep.

## Issues Encountered
None - dependencies removed cleanly, all tests already mocking http_session from prior plans.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- API consolidation complete (plans 08-01 through 08-05)
- pyarr and tmdbv3api fully removed
- All services use shared http_client with retry and connection pooling
- Ready for Phase 08-06 (Service Settings Caching evaluation)

---
*Phase: 08-architecture-api-consolidation*
*Completed: 2026-02-05*
