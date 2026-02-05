---
phase: 07
plan: 02
subsystem: scheduler
completed: 2026-02-05
duration: 6 minutes

requires:
  - 07-01

provides:
  - scheduler service with APScheduler integration
  - automatic cron-based list import execution
  - global pause/resume functionality
  - overlap detection for scheduled jobs

affects:
  - 07-03 (scheduler UI controls will use these functions)
  - 07-04 (list edit form will use validate_cron_expression)

tech-stack:
  added:
    - APScheduler BackgroundScheduler
    - CronTrigger for job scheduling
    - cronsim for cron validation
    - cron-descriptor for human-readable descriptions
  patterns:
    - Singleton scheduler instance (module-level)
    - First worker scheduler pattern (SCHEDULER_WORKER env var)
    - App context management for database access
    - Graceful shutdown with atexit handler

key-files:
  created:
    - listarr/services/scheduler.py (346 lines)
  modified:
    - listarr/__init__.py (added scheduler initialization)

decisions:
  - use-hasattr-for-proxy-check:
      context: Flask app vs proxy object detection
      decision: Use hasattr(app, '_get_current_object') to handle both cases
      rationale: Direct Flask app instances don't have _get_current_object, only proxies do
      alternatives: Always use app directly, but wouldn't work with current_app proxy
  - tick-after-advance:
      context: cronsim next_runs calculation
      decision: Call tick() after each advance() to move forward 1 second
      rationale: advance() finds next match but stays at that time, need to move forward to find subsequent matches
      alternatives: Create new CronSim instances, but less efficient

commits:
  - ccdf760: feat(07-02) create scheduler service
  - cc72ceb: feat(07-02) integrate scheduler into app initialization
---

# Phase 7 Plan 02: Scheduler Service Summary

**One-liner:** APScheduler-based scheduler service with cron validation, job execution via job_executor, and global pause toggle

## What Was Built

### 1. Scheduler Service Module (scheduler.py)

Created comprehensive scheduler service with:

**Core Functions:**
- `init_scheduler(app)` - Initialize APScheduler in designated worker only
- `schedule_list(list_id, cron_expression)` - Register cron job for list
- `unschedule_list(list_id)` - Remove list from schedule
- `_run_scheduled_import(list_id)` - Execute scheduled import with checks
- `pause_scheduler()` / `resume_scheduler()` - Global pause toggle
- `is_scheduler_paused()` - Check pause state
- `get_next_run_time(list_id)` - Get next scheduled execution time
- `validate_cron_expression(cron_expr)` - Validate and describe cron patterns

**Key Features:**
- Singleton pattern with module-level `_scheduler` instance
- Only initializes in first worker (SCHEDULER_WORKER='true') or development
- BackgroundScheduler with UTC timezone (respects TZ env var)
- Job defaults: coalesce=True, max_instances=1, misfire_grace_time=60s
- Loads existing schedules from database on startup
- Atexit handler for graceful shutdown

**Execution Safeguards:**
- Global pause check (ServiceConfig.scheduler_paused)
- List existence and is_active validation
- Overlap detection via is_list_running()
- Exception handling with detailed logging

### 2. App Initialization Integration

**Changes to listarr/__init__.py:**
- Added conditional scheduler initialization after job recovery
- Checks SCHEDULER_WORKER env var (defaults to 'true' in development)
- Conditional import to avoid circular dependencies
- Logs "Scheduler initialized" on success

**Worker Pattern:**
- Gunicorn post_fork hook sets SCHEDULER_WORKER='true' for first worker (age==1)
- All other workers get SCHEDULER_WORKER='false'
- Prevents duplicate job execution across workers

### 3. Cron Validation and Description

**validate_cron_expression() Returns:**
- `valid` (bool) - Whether expression is valid
- `error` (str|None) - Error message if invalid
- `description` (str) - Human-readable description via cron-descriptor
- `next_runs` (list) - Next 3 execution times as ISO strings

**Examples:**
- `"0 0 * * *"` → "At 00:00" with next 3 daily occurrences
- `"0 * * * *"` → "Every hour" with next 3 hourly occurrences
- `"invalid"` → valid=False with error message

## Testing

### Test Results
- All 444 existing tests pass
- No regressions introduced
- Manual verification:
  - App starts successfully with scheduler
  - 2 scheduled lists loaded from database
  - validate_cron_expression returns correct results
  - SCHEDULER_WORKER=false skips initialization

### Integration Verified
- scheduler.py imports from job_executor (submit_job, is_list_running)
- __init__.py imports and calls init_scheduler
- Database queries work within app context
- APScheduler logs show jobs registered and scheduler started

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed cronsim next_runs calculation**
- **Found during:** Task 1 verification
- **Issue:** Used non-existent `next_time()` method, then `advance()` alone which returned same time 3 times
- **Fix:** Use `advance()` followed by `tick()` to move forward 1 second between matches
- **Files modified:** listarr/services/scheduler.py
- **Commit:** ccdf760

**2. [Rule 1 - Bug] Fixed _get_current_object() AttributeError**
- **Found during:** Task 2 verification
- **Issue:** Flask app instance doesn't have `_get_current_object()` method (only proxies do)
- **Fix:** Added hasattr check to handle both Flask app instances and proxy objects
- **Files modified:** listarr/services/scheduler.py
- **Commit:** cc72ceb

