# Phase 7: Scheduler System - Research

**Researched:** 2026-02-05
**Domain:** Python cron-based job scheduling with Flask
**Confidence:** HIGH

## Summary

This phase implements cron-based scheduling for automated list imports. The research focused on three key areas: (1) scheduler architecture given the existing Flask/Gunicorn/ThreadPoolExecutor infrastructure, (2) cron expression parsing and validation, and (3) UI patterns for schedule management.

The existing codebase already has a robust job execution framework (job_executor.py with ThreadPoolExecutor, Job model with triggered_by field, is_list_running() for overlap detection). The scheduler layer integrates on top of this foundation rather than replacing it.

**Primary recommendation:** Use APScheduler 3.11.x with BackgroundScheduler running in a single dedicated worker, leveraging the existing job_executor.submit_job() for actual execution. Use cronsim for cron expression validation and human-readable descriptions.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.11.2 | Cron-based job scheduling | Industry standard for Python, built-in cron trigger, pause/resume support, Flask integration |
| cronsim | 2.7 | Cron expression parsing/validation | Actively maintained (Oct 2025), matches Debian cron behavior, explain() method for UI |
| cron-descriptor | 2.0.5 | Human-readable cron descriptions | Multi-language support, converts cron to "Every day at 2 PM" style text |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Flask-APScheduler | 1.13.1 | Flask integration for APScheduler | Optional - provides REST API for job management (not needed for this phase) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler | Custom scheduler with threading.Timer | APScheduler handles edge cases (DST, missed jobs, timezones) that custom code would need to implement |
| cronsim | croniter | croniter is unmaintained as of Dec 2024 (EU CRA compliance), scheduled for potential unpublishing |
| In-process scheduler | System cron + Flask CLI | Would separate concerns but adds deployment complexity for a self-contained Docker app |

**Installation:**
```bash
pip install APScheduler==3.11.2 cronsim==2.7 cron-descriptor==2.0.5
```

## Architecture Patterns

### Recommended Project Structure
```
listarr/
├── services/
│   ├── job_executor.py      # (existing) ThreadPoolExecutor execution
│   └── scheduler.py         # (new) APScheduler wrapper
├── models/
│   ├── lists_model.py       # (existing) schedule_cron column
│   └── service_config_model.py  # Add scheduler_paused boolean
├── routes/
│   └── schedule_routes.py   # (new) Schedule page and API
└── templates/
    └── schedule.html        # (new) Schedule management page
```

### Pattern 1: Scheduler as Singleton Service
**What:** Single APScheduler instance initialized at app startup, controlled via module-level functions
**When to use:** When scheduler needs to survive request context and run independently
**Example:**
```python
# listarr/services/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from cronsim import CronSim
from datetime import datetime

_scheduler = None

def init_scheduler(app):
    """Initialize scheduler at app startup (call from create_app)."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(
        timezone=app.config.get('SCHEDULER_TIMEZONE', 'UTC'),
        job_defaults={
            'coalesce': True,  # Combine missed runs into one
            'max_instances': 1,  # Never run same job concurrently
            'misfire_grace_time': 60  # Allow 60s grace for missed jobs
        }
    )
    _scheduler.start()

    # Load existing schedules from database
    with app.app_context():
        _load_schedules_from_db(app)

def schedule_list(list_id, cron_expression, app):
    """Add or update schedule for a list."""
    job_id = f"list_{list_id}"

    # Remove existing job if present
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    # Add new job
    _scheduler.add_job(
        _run_scheduled_import,
        CronTrigger.from_crontab(cron_expression),
        id=job_id,
        args=[list_id, app],
        replace_existing=True
    )

def _run_scheduled_import(list_id, app):
    """Execute scheduled import via job_executor."""
    from listarr.services.job_executor import is_list_running, submit_job
    from listarr.models.lists_model import List

    with app.app_context():
        list_obj = List.query.get(list_id)
        if not list_obj or not list_obj.is_active:
            return  # List deleted or disabled

        if is_list_running(list_id):
            app.logger.info(f"Skipping scheduled run for list {list_id} - already running")
            return

        submit_job(list_id, list_obj.name, app, triggered_by="scheduled")
```

