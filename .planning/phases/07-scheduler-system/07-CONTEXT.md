# Phase 7: Scheduler System - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Cron-based scheduler that runs list imports automatically on user-defined schedules. Lists can be configured with schedules in the wizard, managed on a dedicated Schedule page, and execute without manual intervention. The scheduler respects existing list enabled/disabled state.

</domain>

<decisions>
## Implementation Decisions

### Schedule options
- Presets + custom cron: Dropdown with common intervals, plus advanced field for cron expression
- Presets: Claude's discretion on sensible defaults (e.g., hourly, every 6h, daily, weekly)
- Cron validation: Parse cron expression, show error if invalid, display "Next run: X" preview
- Wizard (Step 4): Simple preset dropdown with fixed times (daily = midnight, weekly = Sunday midnight)
- Schedule page: Full control — user can edit schedule with specific times, custom cron
- No default schedule: New lists have no schedule, user must explicitly set one
- One schedule per list: No multiple schedules per list
- Timezone: Server timezone, controllable via Docker environment variable (TZ)

### Schedule page
- Overview table: List all scheduled lists with columns for status, last run, next run
- Click row to edit list
- Global pause toggle in page header
- Status column showing: Scheduled, Running, Paused, Manual only

### Execution behavior
- Overlap handling: Skip the new run if list is already running (log it)
- Missed schedules: Skip missed, wait for next scheduled time
- Startup behavior: No jobs on startup, wait for scheduled times
- Concurrency: Parallel execution allowed (multiple lists can run simultaneously)
- Failure handling: Log and continue to next scheduled run (no retry)
- Job source tracking: Jobs show "Scheduled" vs "Manual" trigger type in history

### Status visibility
- Lists page: Subtitle under list name showing next run time in relative format ("in 2 hours", "Tomorrow at 6 AM")
- Dashboard: Add "Upcoming" widget showing next 3-5 scheduled jobs
- Schedule page: "Last Run" column shows time + items count ("2 hours ago (3 added)")
- Running jobs: Same format as dashboard/lists/jobs page — "Running" status, details on Jobs page
- Auto-refresh: Poll every few seconds when jobs active (same pattern as Jobs page)

### Enable/disable flow
- Existing list "enabled" toggle controls scheduling: disabled = no scheduled runs
- Disabled means fully off: Cannot run manually either, must enable first
- Disabled appearance: Grayed out row, "Run" button disabled
- Disabled lists always visible (grayed out)
- Disable during run: Let current job finish, no future scheduled runs
- Re-enable behavior: Resume from next scheduled time (no immediate run)
- Quick toggle: Existing Disable button on Lists page and checkbox in edit form already work
- Global pause: Gray out scheduled items while globally paused

### Documentation
- On phase completion: Update README.md, CHANGELOG.md, CLAUDE.md per established standard

### Claude's Discretion
- Specific preset intervals to offer
- Cron library choice and implementation
- Scheduler architecture (APScheduler vs custom)
- Exact polling interval for auto-refresh
- Progress indicator styling (consistent with existing patterns)

</decisions>

<specifics>
## Specific Ideas

- Wizard keeps it simple (presets only), Schedule page offers full control
- "Next run" display uses relative times for readability ("in 2 hours" not timestamps)
- Global pause toggle is prominent in Schedule page header
- Follows existing UI patterns for running job indicators and polling

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-scheduler-system*
*Context gathered: 2026-02-05*
