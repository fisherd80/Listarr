---
status: resolved
trigger: "Investigate 2 related issues in the scheduler/job execution pipeline"
created: 2026-02-08T00:00:00Z
updated: 2026-02-08T00:20:00Z
---

## Current Focus

hypothesis: Root causes confirmed for both issues
test: Document root causes and proposed solutions
expecting: Clear actionable fixes for both issues
next_action: Update resolution section with root causes and fix proposals

## Symptoms

**Issue 1 - Schedule runs when service is down:**
expected: Scheduled jobs should validate that the target service (Radarr/Sonarr) is reachable before executing the import
actual: Schedule fires regardless of service availability, producing massive error output with many failed items
errors: Massive number of errors when service is offline
reproduction: Have a scheduled list targeting Radarr/Sonarr, take the service offline, wait for schedule to trigger
started: Has always been this way - no pre-flight check was ever implemented

**Issue 2 - Timeout is static, not activity-based:**
expected: Timeout should detect when a service has gone offline or stopped accepting items (activity-based/idle timeout). As long as items are being successfully added/skipped, the job should continue.
actual: Fixed 10-minute timeout (JOB_TIMEOUT_SECONDS = 600) expires on large jobs even though items are actively being processed. Job gets marked as "timed out" but the results show all items were added/skipped successfully - meaning the work completed but was incorrectly marked as failed.
errors: Jobs marked as "failed" with timeout even though all items processed successfully
reproduction: Run a large import that takes >10 minutes of processing time
started: Has always been this way - timeout was implemented as fixed wall-clock

## Eliminated

## Evidence

- timestamp: 2026-02-08T00:10:00Z
  checked: scheduler.py:170-212 (_run_scheduled_import function)
  found: No service health check before submitting job. Flow is: check pause state → check list exists → check list active → check overlap → submit_job. No validation that target service (Radarr/Sonarr) is reachable.
  implication: Issue 1 confirmed - scheduled imports fire regardless of service availability

- timestamp: 2026-02-08T00:10:01Z
  checked: scheduler.py:208 (job submission call)
  found: Calls submit_job(list_id, list_obj.name, _app, triggered_by="scheduled") with no pre-flight check
  implication: submit_job in job_executor.py receives jobs without knowing if service is available

- timestamp: 2026-02-08T00:10:02Z
  checked: job_executor.py:21 (JOB_TIMEOUT_SECONDS constant)
  found: JOB_TIMEOUT_SECONDS = 600 (10 minutes), used as fixed wall-clock timeout
  implication: Issue 2 confirmed - timeout is static, not activity-based

- timestamp: 2026-02-08T00:10:03Z
  checked: job_executor.py:104-107 (timeout timer setup)
  found: threading.Timer(JOB_TIMEOUT_SECONDS, lambda: _trigger_timeout(job_id)) - fires after 600 seconds regardless of job activity
  implication: Timer starts at job submission and fires unconditionally after 10 minutes, even if job is actively processing items

- timestamp: 2026-02-08T00:10:04Z
  checked: job_executor.py:119-125 (_trigger_timeout function)
  found: Simply sets stop_event when timer fires, no check for recent activity
  implication: No logic to detect "job is still making progress" vs "job is hung"

- timestamp: 2026-02-08T00:10:05Z
  checked: arr_service.py:66-85 (validate_api_key function)
  found: Function exists that calls /api/v3/system/status to validate service is reachable. Returns bool.
  implication: Pre-flight health check functionality already exists and could be called before scheduling jobs

- timestamp: 2026-02-08T00:15:00Z
  checked: job_executor.py:128-167 (_execute_job function)
  found: Flow is: (1) check stop_event before starting, (2) run import_list(), (3) check stop_event after import, (4) mark completed or timeout
  implication: Timeout checking happens ONLY before start and after completion. If import_list() takes >10 minutes, the timer fires during execution, sets stop_event, but job keeps running until import_list() returns. Then it checks stop_event and marks as timeout even if all work completed successfully.

- timestamp: 2026-02-08T00:15:01Z
  checked: import_service.py:234-309 (_import_movies function)
  found: Loops through items with time.sleep(API_CALL_DELAY) = 0.2s between each. No check for stop_event during iteration.
  implication: Long imports (e.g., 200 items = 40+ seconds minimum) have no way to detect timeout mid-execution. Job processes all items even after timeout fires.

- timestamp: 2026-02-08T00:15:02Z
  checked: import_service.py:312-413 (_import_series function)
  found: Same pattern - loops through items with delays, no stop_event check
  implication: Both import functions are timeout-unaware. They complete their work regardless of timeout.

- timestamp: 2026-02-08T00:15:03Z
  checked: job_executor.py:149-152 (post-import timeout check)
  found: After import_list() returns, checks if stop_event.is_set() and calls _mark_job_timeout() which marks job.status="failed"
  implication: This is the root of "job succeeded but marked as timeout" issue. The import completed successfully (all items processed), but because timer fired during execution, it's incorrectly marked as failed.

## Resolution

root_cause:

**Issue 1 - No Service Health Check:**
File: `listarr/services/scheduler.py`
Location: `_run_scheduled_import()` function (lines 170-212)
Problem: Scheduled jobs execute without validating that the target service (Radarr/Sonarr) is reachable. The function checks global pause state, list existence, list active status, and overlap detection, but never validates the target service API is responding before calling `submit_job()`. This causes jobs to run against offline services, generating massive error output as each item in the list fails when trying to add to an unreachable service.

Root cause mechanism:
1. Scheduler fires at cron time
2. `_run_scheduled_import()` checks pause/active/overlap
3. Calls `submit_job()` directly without service health check
4. Job executor starts import
5. `import_service.import_list()` attempts to add items
6. Every single item fails because service is unreachable
7. Job completes with 100% failure rate

