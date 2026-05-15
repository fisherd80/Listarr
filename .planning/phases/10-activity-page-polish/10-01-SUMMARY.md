---
phase: 10-activity-page-polish
plan: "01"
subsystem: api
tags: [flask, sqlalchemy, activity, tests, tdd]

requires:
  - phase: 10-activity-page-polish
    provides: "Activity page polish plan context and BUG-03 backend contract"
provides:
  - "GET /api/activity now emits list_deleted for each job"
  - "Integration tests cover orphaned, existing, and null list_id activity rows"
affects: [10-02-PLAN.md, activity-page-polish, BUG-03]

tech-stack:
  added: []
  patterns:
    - "Reuse existing List.query.get(job.list_id) lookup when deriving per-job activity response fields"
    - "Use bulk list-row delete in tests when an orphaned job must retain a stale list_id"

key-files:
  created:
    - ".planning/phases/10-activity-page-polish/10-01-SUMMARY.md"
  modified:
    - "listarr/routes/activity_routes.py"
    - "tests/routes/test_activity_routes.py"

key-decisions:
  - "Derived list_deleted from a non-null job.list_id plus a missing List lookup, preserving null list_id as not deleted."
  - "Used a bulk list delete in the orphaned-job test so SQLAlchemy does not null the loaded Job.list_id before the route is exercised."

patterns-established:
  - "Activity API compatibility: enrich job.to_dict() output inside get_activity() without changing Job.to_dict()."

requirements-completed: [BUG-03]

duration: 2min
completed: 2026-05-15
---

# Phase 10 Plan 01: Activity List Deleted API Summary

**Activity API rows now carry a list_deleted boolean so deleted-list badges can render from a stable backend contract.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-15T10:26:23Z
- **Completed:** 2026-05-15T10:28:26Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added `list_deleted` to each `GET /api/activity` job payload.
- Added `TestGetActivityListDeleted` with coverage for stale list references, existing lists, and `list_id=None`.
- Confirmed all 36 activity route tests pass and both touched files are ruff-clean.

## Task Commits

TDD task was committed atomically:

1. **Task 1 RED: Write failing list_deleted tests** - `5b59308` (test)
2. **Task 1 GREEN: Expose deleted list activity flag** - `93e393c` (feat)

**Plan metadata:** recorded in the final docs commit for this plan

## Files Created/Modified

- `tests/routes/test_activity_routes.py` - Added `TestGetActivityListDeleted` with three API contract tests.
- `listarr/routes/activity_routes.py` - Added `job_dict["list_deleted"] = job.list_id is not None and list_obj is None` inside `get_activity()`.

## Decisions Made

- Kept `list_deleted` as a route-level enrichment rather than changing `Job.to_dict()`, because the field depends on a live `List` lookup already performed by `get_activity()`.
- Preserved the exact deleted predicate from the plan: a deleted list requires a non-null `job.list_id` and no matching `List` row.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Bug] Preserved stale list_id in orphaned-job test**
- **Found during:** Task 1 GREEN verification
- **Issue:** The planned `db.session.delete(test_list)` caused SQLAlchemy to null the loaded child `Job.list_id` in this test session, so the test no longer represented the stale non-null list reference required by BUG-03.
- **Fix:** Replaced the ORM instance delete with `List.query.filter_by(id=list_id).delete(synchronize_session=False)` in the orphaned-row test setup.
- **Files modified:** `tests/routes/test_activity_routes.py`
- **Verification:** `pytest tests/routes/test_activity_routes.py::TestGetActivityListDeleted -q` passed 3/3, and `pytest tests/routes/test_activity_routes.py -x -q` passed 36/36.
- **Committed in:** `93e393c` (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test setup now models the required stale-reference state without expanding implementation scope.

## Issues Encountered

- Initial GREEN run passed the existing-list and null-list cases but failed the orphaned-list case because the test setup had lost the stale FK. Fixed as documented above.

## Known Stubs

None. Stub scan of modified files found only intentional empty dict/JSON literals in test fixtures and request bodies.

## User Setup Required

None - no external service configuration required.

## Verification

- `pytest tests/routes/test_activity_routes.py::TestGetActivityListDeleted -q` - 3 passed
- `pytest tests/routes/test_activity_routes.py -x -q` - 36 passed
- `ruff check listarr/routes/activity_routes.py` - passed
- `ruff check tests/routes/test_activity_routes.py` - passed
- Exact route line present at `listarr/routes/activity_routes.py:67`

## Next Phase Readiness

Plan 10-02 can render the Deleted badge from `job.list_deleted` in the activity response while keeping the existing `target_service` field behavior intact.

## Self-Check: PASSED

- Found summary file: `.planning/phases/10-activity-page-polish/10-01-SUMMARY.md`
- Found task commit: `5b59308`
- Found task commit: `93e393c`

---
*Phase: 10-activity-page-polish*
*Completed: 2026-05-15*
