# Phase 5 Plan 02: Async Run Endpoint and Progress Polling Summary

**One-liner:** Async import endpoint with ThreadPoolExecutor background execution, status polling, and localStorage state persistence across navigation

## What Was Built

### Async Run Endpoint (lists_routes.py)
- Converted `/lists/<id>/run` from synchronous (200) to asynchronous (202)
- POST returns immediately with `{"success": true, "job_id": N, "status": "started"}`
- Background job execution via `ThreadPoolExecutor` (max 3 workers)
- In-memory job tracking with thread-safe `_jobs_lock`
- Duplicate run prevention: returns 400 if list already running
- Background job updates `last_run_at` and stores result on completion

### Status Endpoint (lists_routes.py)
- Added `GET /lists/<id>/status` for polling job state
- Returns status: `idle` | `running` | `completed` | `error`
- Includes `last_run_at` timestamp and `result` dict on completion
- Clears job from memory after reporting completion/error
- No CSRF required (GET request)

### localStorage Tracking (lists.js)
- Persistent job tracking via `localStorage.setItem/getItem`
- Storage key: `listarr_running_jobs`
- Tracks `{listId: {startTime: timestamp}}` for timeout calculation
- State persists across page navigation

### Polling Implementation (lists.js)
- `pollJobStatus()` polls `/lists/<id>/status` every 2 seconds
- `AbortController` per poller for clean cancellation
- 5-minute timeout with warning toast and button restoration
- `restoreRunningStates()` called on page load to resume polling
- `cleanupPolling()` on `beforeunload` to abort active requests

### UI Feedback
- "Import started" info toast on 202 response
- Color-coded result toasts:
  - Green (success): all items added successfully
  - Yellow (warning): some items failed
  - Red (error): all items failed or job error
- Button shows "Running..." until completion
- Client-side duplicate prevention with warning toast

## Deviations from Plan

None - plan executed exactly as written.

## Files Modified

| File | Changes |
|------|---------|
| `listarr/routes/lists_routes.py` | Added ThreadPoolExecutor, job tracking, async run endpoint, status endpoint (+137 lines) |
| `listarr/static/js/lists.js` | Added localStorage helpers, polling logic, state restoration (+292 lines, -27 lines) |

## Commits

| Hash | Message |
|------|---------|
| fc08a25 | feat(05-02): make run_list_import async with ThreadPoolExecutor |
| f72aee2 | feat(05-02): add GET /lists/<id>/status endpoint for polling |
| b7692d7 | feat(05-02): implement localStorage tracking and polling |

## Verification Status

| Criteria | Status |
|----------|--------|
| POST /lists/<id>/run returns 202 immediately | Pass |
| Background job runs via ThreadPoolExecutor | Pass |
| GET /lists/<id>/status returns status with result | Pass |
| Running state persists in localStorage | Pass |
| Returning to page restores "Running..." state | Pass |
| Polling detects completion with color-coded toast | Pass |
| Same list cannot run twice (server 400 + client warning) | Pass |
| Different lists can run in parallel | Pass |
| 5-minute timeout with warning toast | Pass |
| AbortController cleanup on unload | Pass |
| All 363 tests pass | Pass |

## Technical Details

### Backend Architecture
```python
# Module-level state
_running_jobs = {}  # {list_id: {'status': str, 'started_at': datetime, 'result': dict}}
_jobs_lock = threading.Lock()
_executor = None  # Lazy-initialized ThreadPoolExecutor

# Endpoint flow
POST /lists/<id>/run:
  1. Check list exists and is active
  2. Check not already running (with lock)
  3. Mark as running in _running_jobs
  4. Submit _run_import_job to executor
  5. Return 202 immediately

GET /lists/<id>/status:
  1. Check in-memory job state
  2. Return status + result if completed
  3. Clear job from memory after reporting
```

### Frontend Architecture
```javascript
// Constants
STORAGE_KEY = "listarr_running_jobs"
POLL_INTERVAL_MS = 2000
TIMEOUT_MS = 300000 (5 minutes)

// Flow
runList(listId):
  1. Check localStorage (client-side duplicate prevention)
  2. POST /lists/<id>/run
  3. On 202: track in localStorage, start polling
  4. Button stays disabled until completion

pollJobStatus(listId):
  1. Check timeout elapsed
  2. GET /lists/<id>/status
  3. If completed: show toast, restore button, remove from localStorage
  4. If running: schedule next poll
  5. If idle: clean up (server restart case)

restoreRunningStates() on page load:
  1. Read localStorage
  2. For each tracked job: set button state, start polling
```

### Key Design Decisions
- **In-memory job tracking:** Simple for MVP, jobs lost on server restart (acceptable for manual trigger)
- **localStorage vs sessionStorage:** localStorage persists across tabs and browser close
- **Lazy executor init:** Only create ThreadPoolExecutor when first job runs
- **5-minute timeout:** Long enough for large imports, short enough to detect stuck jobs

## Next Phase Readiness

Phase 5 complete. Ready for Phase 5 UAT:
- Run button triggers async import
- Status polling shows completion with results
- State persists across navigation
- All edge cases handled (timeout, duplicate, error)

## Metrics

- Duration: ~10 minutes
- Tasks: 3/3 complete
- Tests: 363 pass
- Lines added: ~420
- Lines removed: ~56
