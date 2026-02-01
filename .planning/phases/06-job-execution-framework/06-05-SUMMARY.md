---
phase: 06-job-execution-framework
plan: 05
subsystem: ui
tags: [frontend, jobs, pagination, filters, polling]
depends_on:
  requires: [06-04]
  provides: [jobs-page-ui, jobs-filter-dropdown]
  affects: [06-06]
tech_stack:
  added: []
  patterns: [expandable-rows, polling-updates, client-side-pagination]
key_files:
  created:
    - listarr/static/js/jobs.js
  modified:
    - listarr/templates/jobs.html
    - listarr/routes/lists_routes.py
decisions:
  - title: "3-second polling interval"
    rationale: "Balance between responsiveness and server load for running jobs"
  - title: "Client-side row expansion"
    rationale: "Load job details on-demand to reduce initial page load"
  - title: "/api/lists in lists_routes.py"
    rationale: "Simple endpoint for filter dropdown, co-located with list management"
metrics:
  duration: "17 minutes"
  completed: "2026-01-30"
---

# Phase 06 Plan 05: Jobs Page UI Summary

**One-liner:** Full Jobs page with paginated table, filters, expandable rows, rerun button, and polling for running jobs.

## What Was Built

### Jobs Page HTML Template (jobs.html)
Complete replacement of placeholder template with:
- Header with title and Clear All button
- Filters section with list dropdown (populated from /api/lists) and status dropdown
- Jobs table with 7 columns: expand toggle, List Name, Status, Started, Duration, Results, Actions
- Pagination controls with page info and prev/next buttons
- Loading, empty, and table container states with proper visibility toggling
- Full dark mode support

### Jobs Page JavaScript (jobs.js)
Comprehensive client-side functionality:
- **State management:** currentPage, totalPages, filters, runningJobs, expandedRows
- **Data loading:** loadLists(), loadJobs() with pagination and filters
- **Rendering:** renderJobs(), renderJobRow(), renderStatus(), renderResults(), renderActions()
- **Expandable rows:** toggleExpand(), loadJobDetails(), renderJobDetails() with items table
- **Actions:** rerunJob() for failed jobs, clearAllJobs() with confirmation
- **Pagination:** updatePagination(), changePage()
- **Polling:** startPolling() (3-second interval), stopPolling() for running job updates
- **Utilities:** formatDate(), formatDuration(), escapeHtmlLocal()

### Lists API Endpoint
- GET /api/lists returns JSON with lists array (id, name, target_service, is_active)
- Used by Jobs page filter dropdown
- Ordered by name for consistent display

## Technical Details

### Status Badges
- Running: Blue with animated spinner
- Completed: Green
- Failed: Red
- Unknown: Gray

### Results Display
- Color-coded: added (green), skipped (gray), failed (red)
- Only shown for completed/failed jobs

### Expanded Row Details
- Job metadata: triggered_by, items_found, retry_count, completed_at
- Error message box for failed jobs
- Items table with: title, TMDB ID, status, message
- Lazy-loaded on expand (reduces initial page load)

### Polling Behavior
- Starts when running jobs detected
- Polls /api/jobs/running every 3 seconds
- Reloads jobs list when running jobs complete
- Stops when no running jobs remain
- Cleaned up on page unload

## API Integration

The Jobs page integrates with all Jobs API endpoints from 06-04:
- GET /api/jobs - Paginated listing with filters
- GET /api/jobs/{id} - Job detail with items
- POST /api/jobs/{id}/rerun - Rerun failed jobs
- POST /api/jobs/clear - Clear all job history
- GET /api/jobs/running - Running jobs for polling

Plus new endpoint:
- GET /api/lists - Lists for filter dropdown

## Verification

All 415 tests pass. Must-haves verified:
- Jobs page displays paginated job history table
- Jobs can be filtered by list and status
- Job rows are expandable to show item details
- Failed jobs have a Rerun button
- Clear buttons exist for global history
- Running jobs update status via polling

Artifact line counts:
- jobs.html: 206 lines (min 100)
- jobs.js: 786 lines (min 150)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 834e916 | feat | Create Jobs page HTML template |
| 3ca80c3 | feat | Create Jobs page JavaScript |
| f83ef02 | feat | Add /api/lists endpoint for filter dropdown |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Phase 06-06 (Dashboard Widget) can proceed:
- Jobs API endpoints available
- GET /api/jobs/recent exists for dashboard widget
- UI patterns established (status badges, results display)