### Pattern 2: Gunicorn Single-Worker for Scheduler
**What:** Configure Gunicorn to run scheduler in only one worker process
**When to use:** Required to prevent duplicate job execution across workers
**Example:**
```python
# gunicorn_config.py modification
import os

workers = int(os.environ.get('GUNICORN_WORKERS', 2))

def on_starting(server):
    """Called just before master process is initialized."""
    # Set flag for scheduler worker identification
    os.environ['SCHEDULER_WORKER'] = 'master'

def post_fork(server, worker):
    """Called after worker fork - only first worker runs scheduler."""
    if worker.age == 1:  # First worker
        os.environ['SCHEDULER_WORKER'] = 'true'
    else:
        os.environ['SCHEDULER_WORKER'] = 'false'

# In listarr/__init__.py create_app():
def create_app():
    # ... existing setup ...

    # Only initialize scheduler in designated worker
    if os.environ.get('SCHEDULER_WORKER') in ('true', 'master'):
        from listarr.services.scheduler import init_scheduler
        init_scheduler(app)
```

### Pattern 3: Cron Validation with Next Run Preview
**What:** Validate cron expressions before saving and show next run time
**When to use:** In schedule form submission and edit pages
**Example:**
```python
# Validation and next run calculation
from cronsim import CronSim, CronSimError
from cron_descriptor import get_description
from datetime import datetime, timezone

def validate_cron_expression(cron_expr):
    """
    Validate cron expression and return info.

    Returns:
        dict with 'valid', 'error', 'description', 'next_runs'
    """
    try:
        now = datetime.now(timezone.utc)
        it = CronSim(cron_expr, now)

        # Get next 3 runs for preview
        next_runs = [next(it) for _ in range(3)]

        # Get human-readable description
        description = get_description(cron_expr)

        return {
            'valid': True,
            'error': None,
            'description': description,
            'next_runs': [r.isoformat() for r in next_runs]
        }
    except (CronSimError, StopIteration) as e:
        return {
            'valid': False,
            'error': str(e),
            'description': None,
            'next_runs': []
        }
```

### Anti-Patterns to Avoid
- **Running scheduler in multiple workers:** Each worker creates its own scheduler, causing duplicate job execution
- **Storing APScheduler jobs in database jobstore:** Unnecessary complexity when List model already has schedule_cron column - use memory jobstore and reload on startup
- **Creating jobs at request time without app reference:** Background threads lose Flask app context; always pass app._get_current_object()
- **Using croniter for new code:** Library is unmaintained and may be unpublished from PyPI

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron expression parsing | Regex-based parser | cronsim | Edge cases: leap years, DST, month/weekday combinations, L/W/# specifiers |
| Cron to human text | String manipulation | cron-descriptor | 31 language localizations, handles all cron syntax variations |
| Job scheduling | threading.Timer loops | APScheduler | Handles missed jobs, timezone changes, pause/resume, graceful shutdown |
| Overlap prevention | Flag variables | APScheduler max_instances=1 + is_list_running() | Race conditions in multi-threaded environment |
| Next run calculation | datetime arithmetic | CronSim iterator | DST transitions, leap seconds, timezone-aware calculations |

**Key insight:** Cron scheduling appears simple (run something at a time) but edge cases accumulate: What if the server was off during scheduled time? What if DST causes an hour to repeat or skip? What if a job is still running when next trigger fires? Established libraries handle these; custom code will have bugs.

## Common Pitfalls

### Pitfall 1: Scheduler Running in Multiple Workers
**What goes wrong:** Jobs execute 2x, 4x, etc. depending on worker count
**Why it happens:** Each Gunicorn worker forks the app, including scheduler initialization
**How to avoid:** Use environment flag to only start scheduler in first worker (see Pattern 2)
**Warning signs:** Same job appearing multiple times in job history with identical timestamps

### Pitfall 2: Lost App Context in Scheduled Jobs
**What goes wrong:** SQLAlchemy errors, Flask g/current_app not available
**Why it happens:** APScheduler runs jobs in separate threads without Flask request context
**How to avoid:** Pass app to job function, wrap all DB operations in `with app.app_context():`
**Warning signs:** "Working outside of application context" errors in logs

### Pitfall 3: Jobs Running Indefinitely After App Shutdown
**What goes wrong:** Orphaned threads continue executing after SIGTERM
**Why it happens:** APScheduler scheduler.shutdown() not called
**How to avoid:** Register atexit handler or use signal handling to call scheduler.shutdown(wait=True)
**Warning signs:** Process hangs during shutdown, zombie processes

### Pitfall 4: Timezone Confusion
**What goes wrong:** Jobs run at wrong times after DST or for users in different timezones
**Why it happens:** Mixing naive and aware datetimes, not specifying scheduler timezone
**How to avoid:** Always use UTC in scheduler config, let user configure TZ via Docker env var
**Warning signs:** Jobs off by 1 hour after DST, logs showing unexpected execution times

### Pitfall 5: croniter Deprecation
**What goes wrong:** Package removed from PyPI after March 2025
**Why it happens:** Maintainer compliance with EU Cyber Resilience Act
**How to avoid:** Use cronsim instead of croniter for new code
**Warning signs:** DeprecationWarning in logs, pip install failures

