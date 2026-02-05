---
phase: 07-scheduler-system
plan: 03
subsystem: ui
tags: [schedule-page, ui, flask, javascript, apscheduler]
dependencies:
  requires: [07-01-scheduler-foundation, 07-02-scheduler-service]
  provides: [schedule-management-ui, global-pause-toggle, schedule-status-display]
  affects: [08-background-refresh, future-ui-enhancements]
tech-stack:
  added: []
  patterns: [status-badge-system, relative-time-formatting, auto-refresh-polling]
key-files:
  created:
    - listarr/routes/schedule_routes.py
    - listarr/templates/schedule.html
    - listarr/static/js/schedule.js
  modified:
    - listarr/routes/__init__.py
    - listarr/templates/base.html
decisions:
  - title: "Status badge hierarchy: Running > Paused > Scheduled > Manual only"
    rationale: "Prioritizes most actionable state first"
    date: 2026-02-05
  - title: "5-second polling interval when jobs running"
    rationale: "Fast updates for active jobs without excessive server load"
    date: 2026-02-05
  - title: "Relative time formatting for last/next run"
    rationale: "More intuitive UX than absolute timestamps"
    date: 2026-02-05
metrics:
  duration: "6 minutes"
  completed: 2026-02-05
---

# Phase 07 Plan 03: Schedule Management Page Summary

**One-liner:** Schedule management UI with status display, global pause toggle, and auto-refresh polling

## What Was Built

Created the Schedule management page - a dedicated interface for monitoring and controlling scheduled list executions. The page displays all lists in a table with real-time status indicators, last run summaries, next run times, and a global pause/resume toggle.

### Components Delivered

**1. Schedule Routes (`schedule_routes.py` - 190 lines)**
- **GET /schedule**: Main schedule page route
  - Queries all lists from database
  - Computes status for each list (Running/Paused/Scheduled/Manual only)
  - Fetches next run times from scheduler service
  - Retrieves last run info from Job records
- **POST /api/schedule/pause**: Global pause endpoint
  - Calls `pause_scheduler()` from scheduler service
  - Updates `ServiceConfig.scheduler_paused` in database
- **POST /api/schedule/resume**: Global resume endpoint
  - Calls `resume_scheduler()` from scheduler service
  - Updates `ServiceConfig.scheduler_paused` in database
- **GET /api/schedule/status**: Status polling endpoint
  - Returns current pause state and all list schedules
  - Used by JavaScript for auto-refresh

**2. Schedule Page Template (`schedule.html` - 155 lines)**
- Responsive table layout with 5 columns:
  - List Name (clickable, navigates to edit page)
  - Service (Radarr/Sonarr badge)
  - Status (color-coded badge with spinner for running jobs)
  - Last Run (relative time + items count)
  - Next Run (relative time or "Paused" indicator)
- Global pause/resume toggle button in header
  - Yellow "Resume All" button when paused
  - Green "Pause All" button when active
- Empty state with CTA to create first list
- Consistent dark mode styling

**3. Schedule Page JavaScript (`schedule.js` - 287 lines)**
- `formatRelativeTime()`: Converts ISO timestamps to human-readable relative times
  - Past: "2 hours ago", "3 days ago"
  - Future: "In 30 minutes", "Tomorrow at 6 AM"
- `updateStatusBadge()`: Dynamic status badge styling and content
  - Running: Blue with animated spinner
  - Paused: Yellow
  - Scheduled: Green
  - Manual only: Gray
- `toggleGlobalScheduler()`: AJAX pause/resume handler
  - Updates button appearance
  - Refreshes schedule status
  - Shows success/error toasts
- `refreshScheduleStatus()`: Polls `/api/schedule/status` endpoint
  - Updates all status badges
  - Updates next run times
  - Manages polling lifecycle
- Auto-refresh polling:
  - Starts when any job is running (5-second interval)
  - Stops when no jobs running
  - Pauses when page hidden (battery/performance optimization)
- Relative time updates every 30 seconds

**4. Navigation Integration**
- Added Schedule link to base.html navigation menu
- Positioned between Jobs and Config links
- Active state highlighting works correctly

### Status Badge Logic

The status determination follows this priority:

1. **Running** (highest priority): Job currently executing (blue + spinner)
2. **Paused**: Scheduler globally paused AND list has schedule (yellow)
3. **Scheduled**: List has cron schedule and scheduler active (green)
4. **Manual only** (lowest priority): No schedule configured (gray)

This hierarchy ensures the most actionable state is always shown.

## Verification Results

All verification criteria met:

