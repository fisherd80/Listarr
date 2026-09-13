---
phase: 15-maintenance-finish
plan: 12
subsystem: ui
tags: [activity, jobs.js, jobs.html, jest-free-static-contract-tests]

# Dependency graph
requires:
  - phase: 15-maintenance-finish
    provides: "15-10's per-list clear-history route wiring (#clear-list-btn / clearListActivity / POST /api/activity/clear/<list_id>)"
provides:
  - "Single #clear-activity-btn control on the Activity page that adapts its label and POST target to the current List filter selection"
affects: [15-maintenance-finish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single dispatching handler (clearActivity) branching on filter state instead of two parallel handlers bound to two buttons"

key-files:
  created: []
  modified:
    - listarr/templates/jobs.html
    - listarr/static/js/jobs.js
    - tests/routes/test_activity_routes.py

key-decisions:
  - "clearActivity() branches with two literal fetch() call sites (one per URL) rather than a single fetch(fetchUrl) variable, so the JS source retains literal `fetch(\"/api/activity/clear\"` and `fetch(\"/api/activity/clear/\"` substrings the plan's asset-contract tests assert on directly."
  - "Button is never disabled now (both branches — clear all vs. clear selected list — are always valid actions); dropped the outline/disabled-state Tailwind classes entirely and kept the destructive bg-error styling unconditionally, per the plan's merged design."

requirements-completed: [UAT-15-G4]

# Metrics
duration: 25min
completed: 2026-09-13
---

# Phase 15 Plan 12: Merge Activity clear-history buttons Summary

**Single adaptive `#clear-activity-btn` on the Activity page replaces the two separate Clear List / Clear All buttons 15-10 shipped, dispatching to the scoped or global clear endpoint based on the List filter.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-13T18:15Z
- **Completed:** 2026-09-13T18:30Z
- **Tasks:** 2/2 completed
- **Files modified:** 3

## Accomplishments
- Replaced the `#clear-list-btn` + `#clear-all-btn` header pair in `jobs.html` with one `#clear-activity-btn` (always-enabled, destructive `bg-error` styling)
- Replaced `updateClearListButton()` / `clearListActivity()` / `clearAllActivity()` in `jobs.js` with `updateClearActivityButton()` (label/title sync) + `clearActivity()` (single dispatching handler covering both the scoped and global POST targets)
- Rewrote the five 15-10 two-button tests in `test_activity_routes.py` into four tests asserting on the merged single-button markup/behavior; all backend route tests, pagination, filters, rerun, auth, and CSRF tests untouched

## Task Commits

Each task was committed atomically:

1. **Task 1: Update failing tests for the merged single clear-history button** - `0838c21` (test)
2. **Task 2: Merge the two buttons into one dispatching clearActivity() control** - `2ae7138` (feat)

_TDD RED confirmed before Task 2: the 4 new/renamed tests failed against the pre-merge markup/JS (missing `#clear-activity-btn`, missing `clearActivity`/`updateClearActivityButton`) prior to the Task 2 edit._

## Files Created/Modified
- `listarr/templates/jobs.html` - Header button group collapsed to a single `#clear-activity-btn`, no disabled-state classes
- `listarr/static/js/jobs.js` - `updateClearActivityButton()` + `clearActivity()` replace the three 15-10 functions; `loadLists()`, `applyFilters()`, `initJobsPage()` call sites updated
- `tests/routes/test_activity_routes.py` - `TestActivityPage`/`TestActivityPageJavaScript` rewritten for the merged control (4 tests replacing 5)

## Decisions Made
- `clearActivity()`'s two POST branches use literal `fetch("/api/activity/clear/" + ...)` and `fetch("/api/activity/clear", ...)` call sites (ternary on the `response =` assignment) instead of a single templated `fetchUrl` variable — keeps the source directly greppable/assertable for both literal URL prefixes per the plan's asset-contract test spec, while still being one function with one internal branch (not two copies).
- Kept the destructive `bg-error`/`text-white` styling unconditionally on the merged button (previously only on `#clear-all-btn`) since every click now performs a genuinely destructive clear, scoped or global.

## Deviations from Plan

None - plan executed exactly as written. `listarr/routes/activity_routes.py` and its backend route tests were not touched, as required.

## Issues Encountered

Both task commits triggered the repository's pre-commit + GPG-signing pipeline; commit `0838c21` (Task 1) took several minutes to land due to an interactive `pinentry` prompt against the (Windows/git-bash) `gpg-agent`, consistent with the precedent recorded in STATE.md for 15-08 ("blocked ~10min by an interactive GPG-signing timeout until the user unlocked gpg-agent externally"). No `--no-gpg-sign` bypass was used; the commit was allowed to complete on its own once the agent's cached credentials became available. Commit `2ae7138` (Task 2) completed promptly. No code changes were required to work around this — it is an environment/tooling characteristic, not a plan defect.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

UAT-15-G4 closed. `listarr/templates/jobs.html` contains exactly one clear-history button; `listarr/static/js/jobs.js` contains only `clearActivity()`/`updateClearActivityButton()` (the old three-function two-button design fully removed). Full `tests/routes/test_activity_routes.py` suite (44 tests) and the broader `-k activity` suite (50 tests) pass; full repo suite (1024 tests) passes; `node --check jobs.js`, `ruff check .`, `ruff format --check .`, and `bandit -r listarr -ll` all clean. No blockers for the phase-level `/gsd-verify-work 15` / phase PR step, which the orchestrator owns.

---
*Phase: 15-maintenance-finish*
*Completed: 2026-09-13*

## Self-Check: PASSED

- FOUND: listarr/templates/jobs.html
- FOUND: listarr/static/js/jobs.js
- FOUND: tests/routes/test_activity_routes.py
- FOUND: .planning/phases/15-maintenance-finish/15-12-SUMMARY.md
- FOUND: commit 0838c21
- FOUND: commit 2ae7138
