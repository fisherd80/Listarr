# Phase 5: Manual Trigger UI - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add manual trigger capability to run any list on-demand from the UI. Users can click a button to immediately execute any list import job using the existing `/lists/<id>/run` endpoint, see status feedback during execution, and view results when complete.

</domain>

<decisions>
## Implementation Decisions

### Button placement & design
- Button appears on list card actions (alongside edit/delete buttons)
- Text-only button labeled "Run" (no icon)
- Button hidden entirely on disabled lists (only visible on enabled lists)
- No confirmation dialog — click and it runs immediately

### Status feedback during run
- Button text changes to "Running..." while executing
- Button is disabled (not clickable) while running
- Running state persists if user navigates away and returns — check status on page load
- Poll endpoint periodically to detect completion (not blocking request)

### Results display
- Toast notification summary when complete (e.g., "5 added, 3 skipped, 1 failed")
- Toast follows existing app notification format/duration
- Color-coded toasts: green for success, yellow if some skipped, red if failures
- Toast only for now — no "View details" link (will link to Job History when Phase 6 delivers it)

### Run prevention logic
- Multiple different lists can run in parallel
- Same list cannot run twice simultaneously — show "Already running" message if attempted
- No rate limiting beyond the "already running" block
- If run fails to start (e.g., service unavailable), show error toast and return button to "Run" state

### Claude's Discretion
- Exact polling interval for status checks
- Toast positioning and animation
- Technical approach for tracking running state across page navigation

</decisions>

<specifics>
## Specific Ideas

- Toast styling should match existing notification system in the app
- Link to job history entry will be added when Phase 6 (Job Execution Framework) delivers the Jobs page

</specifics>

<deferred>
## Deferred Ideas

- Detailed results view with item breakdown — Phase 6 (Job Execution Framework) will provide job history
- "View details" link on toast to navigate to job history — add when Phase 6 delivers

</deferred>

---

*Phase: 05-manual-trigger-ui*
*Context gathered: 2026-01-25*
