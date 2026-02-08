# Phase 10 Plan 03: Dashboard.js Parameterization and Cleanup Summary

**One-liner:** Parameterized Radarr/Sonarr card functions, removed duplicate utilities, extracted constants, added visibility-aware polling

## Plan Metadata

- **Phase:** 10 - UI/UX Simplification
- **Plan:** 03 of 5
- **Type:** refactor
- **Subsystem:** frontend/dashboard
- **Tags:** javascript, refactor, deduplication, parameterization

## What Was Done

### Task 1: Remove duplicate utility functions
Removed three functions from dashboard.js that are already provided globally by utils.js (loaded via base.html):
- `escapeHtml()` (6 lines) - XSS prevention helper
- `formatDate()` (35 lines) - Relative time formatting
- `capitalize()` (4 lines) - String capitalization

All call sites in dashboard.js continue to work via the global utils.js versions.

### Task 2: Parameterize service card functions and add visibility polling
1. **Replaced `showRadarrLoadingState()` + `showSonarrLoadingState()`** with single `showServiceLoadingState(service)` driven by `SERVICE_CONFIG` data object
2. **Replaced `updateRadarrCard(data)` + `updateSonarrCard(data)`** with single `updateServiceCard(data, service)` driven by same config
3. **Extracted `OFFLINE_DATA` constant** - replaces 4+ inline error fallback objects (each ~7 lines)
4. **Extracted `SERVICE_CONFIG` constant** - data-driven element IDs and stat key mappings for both services
5. **Added visibility check to jobs polling** - `if (document.visibilityState !== "visible") return;` prevents unnecessary API calls when tab is hidden
6. **Removed redundant outer try/catch** in `initDashboard()` - the .catch() on the promise chain already handles errors
7. **Consolidated JSDoc comments** - multi-line JSDoc blocks reduced to single-line format

## Line Count

| Metric | Lines |
|--------|-------|
| Before (original) | 876 |
| After Task 1 (duplicates removed) | 813 |
| After Task 2 (parameterized + cleaned) | 539 |
| **Total reduction** | **337 lines (38%)** |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | bd96114 | Remove duplicate utility functions from dashboard.js |
| 2 | b9080c6 | Parameterize service card functions and add visibility polling |

## Key Files

| File | Action | Description |
|------|--------|-------------|
| `listarr/static/js/dashboard.js` | Modified | Reduced from 876 to 539 lines |

## Functions Removed (6 total)

| Function | Reason |
|----------|--------|
| `escapeHtml()` | Duplicate of utils.js global |
| `formatDate()` | Duplicate of utils.js global |
| `capitalize()` | Duplicate of utils.js global |
| `showRadarrLoadingState()` | Replaced by `showServiceLoadingState(service)` |
| `showSonarrLoadingState()` | Replaced by `showServiceLoadingState(service)` |
| `updateRadarrCard(data)` | Replaced by `updateServiceCard(data, service)` |
| `updateSonarrCard(data)` | Replaced by `updateServiceCard(data, service)` |

## Functions Added (2 total)

| Function | Purpose |
|----------|---------|
| `showServiceLoadingState(service)` | Parameterized loading state for radarr/sonarr |
| `updateServiceCard(data, service)` | Parameterized card update for radarr/sonarr |

## Constants Added (2 total)

| Constant | Purpose |
|----------|---------|
| `OFFLINE_DATA` | Shared error fallback object (was repeated 4+ times inline) |
| `SERVICE_CONFIG` | Data-driven element IDs and stat mappings for both services |

## Verification

- All 453 tests pass (no regressions)
- dashboard.js: 539 lines (under 550 target)
- No duplicate escapeHtml, formatDate, capitalize functions
- No duplicate showRadarrLoadingState/showSonarrLoadingState
- No duplicate updateRadarrCard/updateSonarrCard
- Jobs polling includes visibility check
- All error handlers use OFFLINE_DATA constant

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Extract SERVICE_CONFIG as top-level constant | Data-driven approach eliminates need for per-service branches in loading and update functions |
| Single-line JSDoc comments | Reduces visual noise; full parameter docs unnecessary for internal dashboard functions |
| Simplified visibilitychange handler | Removed empty if-block for hidden state; only the visible resume logic is needed |

## Duration

~10 minutes

## Next Phase Readiness

No blockers. Ready for 10-04-PLAN (Jobs.js, schedule.js, lists.js cleanup).
