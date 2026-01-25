# Phase 6: Job Execution Framework - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Create background job processing system with execution tracking and persistent history. Jobs can be queued, executed, tracked, and their history (success/failure) is recorded and displayed. Scheduler (cron-based automation) is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Job Persistence
- Store in SQLite database (same as app data)
- Keep job history forever (no auto-purge)
- On app restart: mark any "running" jobs as "failed (interrupted)"
- Provide both per-list clear button AND global clear in settings

### History Display
- Show on Dashboard (5 most recent jobs across all lists)
- Dedicated Jobs page (placeholder already exists at jobs.html)
- Expandable rows: summary shows list name, status, timestamp, duration + counts; click to expand for full item lists
- Jobs page: paginated table (25-50 per page)
- Jobs page: filter by list AND filter by status
- Rerun button on failed jobs (triggers same list again)
- Live polling for running jobs (similar to Phase 5 Lists page)

### Execution Behavior
- Max 3 concurrent jobs (keep current ThreadPoolExecutor setting)
- Auto-retry on failure: 3 attempts with backoff delays of 5s, 10s, 20s
- Job timeout: 10 minutes
- Silent queuing (no visible "Queued" status, just wait for slot)
- Reject if same list already running (current behavior)
- Save partial results on timeout/failure (items added before error are kept)
- No job cancellation (runs to completion or timeout)

### Job State Model
- Simple statuses: running, completed, failed
- Full audit metadata stored:
  - list_id, list_name
  - status
  - started_at, completed_at, duration
  - triggered_by (manual/scheduled - prep for Phase 7)
  - retry_count
  - error_message (user-friendly) + error_details (technical, expandable)
  - import result (counts + item details)

### Claude's Discretion
- Exact item details storage (balance detail vs DB size)
- Pagination size (25 or 50)
- Polling interval for Jobs page
- Error message formatting

</decisions>

<specifics>
## Specific Ideas

- Jobs page placeholder already exists (jobs.html)
- Reuse Phase 5 polling pattern for live status updates
- Error display: user-friendly summary visible, technical details expandable for debugging

</specifics>

<schema>
## Database Schema Changes

Existing `Job` model in `listarr/models/jobs_model.py` needs updates. Tables are currently empty — safe to modify.

### Current Job fields (keep):
- id, list_id, status, started_at, finished_at
- items_found, items_added, items_skipped
- error_message

### Fields to ADD to Job:
- `list_name` (String 255) — denormalized, survives list deletion
- `duration` (Integer) — seconds, for display
- `triggered_by` (String 20, default "manual") — manual/scheduled (prep for Phase 7)
- `retry_count` (Integer, default 0)
- `items_failed` (Integer, default 0) — count of failed items
- `error_details` (Text) — technical stack trace, separate from user-friendly error_message

### Optional rename:
- `finished_at` → `completed_at` (consistency)

### JobItem model (no changes needed):
- Already has: id, job_id, tmdb_id, title, status, message
- Sufficient for per-item tracking

</schema>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-job-execution-framework*
*Context gathered: 2026-01-25*
