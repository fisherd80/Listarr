# Phase 6: Job Execution Framework - Research

**Researched:** 2026-01-25
**Domain:** Flask background job processing with SQLite persistence
**Confidence:** MEDIUM-HIGH

## Summary

This phase transitions the existing in-memory job tracking (Phase 5) to a persistent database-backed system with proper execution tracking, retry logic, and history display. The key architectural decision is to **extend the existing ThreadPoolExecutor pattern** rather than introducing new job queue infrastructure (Celery/RQ), which aligns with the project's lightweight single-container deployment model.

The research identified that:
1. The existing `ThreadPoolExecutor(max_workers=3)` pattern is appropriate for this use case (I/O-bound API calls, modest concurrency needs)
2. SQLite with WAL mode can handle the concurrent read/write patterns this phase introduces
3. Tenacity is the standard Python library for retry with exponential backoff
4. Job timeouts require cooperative cancellation since Python threads cannot be forcefully terminated
5. Flask app context management requires careful handling in background threads

**Primary recommendation:** Keep the current ThreadPoolExecutor architecture, add Tenacity for retry logic, enable SQLite WAL mode, and implement cooperative timeout handling with threading.Event.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask-SQLAlchemy | 3.1.1 | Database ORM | Already in use; provides scoped_session for thread safety |
| SQLAlchemy | 2.0.44 | Database toolkit | Already in use; handles connection pooling |
| concurrent.futures | stdlib | ThreadPoolExecutor | Already in use from Phase 5; appropriate for I/O-bound tasks |
| threading | stdlib | Lock, Event | Already in use; needed for cooperative cancellation |

### New Dependencies

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | ^8.2.0 | Retry with backoff | API call retries within import jobs |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ThreadPoolExecutor | Celery + Redis | Overkill for 3 concurrent jobs; adds infrastructure complexity |
| ThreadPoolExecutor | Flask-Executor | Nice wrapper but adds dependency; current manual context push works |
| tenacity | Manual retry loop | Tenacity handles edge cases (jitter, logging, statistics) that manual loops miss |
| SQLite | PostgreSQL | SQLite is sufficient for single-container deployment; decision already locked |

**Installation:**
```bash
pip install tenacity>=8.2.0
```

## Architecture Patterns

### Recommended Project Structure
```
listarr/
├── services/
│   ├── import_service.py       # Existing import logic
│   └── job_executor.py         # NEW: Job execution orchestration
├── models/
│   └── jobs_model.py           # UPDATE: Enhanced Job model
├── routes/
│   ├── lists_routes.py         # UPDATE: Remove in-memory tracking
│   └── jobs_routes.py          # UPDATE: Jobs page API endpoints
└── templates/
    └── jobs.html               # UPDATE: Jobs page UI
```

### Pattern 1: App Context Push in Background Threads

**What:** Manually push Flask app context when accessing database in background threads
**When to use:** Every background job that needs database access

**Example:**
```python
# Source: Flask documentation + existing Phase 5 pattern
def _run_import_job(list_id, app):
    """Background job that runs with proper Flask context."""
    with app.app_context():
        try:
            # Create job record first
            job = Job(list_id=list_id, status='running', started_at=datetime.now(timezone.utc))
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Run import...
            result = import_list(list_id)

            # Update job record
            job = Job.query.get(job_id)
            job.status = 'completed'
            job.finished_at = datetime.now(timezone.utc)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Update job as failed
```

**Critical:** Always pass `app._get_current_object()` to background threads, not `current_app`.

### Pattern 2: Tenacity Retry with Exponential Backoff

**What:** Wrap retry-able operations with exponential backoff decorator
**When to use:** External API calls (TMDB, Radarr, Sonarr)

**Example:**
```python
# Source: Tenacity documentation
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),  # Max 3 attempts
    wait=wait_exponential(multiplier=1, min=5, max=20),  # 5s, 10s, 20s backoff
    retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
    reraise=True  # Re-raise after final failure
)
def call_external_api(url, **kwargs):
    response = requests.get(url, **kwargs)
    response.raise_for_status()
    return response.json()
```

**For Phase 6:** Apply retry to the import_list function's API calls, not the entire job (avoid retrying partial imports).

### Pattern 3: Cooperative Timeout with threading.Event

