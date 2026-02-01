---
phase: 06-job-execution-framework
plan: 06
subsystem: ui
tags: [dashboard, recent-jobs, javascript, polling]

dependency-graph:
  requires: [06-04]
  provides: [dashboard-jobs-widget]
  affects: []

tech-stack:
  added: []
  patterns: [polling-for-status]

key-files:
  created: []
  modified:
    - listarr/static/js/dashboard.js
    - listarr/templates/dashboard.html

decisions:
  - id: jobs-polling-interval
    choice: "2 seconds for running jobs"
    rationale: "Balance responsiveness vs server load"
  - id: error-truncation
    choice: "50 characters max for error messages"
    rationale: "Keep table rows clean, full details on Jobs page"

metrics:
  duration: "~10 minutes"
  completed: 2026-01-30
---

# Phase 6 Plan 6: Dashboard Recent Jobs Widget Summary

Dashboard displays real recent jobs from database with live status updates.

## What Was Built

### Dashboard JavaScript Updates (listarr/static/js/dashboard.js)

Updated dashboard JavaScript to load and display recent jobs from `/api/jobs/recent`:

1. **loadRecentJobs()** - Main function to fetch and display jobs
2. **fetchRecentJobs()** - API call to `/api/jobs/recent` endpoint
3. **formatJobSummary(job)** - Formats display based on status:
   - Running: Spinner animation + "Running..."
   - Completed: "X added, Y skipped"
   - Failed: Truncated error message (max 50 chars)
   - Pending: "Pending..."
4. **formatDate(dateStr)** - Relative timestamps ("Just now", "5m ago", "2h ago")
5. **escapeHtml(str)** - XSS prevention for user content
6. **capitalize(str)** - Service name formatting (radarr -> Radarr)
7. **Polling logic** - Auto-start 2s polling when running jobs detected, auto-stop when done

### Dashboard HTML Updates (listarr/templates/dashboard.html)

- Removed static placeholder rows
- Added loading state row that JavaScript replaces
- Preserved `id="recent-jobs-table-body"` for JS targeting

## Key Behaviors

| Behavior | Implementation |
|----------|----------------|
| Recent jobs from database | Fetches `/api/jobs/recent` on load |
| Table columns | List Name, Service, Executed At, Summary |
| Running job indicator | Animated spinner SVG |
| Running job updates | 2-second polling interval |
| Empty state | "No jobs have been executed yet" |
| Refresh integration | loadRecentJobs() called with refresh button |
| Cleanup | Polling stopped on page unload |

## Files Modified

| File | Changes |
|------|---------|
| `listarr/static/js/dashboard.js` | +169/-61 lines - Jobs loading, polling, formatting |
| `listarr/templates/dashboard.html` | +4/-25 lines - Loading state, removed placeholders |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| aabb1be | feat | Update dashboard recent jobs to use Jobs API |
| f75c3b5 | feat | Update dashboard HTML for dynamic job loading |

## Verification

All must-have artifacts verified:
- [x] Dashboard fetches `/api/jobs/recent` (line 30 in dashboard.js)
- [x] Table body has `id="recent-jobs-table-body"` (line 167 in dashboard.html)
- [x] `loadRecentJobs()` function exists (line 199 in dashboard.js)
- [x] Fetch pattern `fetch.*api/jobs/recent` present

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Phase 6 is now complete with all 6 plans executed:
- Wave 1: Job model + Job executor service
- Wave 2: Lists routes migration + Jobs API endpoints
- Wave 3: Jobs page UI + Dashboard widget

Ready for:
1. Phase 6 verification
2. README.md and CHANGELOG.md updates
3. Phase 6.1 (Bug Fixes) planning