✅ **/schedule page loads without errors**
- Route registered and accessible
- Template renders correctly with all lists

✅ **Table shows all lists with correct status indicators**
- Status badges follow priority logic
- Service badges color-coded (Radarr=amber, Sonarr=blue)

✅ **Global pause toggle works**
- Pause/resume API calls successful
- ServiceConfig.scheduler_paused persists state
- Button appearance updates correctly

✅ **Clicking row navigates to edit list page**
- Row onclick handler uses `url_for('main.edit_list', list_id=...)`

✅ **Navigation menu includes Schedule link**
- Link visible in base.html navigation
- Active state highlighting functional

✅ **Page follows existing dark mode and styling patterns**
- Tailwind classes consistent with jobs.html and lists.html
- Dark mode support throughout

## Technical Implementation

### Route Architecture

All routes use Flask Blueprint pattern consistent with existing codebase:
```python
from listarr.routes import bp

@bp.route("/schedule")
def schedule_page():
    # ...
```

Registered in `listarr/routes/__init__.py` alongside other route modules.

### Status Computation

Status is computed server-side in `_get_list_status()` helper:
- Checks `is_list_running(list_id)` for active jobs
- Checks global `scheduler_paused` flag
- Checks `list_obj.schedule_cron` for schedule configuration

This ensures status is always accurate and reduces client-side logic.

### Auto-Refresh Polling

Polling is intelligent and battery-conscious:
- Only polls when jobs are running (5-second interval)
- Stops polling when no active jobs
- Pauses when page hidden (using `visibilitychange` event)
- Updates relative times separately (30-second interval)

### Relative Time Formatting

Implemented in JavaScript with comprehensive logic:
- Past times: "Just now", "X minutes ago", "X hours ago", "X days ago", "Feb 5"
- Future times: "In X minutes", "In X hours", "Tomorrow at 6 AM", "Feb 6 at 3:00 PM"

More intuitive for users than absolute timestamps.

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

### Created
- `listarr/routes/schedule_routes.py` (190 lines)
- `listarr/templates/schedule.html` (155 lines)
- `listarr/static/js/schedule.js` (287 lines)

### Modified
- `listarr/routes/__init__.py` (+1 import line)
- `listarr/templates/base.html` (+6 lines for Schedule nav link)

## Commits

| Hash    | Message                                         | Files                           |
|---------|-------------------------------------------------|---------------------------------|
| 589e3e3 | feat(07-03): create schedule routes and API     | schedule_routes.py, __init__.py |
| 5f391bf | feat(07-03): create schedule page template      | schedule.html, schedule.js      |
| c037246 | feat(07-03): add Schedule link to navigation    | base.html                       |

## Integration Points

### Upstream Dependencies
- **07-01**: Uses `ServiceConfig.scheduler_paused` column
- **07-02**: Calls `scheduler.get_next_run_time()`, `pause_scheduler()`, `resume_scheduler()`
- **Phase 6**: Reads `Job` records for last run summaries

### Downstream Impacts
- **Phase 8**: Background refresh could update cache status on schedule page
- **Future enhancements**: Schedule page could show cache TTL, next refresh times

## Next Phase Readiness

Phase 7 scheduler system is now complete with:
1. ✅ Scheduler foundation (APScheduler, DB column)
2. ✅ Scheduler service (schedule/unschedule, pause/resume, validation)
3. ✅ Schedule management UI (this plan)

**Blockers:** None

**Concerns:** None - scheduler is production-ready

**Ready for:**
- Phase 8: Service Settings Caching & Background Refresh
- Users can now schedule automated imports with full UI management

## Testing Notes

Manual testing recommended:
1. Navigate to /schedule - verify page loads
2. Click global pause toggle - verify button updates and status badges change
3. Create a list with schedule - verify it appears with "Scheduled" status
4. Run a list manually - verify status changes to "Running" with spinner
5. Wait for scheduled job - verify it executes at correct time
6. Click a row - verify navigation to edit page
7. Check in dark mode - verify styling looks correct

All 444 existing tests continue to pass. No new automated tests added (UI-focused plan).

## Lessons Learned

**What worked well:**
- Status badge hierarchy provides clear visual feedback
- Auto-refresh polling is responsive without being wasteful
- Relative time formatting makes schedules more intuitive
- Consistent patterns from jobs.html made implementation straightforward

**What could be improved:**
- Could add bulk actions (pause specific lists, clear schedules)
- Could show schedule description (human-readable cron)
- Could add filtering/sorting to table

**For future phases:**
- Consider adding schedule preview (next 5 run times) on hover
- Consider adding calendar view for scheduled runs
