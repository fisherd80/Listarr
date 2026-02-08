---
phase: 10-ui-ux-simplification
plan: 04
status: complete
started: 2026-02-08
completed: 2026-02-08
---

# Summary: Jobs.js, Schedule.js, Lists.js Cleanup and Performance Fixes

## What Was Done

### Task 1: Clean up jobs.js
- Removed duplicate `getCsrfToken()` (now from global utils.js)
- Removed duplicate `escapeHtmlLocal()`, replaced all 7 call sites with global `escapeHtml()`
- Removed duplicate `formatDuration()` (now from global utils.js)
- Renamed local `formatDate()` to `formatDateAbsolute()` (keeps absolute format for job history table, avoids conflict with global relative `formatDate()`)
- Added `document.visibilityState` check inside polling interval (skip API calls when tab hidden)
- Added `visibilitychange` event listener to stop/start polling on tab hide/show
- Replaced Enter key filter listeners with `change` event listeners for auto-apply on dropdown change

### Task 2: Clean up schedule.js and lists.js
- Removed duplicate `getCsrfToken()` from schedule.js (now from global utils.js)
- Removed duplicate `formatRelativeTime()` from schedule.js (now from global utils.js, 42 lines)
- Removed duplicate `getCsrfToken()` from lists.js (now from global utils.js)
- Verified all call sites still reference global functions correctly

## Metrics

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| jobs.js | 795 | 756 | 39 lines (5%) |
| schedule.js | 288 | 230 | 58 lines (20%) |
| lists.js | 552 | 542 | 10 lines (2%) |
| **Total** | **1635** | **1528** | **107 lines (7%)** |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| bfa4e84 | refactor | Clean up jobs.js duplicates and add visibility polling |
| ab57cbc | refactor | Remove duplicate utilities from schedule.js and lists.js |

## Test Results

- All 453 tests pass (no modifications needed)
- JavaScript changes are frontend-only, no backend test impact

## Deviations

None.

## Must-Haves Verification

- [x] jobs.js uses shared getCsrfToken, escapeHtml, formatDuration from utils.js (no local duplicates)
- [x] schedule.js uses shared getCsrfToken, formatRelativeTime from utils.js (no local duplicates)
- [x] lists.js uses shared getCsrfToken from utils.js (no local duplicate)
- [x] Jobs page polling pauses when tab is hidden
- [x] Jobs filter inputs auto-apply on change (select dropdowns use `change` event)

## Duplicate Function Elimination Summary (Phase 10 cumulative)

After this plan, no page-specific JS file defines any of these shared functions:
- `getCsrfToken()` - only in utils.js
- `escapeHtml()` - only in utils.js
- `formatDuration()` - only in utils.js
- `formatRelativeTime()` - only in utils.js
- `formatDate()` - only in utils.js (relative), jobs.js keeps `formatDateAbsolute()` (absolute format)
- `capitalize()` - only in utils.js
- `debounce()` - only in utils.js