## Code Examples

Verified patterns from official sources:

### APScheduler CronTrigger from Crontab String
```python
# Source: https://apscheduler.readthedocs.io/en/stable/modules/triggers/cron.html
from apscheduler.triggers.cron import CronTrigger

# Standard 5-field crontab: minute hour day month day_of_week
scheduler.add_job(my_function, CronTrigger.from_crontab('0 0 1-15 may-aug *'))

# With timezone
scheduler.add_job(my_function, CronTrigger.from_crontab('0 6 * * *', timezone='America/New_York'))
```

### APScheduler Pause/Resume
```python
# Source: https://apscheduler.readthedocs.io/en/stable/userguide.html
# Individual job control
scheduler.pause_job('my_job_id')
scheduler.resume_job('my_job_id')

# Global pause (all jobs)
scheduler.pause()
scheduler.resume()
```

### cronsim Validation and Iteration
```python
# Source: https://github.com/cuu508/cronsim
from cronsim import CronSim, CronSimError
from datetime import datetime

try:
    it = CronSim("0 6 * * MON-FRI", datetime.now())
    next_run = next(it)
    print(f"Next run: {next_run}")
except CronSimError as e:
    print(f"Invalid expression: {e}")

# Human-readable explanation
it = CronSim("0 0 * 2 MON#5", datetime.now())
print(it.explain())  # "At 00:00 on the 5th Monday of the month, only in February"
```

### cron-descriptor Human-Readable Output
```python
# Source: https://github.com/Salamek/cron-descriptor
from cron_descriptor import get_description

print(get_description("*/5 * * * *"))  # "Every 5 minutes"
print(get_description("0 0 * * 0"))    # "At 12:00 AM, only on Sunday"
print(get_description("0 6 * * 1-5"))  # "At 6:00 AM, Monday through Friday"
```

### Preset Schedule Definitions
```python
# Recommended presets for wizard dropdown (Claude's discretion)
SCHEDULE_PRESETS = [
    ('hourly', '0 * * * *', 'Every hour'),
    ('every_6h', '0 */6 * * *', 'Every 6 hours'),
    ('daily', '0 0 * * *', 'Daily at midnight'),
    ('daily_6am', '0 6 * * *', 'Daily at 6 AM'),
    ('weekly', '0 0 * * 0', 'Weekly on Sunday'),
    ('custom', None, 'Custom cron expression'),
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| croniter for parsing | cronsim | Dec 2024 | croniter unmaintained, switch to avoid future breakage |
| APScheduler 3.x with database jobstore | APScheduler 3.x with memory jobstore | Current | Simpler when schedules already in app DB |
| Flask-APScheduler extension | Direct APScheduler + manual Flask integration | Current | Extension adds overhead for simple use cases |

**Deprecated/outdated:**
- croniter: Unmaintained as of Dec 2024, potential PyPI removal after Mar 2025
- APScheduler 4.x alpha: Available but not stable, stick with 3.11.x

## Open Questions

Things that couldn't be fully resolved:

1. **Gunicorn worker identification reliability**
   - What we know: Using worker.age == 1 or first forked worker works in testing
   - What's unclear: Behavior under high load with worker recycling
   - Recommendation: Test with `max_requests` worker recycling; fall back to file lock if issues arise

2. **Scheduler persistence across worker restart**
   - What we know: Memory jobstore loses jobs on restart; reload from DB on startup
   - What's unclear: Race condition window during worker restart
   - Recommendation: Accept brief window; jobs will be reloaded within seconds

## Sources

### Primary (HIGH confidence)
- APScheduler 3.11.2 official docs - https://apscheduler.readthedocs.io/en/stable/ (userguide, faq, triggers/cron)
- cronsim 2.7 GitHub - https://github.com/cuu508/cronsim (README, usage examples)
- cron-descriptor 2.0.5 GitHub - https://github.com/Salamek/cron-descriptor (README)

### Secondary (MEDIUM confidence)
- Flask-APScheduler tips - https://viniciuschiele.github.io/flask-apscheduler/rst/tips.html (worker issues)
- APScheduler GitHub issues #218, #160 - Gunicorn multi-worker solutions

### Tertiary (LOW confidence)
- croniter deprecation - https://github.com/pallets-eco/croniter/issues/144 (status may change)
- Community blog posts on APScheduler patterns (verify against official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - APScheduler is well-documented, cronsim is actively maintained
- Architecture: HIGH - Patterns verified against official docs and project's existing code
- Pitfalls: MEDIUM - Based on GitHub issues and community reports, not all personally verified

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - APScheduler is stable, cronsim actively maintained)
