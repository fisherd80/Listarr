---
phase: 07-scheduler-system
plan: 05
subsystem: dashboard
tags: [ui, scheduler, dashboard, widget, api]
requires: [07-02]
provides: [upcoming-jobs-widget, dashboard-scheduler-visibility]
affects: []
tech-stack:
  added: []
  patterns: [relative-time-formatting, widget-polling]
key-files:
  created: []
  modified:
    - listarr/routes/dashboard_routes.py
    - listarr/templates/dashboard.html
    - listarr/static/js/dashboard.js
decisions:
  - format_relative_time helper uses minute/hour/day units for human-readable times
  - Upcoming widget refreshes during job polling (2-second interval)
  - Widget limited to 5 upcoming jobs sorted by next run time
  - 2-column layout: Upcoming (1/3 width) + Recent Jobs (2/3 width)
  - Paused badge shows when scheduler_paused is true
metrics:
  duration: 8 minutes
  completed: 2026-02-05
---

# Phase 07 Plan 05: Dashboard Upcoming Widget Summary

**One-liner:** Upcoming widget shows next 5 scheduled jobs with relative times and scheduler pause status

## What Was Built

Added "Upcoming" widget to dashboard showing next 3-5 scheduled jobs for at-a-glance visibility.

### Task Breakdown

**Task 1: Add upcoming jobs API endpoint** (Commit: 2236a2c)
- Created GET /api/dashboard/upcoming endpoint in dashboard_routes.py
- Returns next 5 scheduled jobs sorted by run time
- Includes list_id, list_name, service, next_run (ISO), next_run_relative
- Shows scheduler_paused status from ServiceConfig
- Added format_relative_time() helper for human-readable times (minutes, hours, days)
- **Fixed missing scheduler_paused column in database** (Rule 2 - Missing Critical)

**Task 2: Add Upcoming widget to dashboard template** (Commit: 0c1c12c)
- Added Upcoming widget in 2-column grid layout with Recent Jobs
- Upcoming widget: 1/3 width, Recent Jobs: 2/3 width on large screens
- Includes loading state, empty state with guidance text, and paused badge
- Empty state guides users to configure schedules on Lists page
- Paused badge displayed when scheduler is globally paused

**Task 3: Add Upcoming widget JavaScript** (Commit: a2bf2bb)
- Added fetchUpcomingJobs() to call /api/dashboard/upcoming
- Added updateUpcomingWidget() to render list of upcoming jobs
- Added loadUpcoming() function called on page load
- Integrated upcoming refresh into polling loop (2-second interval when jobs running)
- Refresh button now refreshes both recent and upcoming widgets
- Shows/hides paused badge based on scheduler_paused status
- Uses existing escapeHtml() and capitalize() helpers

## Technical Details

**API Response Format:**
```json
{
  "upcoming": [
    {
      "list_id": 1,
      "list_name": "Top Rated Movies",
      "service": "radarr",
      "next_run": "2026-02-09T00:00:00+00:00",
      "next_run_relative": "in 3 days"
    }
  ],
  "scheduler_paused": false
}
```

**Relative Time Logic:**
- < 1 minute: "in less than a minute"
- < 1 hour: "in X minute(s)"
- < 1 day: "in X hour(s)"
- ≥ 1 day: "in X day(s)"
- Past due: "overdue"

**Polling Behavior:**
- Widget loads on page load
- Refreshes every 2 seconds when jobs are running
- Refreshes when manual refresh button clicked
- No polling when no jobs running (efficiency)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added scheduler_paused column to database**
- **Found during:** Task 1 (API endpoint testing)
- **Issue:** ServiceConfig.scheduler_paused column defined in model but missing from database
- **Fix:** Added column via ALTER TABLE statement using SQLAlchemy text() execution
- **Files modified:** Database schema (ALTER TABLE service_config)
- **Commit:** Part of 2236a2c
- **Rationale:** Column was supposed to be added in Plan 07-01 but database migration was missed. Without this column, API endpoint would crash on every request. This is critical for basic operation.

## Testing

**API Endpoint:**
```bash
GET /api/dashboard/upcoming
Status: 200
Response: 2 upcoming jobs with relative times
```

**Dashboard Page:**
```bash
GET /
Status: 200
Contains: upcoming-jobs-list, scheduler-paused-badge, upcoming-empty
JavaScript loaded: dashboard.js
```

**All endpoints verified:** ✓

## Integration Points

**Depends On:**
- 07-02: Scheduler service with get_next_run_time() function
- Existing dashboard infrastructure (dashboard.js, service cards)
- APScheduler job tracking

**Provides:**
- Upcoming widget for dashboard visibility
- /api/dashboard/upcoming endpoint
- format_relative_time() helper function

**Key Files:**
- `listarr/routes/dashboard_routes.py` - upcoming_jobs() endpoint + helper
- `listarr/templates/dashboard.html` - Upcoming widget HTML
- `listarr/static/js/dashboard.js` - fetchUpcomingJobs(), updateUpcomingWidget(), loadUpcoming()

## Next Phase Readiness

**Ready for:** Next phase can proceed

**Blockers:** None

**Concerns:** None

## Notes

- Widget gracefully handles empty state (no scheduled jobs)
- Paused badge provides visibility into global scheduler state
- 2-column layout works responsively (stacks on mobile)
- Polling integration ensures real-time updates during job execution
- Relative time format matches user expectations (human-readable)
- Database schema fix ensures scheduler_paused works across all plans

---

*Plan completed: 2026-02-05*
*Duration: 8 minutes*
*Tasks: 3/3*
*Commits: 2236a2c, 0c1c12c, a2bf2bb*