The `arr_service.validate_api_key()` function (lines 66-85) already exists and could be used for pre-flight validation, but is never called from the scheduler path.

**Issue 2 - Static Wall-Clock Timeout:**
Files: `listarr/services/job_executor.py`, `listarr/services/import_service.py`
Locations:
- `job_executor.py`: Lines 21 (JOB_TIMEOUT_SECONDS), 104-107 (timer setup), 119-125 (_trigger_timeout)
- `import_service.py`: Lines 234-309 (_import_movies), 312-413 (_import_series)

Problem: Timeout is implemented as a fixed 10-minute wall-clock timer that starts when the job is submitted and fires unconditionally after 600 seconds. This is the wrong timeout model for batch processing jobs. The current implementation:

1. Starts timer at job submission (line 105)
2. Timer fires after 600 seconds regardless of job activity (line 105)
3. Sets `stop_event` when timer fires (line 125)
4. Import functions (`_import_movies`, `_import_series`) have no awareness of `stop_event` - they loop through all items without checking timeout
5. After import completes, `_execute_job()` checks `stop_event` (line 150) and marks job as "failed" if set (line 151)

This creates false failures: A large import that takes 15 minutes to process 500 items will complete successfully (all items added/skipped), but because the timer fired at the 10-minute mark, the job is marked as "failed" with error message "Job timed out" even though all work completed.

The desired behavior is an **idle timeout** or **activity-based timeout**:
- If items are actively being processed (added/skipped every few seconds), the job should continue
- Only timeout if the job appears hung (no progress for N seconds)
- Alternatively: remove timeout entirely or make it much larger (e.g., 1+ hour) for batch jobs where progress rate varies by list size

fix:

**Proposed Fix for Issue 1:**

In `listarr/services/scheduler.py`, modify `_run_scheduled_import()` to add pre-flight service health check:

1. After checking list exists and is active (around line 199)
2. Before checking overlap (line 202)
3. Add service health validation:
   ```python
   # Pre-flight: validate target service is reachable
   service_config = ServiceConfig.query.filter_by(service=list_obj.target_service).first()
   if not service_config:
       logger.error(f"Service {list_obj.target_service} not configured for list {list_id}")
       return

   # Decrypt API key and test connection
   from listarr.services.crypto_utils import decrypt_data
   from listarr.services.arr_service import validate_api_key

   try:
       api_key = decrypt_data(service_config.api_key_encrypted)
       if not validate_api_key(service_config.base_url, api_key):
           logger.warning(f"Service {list_obj.target_service} is unreachable, skipping scheduled import for list {list_id}")
           return
   except Exception as e:
       logger.error(f"Error validating service for list {list_id}: {e}")
       return
   ```

This prevents job submission if service is down, avoiding the cascade of item-level failures.

**Proposed Fix for Issue 2:**

Two implementation options:

**Option A: Activity-Based Timeout (Recommended)**
Modify `job_executor.py` to track last activity timestamp and implement idle timeout:

1. Replace fixed timer with periodic check (e.g., every 30 seconds)
2. Track `last_activity_time` (updated when items are added/skipped)
3. Timeout only if `(current_time - last_activity_time) > IDLE_TIMEOUT_SECONDS` (e.g., 300 = 5 minutes idle)
4. Pass `stop_event` and `last_activity_tracker` to `import_service.import_list()`
5. Modify `_import_movies()` and `_import_series()` to:
   - Check `stop_event.is_set()` in each iteration loop
   - Update `last_activity_time` after each successful add/skip
   - Break early if timeout detected

This requires:
- Change `import_list()` signature to accept `stop_event` and `activity_tracker`
- Modify import loops to check timeout and update activity
- Replace fixed timer with idle detection logic

**Option B: Remove/Increase Timeout (Simpler)**
1. Increase `JOB_TIMEOUT_SECONDS` from 600 to much larger value (3600 = 1 hour, or even remove entirely)
2. Rational: Batch import jobs complete when they finish processing all items. Natural termination is list completion. A 10-minute limit is arbitrary and too short for large lists.
3. If timeout is for "runaway jobs", current implementation doesn't help (job completes before timeout is checked)
4. Simpler approach: trust that jobs complete naturally, log/monitor for jobs that run unusually long

**Recommendation:** Start with Option B (increase timeout to 3600 seconds or remove limit entirely) as it's simpler and addresses the immediate false-failure issue. Implement Option A only if there's evidence of actual runaway jobs that need detection.

verification:

**Issue 1 Verification Plan:**
1. Configure a scheduled list targeting Radarr/Sonarr
2. Stop the target service (docker stop radarr/sonarr)
3. Wait for schedule trigger time
4. Verify: Scheduler logs show "Service unreachable, skipping scheduled import"
5. Verify: No job record created in database
6. Verify: No cascade of item-level errors
7. Restart service, wait for next schedule trigger
8. Verify: Job executes successfully when service is online

**Issue 2 Verification Plan:**
1. Create a large list (200+ items) that will take >10 minutes to import
2. Execute manual import
3. Monitor job execution time
4. If using Option A (activity timeout):
   - Verify job continues past 10 minutes while actively processing
   - Verify job times out only if no activity for idle period
5. If using Option B (increased timeout):
   - Verify job completes successfully with status="completed"
   - Verify all items processed and recorded in job_items table
   - Verify no false "timed out" errors for long-running jobs
6. Test actual timeout case: introduce artificial delay/hang in import logic
7. Verify timeout still triggers for truly hung jobs

files_changed: []