**What:** Use a shared Event to signal job cancellation for timeout
**When to use:** Jobs that need to respect a timeout deadline

**Example:**
```python
# Source: Python concurrent.futures docs + SuperFastPython patterns
import threading
from concurrent.futures import ThreadPoolExecutor

# Shared stop events per job
_stop_events = {}
_stop_events_lock = threading.Lock()

def _run_job_with_timeout(job_id, list_id, app, stop_event):
    """Job that checks stop_event periodically."""
    with app.app_context():
        items = fetch_items()  # Fast operation

        for item in items:
            # Check timeout before each item
            if stop_event.is_set():
                # Save partial results, mark as timed out
                save_partial_results(job_id)
                raise TimeoutError("Job timed out")

            process_item(item)  # The slow operation

def submit_job_with_timeout(list_id, timeout_seconds=600):
    """Submit job and monitor for timeout."""
    stop_event = threading.Event()

    with _stop_events_lock:
        _stop_events[list_id] = stop_event

    future = executor.submit(_run_job_with_timeout, job_id, list_id, app, stop_event)

    # Schedule timeout
    def timeout_callback():
        stop_event.set()

    timer = threading.Timer(timeout_seconds, timeout_callback)
    timer.start()

    # When job completes, cancel timer
    def cleanup(f):
        timer.cancel()
        with _stop_events_lock:
            _stop_events.pop(list_id, None)

    future.add_done_callback(cleanup)
```

**Important:** The 10-minute timeout means we check `stop_event.is_set()` before each item import (not each API call).

### Pattern 4: SQLite WAL Mode for Concurrent Access

**What:** Enable Write-Ahead Logging for better concurrent read/write performance
**When to use:** At application startup

**Example:**
```python
# Source: SQLAlchemy docs + Simon Willison TIL
from sqlalchemy import event
from listarr import db

def init_sqlite_wal(app):
    """Enable WAL mode and set busy timeout for SQLite."""

    @event.listens_for(db.engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")  # 5 second wait on locks
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
```

**Place this in:** `listarr/__init__.py` after `db.init_app(app)`

### Pattern 5: App Restart Recovery

**What:** Mark interrupted jobs as failed on application startup
**When to use:** At application initialization

**Example:**
```python
# Source: Common pattern for job queue systems
def recover_interrupted_jobs(app):
    """Mark any 'running' jobs as failed on startup."""
    with app.app_context():
        running_jobs = Job.query.filter_by(status='running').all()
        for job in running_jobs:
            job.status = 'failed'
            job.error_message = 'Job interrupted by application restart'
            job.error_details = 'Application was restarted while job was running'
            job.finished_at = datetime.now(timezone.utc)

        if running_jobs:
            db.session.commit()
            app.logger.warning(f"Recovered {len(running_jobs)} interrupted jobs")
```

**Place this in:** `listarr/__init__.py` within `create_app()` after database init.

### Anti-Patterns to Avoid

- **Sharing Session across threads:** SQLAlchemy Session is NOT thread-safe. Always create a new session in each background thread via `with app.app_context()`.
- **Passing Flask proxies to threads:** Pass concrete objects, not `current_app` or `request`. Use `app._get_current_object()`.
- **Assuming future.cancel() works:** It only works for pending tasks, not running ones. Use cooperative cancellation.
- **Long transactions with SQLite:** Keep transactions short to minimize lock contention. Commit after each item, not batch.
- **Retry entire jobs:** Retry individual API calls within a job, not the whole job (avoids duplicate imports).

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Manual sleep loop | tenacity | Handles jitter, max delay, logging, statistics, edge cases |
| Thread-safe job tracking | Dict with manual locking | Database records | Persists across restarts, survives crashes |
| Job timeouts | Complex timer logic | threading.Event + Timer | Clean pattern, cancellable timer |
| SQLite concurrent writes | Hope for the best | WAL mode + busy_timeout | Proven solution for multi-threaded SQLite |

**Key insight:** The only custom logic needed is the orchestration glue. Every individual problem (retry, timeout, persistence, concurrency) has established solutions.

## Common Pitfalls

### Pitfall 1: Database Locked Errors

