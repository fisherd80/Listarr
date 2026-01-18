---
phase: 03-tmdb-caching-layer
plan: 02
subsystem: api
tags: [tmdb, caching, preview, wizard]

# Dependency graph
requires:
  - phase: 03-01
    provides: tmdb_cache.py with cached wrapper functions
provides:
  - Wizard preview uses cached TMDB calls
  - Debug endpoint for cache statistics
affects: [phase-4-import-automation, any-tmdb-consumer]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cache-first pattern for external API calls"
    - "Debug endpoints for cache observability"

key-files:
  created: []
  modified:
    - listarr/routes/lists_routes.py

key-decisions:
  - "Import tmdb_cache functions directly rather than wrapping tmdb_service"
  - "Add debug endpoint for cache stats observability in development"

patterns-established:
  - "External API calls go through cache layer for rate limit protection"

issues-created: []

# Metrics
duration: 8min
completed: 2026-01-18
---

# Phase 3 Plan 2: Integrate TMDB Caching Summary

**Wizard preview now uses cached TMDB functions, reducing API calls through TTL-based caching with debug observability**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-18T17:15:00Z
- **Completed:** 2026-01-18T17:23:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Replaced direct TMDB service calls with cached versions in wizard preview
- All 6 list-fetching functions now use cache layer (trending, popular, discover)
- Added debug endpoint `/lists/debug/cache-stats` for cache observability
- All 363 existing tests pass without modification

## Task Commits

Each task was committed atomically:

1. **Task 1: Update wizard preview to use cached TMDB functions** - `ffa93c4` (feat)
2. **Task 3: Add debug endpoint for cache statistics** - `3333f4c` (feat)

Note: Task 2 was verification only (pytest run), no code changes needed.

## Files Created/Modified

- `listarr/routes/lists_routes.py` - Changed imports from tmdb_service to tmdb_cache, updated all function calls in wizard_preview(), added debug cache stats endpoint

## Decisions Made

- **Import strategy:** Import cached functions directly from tmdb_cache rather than creating a wrapper. This is cleaner and the function signatures are identical.
- **Debug endpoint:** Added `/lists/debug/cache-stats` to allow verification of cache effectiveness during development. Returns JSON with cache sizes, max sizes, and TTLs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tests passed without requiring mock updates because the tests test tmdb_service directly (which still exists and is called by tmdb_cache internally).

## Next Phase Readiness

Phase 3 (TMDB Caching Layer) is now complete:
- Cached wrapper functions created in 03-01
- Wizard preview integrated with cache in 03-02
- Cache hit/miss logging available at DEBUG level
- Cache stats endpoint available for verification

Ready to proceed to Phase 4 (Import Automation Engine).

---
*Phase: 03-tmdb-caching-layer*
*Completed: 2026-01-18*