## Decisions Made

### Technical Decisions

**1. Singleton Scheduler Pattern**
- Store scheduler instance at module level like job_executor
- Prevents multiple scheduler instances
- Simplifies access from other modules

**2. App Context Management**
- Store app reference in module-level `_app` variable
- Use app.app_context() for all database operations
- Ensures SQLAlchemy queries have proper context

**3. First Worker Scheduler Pattern**
- Only worker with age==1 runs scheduler
- Set via Gunicorn post_fork hook (from plan 07-01)
- Prevents duplicate job execution in multi-worker deployments

**4. cronsim API Usage**
- Use `advance()` to find next matching time
- Call `tick()` after advance() to move forward
- Required to generate multiple next_runs without duplicates

**5. Graceful Error Handling**
- Log errors but don't crash on schedule load failures
- Continue execution if individual list schedule fails
- Return True (paused) on error in is_scheduler_paused()

## Next Phase Readiness

### Ready for Phase 7 Plan 03 (Scheduler UI Controls)
**Provides:**
- pause_scheduler() / resume_scheduler() for UI controls
- is_scheduler_paused() for status display
- get_next_run_time(list_id) for showing next execution

**API Surface for UI:**
```python
# Pause/resume
from listarr.services.scheduler import pause_scheduler, resume_scheduler, is_scheduler_paused

# Schedule management
from listarr.services.scheduler import schedule_list, unschedule_list, get_next_run_time

# Validation
from listarr.services.scheduler import validate_cron_expression
```

### Ready for Phase 7 Plan 04 (List Edit Form Schedule Field)
**Provides:**
- validate_cron_expression() for inline validation
- Returns human-readable description for user feedback
- Returns next 3 run times for preview

### No Blockers
- Scheduler service fully functional
- Integration with job_executor working
- Database queries successful
- All tests passing

## File Structure

```
listarr/
├── __init__.py                    # Scheduler initialization added
└── services/
    ├── scheduler.py              # NEW - 346 lines
    └── job_executor.py           # Used by scheduler (submit_job, is_list_running)
```

## Statistics

- **Files created:** 1
- **Files modified:** 1
- **Lines of code added:** ~360
- **Tests added:** 0 (no new tests in this plan)
- **Tests passing:** 444/444 (100%)
- **Commits:** 2

## Key Metrics

- Scheduler initialization time: <1 second
- Schedules loaded: 2 (from existing database)
- Timezone support: UTC default, respects TZ env var
- Misfire grace time: 60 seconds
- Job overlap protection: Via is_list_running() check

## Notes

### Scheduler Lifecycle
1. Gunicorn starts workers
2. post_fork hook identifies first worker (age==1)
3. First worker sets SCHEDULER_WORKER='true'
4. create_app() calls init_scheduler(app)
5. Scheduler loads schedules from database
6. BackgroundScheduler starts
7. Jobs execute at scheduled times
8. atexit handler shuts down gracefully

### Development vs Production
- **Development:** SCHEDULER_WORKER defaults to 'true' (no Gunicorn)
- **Production:** Only first Gunicorn worker has SCHEDULER_WORKER='true'

### Database Integration
- Queries ServiceConfig for scheduler_paused flag
- Queries List table for active schedules (schedule_cron not null, is_active=True)
- All queries within app.app_context()

### APScheduler Configuration
- **Scheduler type:** BackgroundScheduler (non-blocking)
- **Timezone:** UTC (or TZ env var)
- **Coalesce:** True (combine missed runs)
- **Max instances:** 1 (prevent concurrent executions)
- **Misfire grace:** 60 seconds

## Future Enhancements

### For Later Phases
1. **Scheduler status API endpoint** (Plan 07-03)
   - GET /api/scheduler/status
   - Returns is_paused, active_jobs count, next_run times

2. **Schedule preview in UI** (Plan 07-04)
   - Show next 3 run times when editing list
   - Validate cron on blur/change

3. **Scheduler metrics** (Future)
   - Track execution success rate
   - Monitor misfire frequency
   - Alert on repeated failures

### Potential Improvements
1. **Persistent job store** - Use database instead of memory (APScheduler supports SQLAlchemy)
2. **Schedule history** - Log when schedules are added/removed/modified
3. **Timezone per list** - Allow lists to have different timezones
4. **Schedule templates** - Common patterns like "daily at midnight", "every 6 hours"

## Dependencies

### Runtime Dependencies (Already Installed)
- APScheduler==3.11.2
- cronsim==2.7
- cron-descriptor==2.0.5

### Integration Dependencies
- job_executor.py (submit_job, is_list_running)
- ServiceConfig model (scheduler_paused flag)
- List model (schedule_cron, is_active)

## Implementation Quality

### Code Quality
- Clear function names and docstrings
- Comprehensive error handling
- Detailed logging at appropriate levels
- Module-level comments explaining patterns

### Testing Coverage
- All existing tests pass (444/444)
- Manual verification successful
- Integration points verified

### Production Readiness
- Graceful shutdown handler
- Error recovery on schedule load failures
- Safe defaults (paused on error)
- Worker isolation (first worker pattern)

---

**Phase Status:** 2/? plans complete
**Next Plan:** 07-03 (Scheduler UI Controls)