**What goes wrong:** Multiple background threads writing to SQLite simultaneously cause `OperationalError: database is locked`
**Why it happens:** SQLite allows only one writer at a time; default lock timeout is short
**How to avoid:**
1. Enable WAL mode (allows concurrent readers with one writer)
2. Set `busy_timeout=5000` (wait 5 seconds for locks)
3. Keep transactions short (commit after each item)
4. Use `db.session.rollback()` in exception handlers
**Warning signs:** Sporadic "database is locked" errors under load

### Pitfall 2: Context Not Available in Thread

**What goes wrong:** `RuntimeError: Working outside of application context` in background job
**Why it happens:** Flask contexts don't automatically propagate to new threads
**How to avoid:**
1. Always wrap background work in `with app.app_context():`
2. Pass `app._get_current_object()` to thread, not `current_app`
3. Access database only within the context block
**Warning signs:** RuntimeError about application or request context

### Pitfall 3: Stale Session State After Failure

**What goes wrong:** After a database error, subsequent operations fail with `InvalidRequestError: Can't reconnect until invalid transaction is rolled back`
**Why it happens:** Failed transactions leave the session in an invalid state
**How to avoid:**
1. Always call `db.session.rollback()` in exception handlers
2. Consider `db.session.remove()` at the end of background jobs
3. Use `try/except/finally` pattern for cleanup
**Warning signs:** Cascading errors after the first database failure

### Pitfall 4: Job Result Lost on Timeout

**What goes wrong:** Job times out and all processed items are lost
**Why it happens:** Timeout kills job before results are saved
**How to avoid:**
1. Commit after each successfully imported item (not batch)
2. On timeout, save partial results before marking failed
3. Track items_added/items_failed incrementally
**Warning signs:** User reports job "failed" but items were actually added

### Pitfall 5: Duplicate Jobs for Same List

**What goes wrong:** User rapidly clicks "Run" and multiple jobs start for the same list
**Why it happens:** Race condition between checking "is running" and starting job
**How to avoid:**
1. Check database for running job before starting (not just in-memory)
2. Use database-level unique constraint or status check
3. Return 409 Conflict if already running
**Warning signs:** Multiple "running" jobs for the same list in job history

## Code Examples

Verified patterns from official sources:

### Database Model Enhancement

```python
# Source: Phase 6 CONTEXT.md requirements
class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey("lists.id"))
    list_name = db.Column(db.String(255))  # NEW: Denormalized, survives list deletion

    status = db.Column(db.String(20))  # running/completed/failed
    started_at = db.Column(TZDateTime)
    completed_at = db.Column(TZDateTime)  # Renamed from finished_at
    duration = db.Column(db.Integer)  # NEW: Seconds

    triggered_by = db.Column(db.String(20), default="manual")  # NEW: manual/scheduled
    retry_count = db.Column(db.Integer, default=0)  # NEW

    items_found = db.Column(db.Integer, default=0)
    items_added = db.Column(db.Integer, default=0)
    items_skipped = db.Column(db.Integer, default=0)
    items_failed = db.Column(db.Integer, default=0)  # NEW

    error_message = db.Column(db.Text)  # User-friendly
    error_details = db.Column(db.Text)  # NEW: Technical stack trace
```

### Job Executor Service Skeleton

```python
# Source: Research synthesis
"""Job execution service with retry and timeout."""
import logging
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

from listarr import db
from listarr.models.jobs_model import Job
from listarr.services.import_service import import_list

logger = logging.getLogger(__name__)

# Configuration
MAX_WORKERS = 3
JOB_TIMEOUT_SECONDS = 600  # 10 minutes
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = (5, 10, 20)  # seconds

# Global executor (lazy init)
_executor = None
_stop_events = {}
_stop_events_lock = threading.Lock()


def get_executor():
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix='job_')
    return _executor


def is_list_running(list_id):
    """Check if a job for this list is currently running."""
    return Job.query.filter_by(list_id=list_id, status='running').first() is not None


def submit_job(list_id, list_name, app, triggered_by='manual'):
    """Submit a job for execution with timeout monitoring."""
    if is_list_running(list_id):
        raise ValueError(f"Job already running for list {list_id}")

    # Create stop event for timeout
    stop_event = threading.Event()
    with _stop_events_lock:
        _stop_events[list_id] = stop_event

    # Submit job
    future = get_executor().submit(
        _execute_job, list_id, list_name, triggered_by, stop_event, app
    )

    # Set up timeout timer
    timer = threading.Timer(JOB_TIMEOUT_SECONDS, lambda: stop_event.set())
    timer.start()

    def cleanup(f):
        timer.cancel()
        with _stop_events_lock:
            _stop_events.pop(list_id, None)

    future.add_done_callback(cleanup)

    return future
```

