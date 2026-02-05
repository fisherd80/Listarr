---
phase: 07-scheduler-system
plan: 04
subsystem: ui
tags: [apscheduler, flask, jinja2, scheduler, lists, ui]

# Dependency graph
requires:
  - phase: 07-02
    provides: Scheduler service with schedule_list/unschedule_list functions
  - phase: 07-03
    provides: Schedule page UI for monitoring scheduled jobs
provides:
  - Lists page with next run time subtitles for scheduled lists
  - Edit form syncs schedule changes to APScheduler
  - Wizard syncs schedule registration on list creation
  - Toggle/delete routes update scheduler state
affects: [dashboard, jobs-page, list-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - format_relative_time helper for human-readable time display
    - Scheduler sync pattern in routes (schedule/unschedule after DB commit)

key-files:
  created: []
  modified:
    - listarr/routes/lists_routes.py
    - listarr/templates/lists.html

key-decisions:
  - "format_relative_time uses minute/hour/day units for human readability"
  - "Next run subtitle only shown for active scheduled lists"
  - "Scheduler sync happens after DB commit to ensure consistency"
  - "Scheduler errors handled gracefully with logging (non-blocking)"

patterns-established:
  - "Scheduler sync pattern: schedule if (cron AND active), else unschedule"
  - "Graceful error handling for scheduler operations (no user-facing errors)"

# Metrics
duration: 4min
completed: 2026-02-05
---

# Phase 07 Plan 04: Lists UI Scheduler Integration Summary

**Lists page shows next run subtitles, edit form and wizard sync schedule changes to APScheduler automatically**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-05T21:49:14Z
- **Completed:** 2026-02-05T21:53:54Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Lists page displays next scheduled run time under each list name
- Edit form syncs schedule changes to APScheduler on save
- Wizard syncs schedule registration on list creation/update
- Toggle/delete routes update scheduler state appropriately
- Graceful error handling for scheduler operations

## Task Commits

Each task was committed atomically:

1. **Task 1: Add next run subtitle to Lists page** - `b456956` (feat)
2. **Task 2: Wire edit form to update scheduler** - `e26777d` (feat)
3. **Task 3: Wire wizard save to register schedule** - `2ca0080` (feat)

## Files Created/Modified
- `listarr/routes/lists_routes.py` - Added scheduler integration to lists_page, edit_list, toggle_list, delete_list, and wizard_submit routes; added format_relative_time helper
- `listarr/templates/lists.html` - Updated Name column to show next run subtitle with relative time formatting

## Decisions Made

1. **format_relative_time helper uses minute/hour/day units** - Human-readable upcoming job times ("in 2 hours", "in 3 days") are more intuitive than absolute timestamps for at-a-glance visibility
2. **Next run subtitle only for active scheduled lists** - Disabled lists show "Disabled" italic text instead of next run time
3. **Scheduler sync after DB commit** - Ensures database consistency before registering/updating APScheduler jobs
4. **Graceful scheduler error handling** - Scheduler operations log warnings but don't block user actions (allows operation in non-scheduler workers)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

- Lists UI fully integrated with scheduler
- Users can see next run times at-a-glance on Lists page
- All CRUD operations (create, edit, toggle, delete) sync with scheduler
- Ready for any additional scheduler UI features or automation

---
*Phase: 07-scheduler-system*
*Completed: 2026-02-05*
