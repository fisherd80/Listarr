# Plan 10-01 Summary: Jinja2 Macro Library

**Phase:** 10 - UI/UX Simplification
**Plan:** 01 of 05
**Status:** Complete
**Date:** 2026-02-07

## What Was Done

### Task 1: Create Jinja2 macro library files
- Created `listarr/templates/macros/status.html` with `status_badge` and `service_badge` macros
- Created `listarr/templates/macros/ui.html` with `loading_spinner` and `empty_state` macros
- `status_badge`: Supports 12 status types with exact Tailwind color mapping, optional animated spinner for "running" status
- `service_badge`: Renders amber (Radarr) or blue (Sonarr) pill badges
- `loading_spinner`: SVG spinner with configurable message and size (renders content only, no wrapper div)
- `empty_state`: Icon + heading + description + optional action button (renders content only, no wrapper div)
- **Commit:** `9e0b5ff`

### Task 2: Replace inline HTML with macro calls in templates
- **lists.html**: Imported `empty_state`, replaced 18-line empty state block with 1-line macro call
- **schedule.html**: Imported `service_badge` and `empty_state`, replaced inline service badge (3 lines → 1) and 33-line empty state with 1-line macro call
- **jobs.html**: Imported `loading_spinner` and `empty_state`, replaced 7-line spinner and 22-line empty state with 1-line macro calls each
- **dashboard.html**: Skipped — all status badges are JS-managed (dynamically replaced by `updateStatusBadge()`)
- **lists.html status badges**: Skipped — JS `toggleList()` directly sets className on `data-status-badge` elements
- Net reduction: **82 lines of inline HTML** replaced with **15 lines** (imports + macro calls)
- **Commit:** `fddc5bb`

## Deviations

None. Plan executed as designed.

## Verification

- All 453 tests pass (no test modifications needed)
- Macro files use exact same Tailwind classes as the inline HTML they replace
- JS-managed elements (dashboard badges, lists status badges) left untouched to preserve dynamic behavior
- Wrapper divs with IDs (`jobs-loading`, `jobs-empty`) preserved for JS show/hide

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Inline empty state blocks | 3 (lists, schedule, jobs) | 0 |
| Inline loading spinners | 1 (jobs) | 0 |
| Inline service badges | 1 (schedule) | 0 |
| Net lines removed | - | 67 |
| Macro files created | 0 | 2 |
| Templates using macros | 0 | 3 |