### Retry Decorator for API Calls

```python
# Source: Tenacity documentation
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

def create_retry_decorator():
    """Create retry decorator with configured backoff: 5s, 10s, 20s."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(5) | wait_fixed(10) | wait_fixed(20),  # Custom sequence
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )

# Alternative with true exponential: 5, 10, 20 approximation
api_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2.5, min=5, max=20),
    retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
    reraise=True
)
```

### Jobs Page API Endpoint

```python
# Source: Phase 6 CONTEXT.md requirements
@bp.route("/api/jobs")
def get_jobs():
    """
    Get paginated job history with optional filters.

    Query params:
        page: int (default 1)
        per_page: int (default 25, max 50)
        list_id: int (optional filter)
        status: string (optional filter: running/completed/failed)
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 50)
    list_id = request.args.get('list_id', type=int)
    status = request.args.get('status', type=str)

    query = Job.query.order_by(Job.started_at.desc())

    if list_id:
        query = query.filter_by(list_id=list_id)
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'jobs': [job.to_dict() for job in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| In-memory job tracking | Database persistence | Phase 6 | Jobs survive restarts |
| Manual retry loops | Tenacity decorators | 2020+ | Cleaner, more robust |
| Hope SQLite handles it | WAL mode + busy_timeout | SQLite 3.7+ | Better concurrency |
| future.cancel() for timeout | Cooperative cancellation | Python 3.x | Actually works |

**Deprecated/outdated:**
- `retrying` library: Use `tenacity` instead (better maintained, more features)
- Global threading.Lock for SQLite: Use WAL mode instead
- Flask-SQLAlchemy `SQLALCHEMY_POOL_SIZE`: Not applicable to SQLite

## Open Questions

Things that couldn't be fully resolved:

1. **Exact retry timing**
   - What we know: Tenacity supports `wait_exponential` with min/max bounds
   - What's unclear: Whether to use true exponential (5, 10, 20) or allow slight variance with jitter
   - Recommendation: Use fixed backoff `[5, 10, 20]` as specified in CONTEXT.md for predictability

2. **Job items persistence granularity**
   - What we know: JobItem model exists; can store per-item results
   - What's unclear: Performance impact of writing one JobItem per imported media
   - Recommendation: Keep JobItem writes; consider batch commits if performance issues arise

3. **Dashboard recent jobs count**
   - What we know: CONTEXT.md says 5 recent jobs on dashboard
   - What's unclear: Should this be configurable?
   - Recommendation: Hardcode 5 initially; extract to config later if requested

## Sources

### Primary (HIGH confidence)
- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/) - App context and session management
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) - SQLite dialect, WAL mode, events
- [Python concurrent.futures Documentation](https://docs.python.org/3/library/concurrent.futures.html) - ThreadPoolExecutor, Future.cancel() limitations
- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Retry decorators, backoff strategies

### Secondary (MEDIUM confidence)
- [Flask-Executor Documentation](https://flask-executor.readthedocs.io/) - Context wrapping patterns (verified with official Flask docs)
- [SQLite WAL Mode TIL](https://til.simonwillison.net/sqlite/enabling-wal-mode) - Simon Willison's practical WAL examples
- [SQLite Concurrent Writes Blog](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/) - Detailed concurrent write patterns

### Tertiary (LOW confidence - needs validation in implementation)
- SuperFastPython ThreadPoolExecutor patterns - Cooperative cancellation examples (could not fetch full content)
- Flask GitHub discussions - Context propagation edge cases

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing libraries + one well-established addition (tenacity)
- Architecture: MEDIUM-HIGH - Patterns verified with official docs; some integration specifics TBD
- Pitfalls: HIGH - Well-documented issues with SQLite concurrency and Flask contexts

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (stable technologies, 30 days)
