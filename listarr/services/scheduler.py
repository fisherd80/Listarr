"""
Scheduler Service
Manages APScheduler for automated list imports with cron schedules.
"""

import atexit
import logging
import os
import re
import threading
import zoneinfo
from dataclasses import dataclass, field
from datetime import datetime, timezone

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.util import astimezone
from cron_descriptor import get_description
from cronsim import CronSim
from cronsim.cronsim import CronSimError
from cryptography.fernet import InvalidToken
from requests.exceptions import RequestException
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from listarr import db
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.services.arr_service import validate_api_key
from listarr.services.crypto_utils import decrypt_data
from listarr.services.job_executor import is_list_running, submit_job
from listarr.utils.time_utils import (
    coerce_zone,
    get_app_timezone_fallback_name,
    get_app_timezone_name,
    resolve_db_timezone_string,
)

logger = logging.getLogger(__name__)

# Module-level scheduler instance (singleton pattern like job_executor)
_scheduler = None
_app = None
_reschedule_lock = threading.Lock()
_tz_poll_last_bad_value = None

# The timezone reschedule is one idempotent desired-vs-live diff (reconcile_scheduler_jobs),
# so there is no half-finished rebuild to describe and none of the old quarantine /
# incomplete-flag / reminder-countdown state. Two plain values are enough:
#
#   _unbuildable_crons  - {list_id: cron} from the last reconcile pass, overwritten
#                         wholesale each time. Defensive logging only: validate_cron_expression
#                         rejects an unbuildable cron at list-save time, so a stored row that
#                         builds no trigger is a near-impossibility.
#   _last_reconciled_tz - the tz_name of the last non-deferred full pass. The poll retries
#                         whenever the resolved zone name differs from this; a deferred
#                         (transient DB/lock) pass leaves it unchanged so the next tick retries.
_unbuildable_crons: dict[int, str] = {}
_last_reconciled_tz: str | None = None


@dataclass(frozen=True)
class ReconcileResult:
    """Outcome of one reconcile_scheduler_jobs() pass."""

    applied: int = 0
    removed: int = 0
    unbuildable: dict = field(default_factory=dict)
    deferred: bool = False
    pending: int = 0


# POSIX cron uses 0=Sunday; APScheduler's CronTrigger uses 0=Monday internally.
# Converting to name strings avoids the ambiguity entirely.
_POSIX_DOW_NAMES = {"0": "sun", "1": "mon", "2": "tue", "3": "wed", "4": "thu", "5": "fri", "6": "sat", "7": "sun"}


def _posix_cron_to_apscheduler(cron_expr):
    """Translate POSIX day-of-week numbers to name strings before handing to APScheduler.

    APScheduler's CronTrigger treats numeric day-of-week as 0=Monday (Python weekday),
    while POSIX cron uses 0=Sunday. '0 2 * * 1' would fire Tuesday in APScheduler
    but Monday in every standard cron tool. Name strings ('mon', 'tue', …) are
    unambiguous in both systems.

    Wildcards and step-only expressions (*/N) are left unchanged.
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        return cron_expr
    dow = parts[4]
    if dow == "*" or dow.startswith("*/") or not any(c.isdigit() for c in dow):
        return cron_expr
    parts[4] = re.sub(r"\b([0-7])\b", lambda m: _POSIX_DOW_NAMES.get(m.group(1), m.group(1)), dow)
    return " ".join(parts)


def _get_scheduler_timezone():
    """Return the configured scheduler timezone.

    Resolution order is AppConfig.timezone, live scheduler timezone, TZ env var,
    then UTC. This function never raises and always returns a tzinfo object.
    """
    # WR-05: bind once. shutdown_scheduler() nulls the global from the atexit handler on
    # another thread, so re-reading it between the check and the dereference would raise
    # AttributeError out of a function documented as never raising.
    scheduler = _scheduler

    stored = resolve_db_timezone_string()
    if stored:
        zone = coerce_zone(stored)
        if zone is not None:
            return zone
        logger.warning("Configured timezone %r could not be loaded by scheduler; falling back", stored)

    if scheduler is not None:
        return scheduler.timezone

    return coerce_zone(os.environ.get("TZ", "UTC")) or timezone.utc


def init_scheduler(app):
    """
    Initialize the scheduler service.

    Only initializes if SCHEDULER_WORKER env var is 'true' or running in development.
    Creates BackgroundScheduler with UTC timezone, loads existing schedules, and starts.

    Args:
        app: Flask app instance
    """
    global _scheduler, _app

    # Only initialize in designated worker or development mode
    scheduler_worker = os.environ.get("SCHEDULER_WORKER", "true")  # Default true for dev
    if scheduler_worker != "true":
        logger.debug("Scheduler not initialized in this worker")
        return

    if _scheduler is not None:
        logger.warning("Scheduler already initialized")
        return

    # Store app reference for later use
    # Use _get_current_object() if app is a proxy, otherwise use app directly
    _app = app._get_current_object() if hasattr(app, "_get_current_object") else app

    # Get timezone from the application resolver.
    tz = get_app_timezone_name()

    # Create scheduler with configuration
    _scheduler = BackgroundScheduler(
        timezone=tz,
        job_defaults={
            "coalesce": True,  # Combine multiple missed runs into one
            "max_instances": 1,  # Only one instance of each job at a time
            "misfire_grace_time": 3600,  # Jobs can run up to 1h late (handles container restarts)
        },
    )

    # Register shutdown handler
    atexit.register(lambda: shutdown_scheduler())

    # Load existing schedules from database
    _load_schedules_from_db()

    # Backstop that converges the live scheduler onto the AppConfig timezone and
    # retries a deferred reconcile. Settings saves trigger reconcile_scheduler_jobs
    # directly, so a slow interval is enough here - timezone changes are rare admin
    # actions and every tick logs at INFO.
    _scheduler.add_job(
        _tz_poll_tick,
        trigger="interval",
        seconds=300,
        id="_tz_poll",
        max_instances=1,
        coalesce=True,
    )

    # Start the scheduler
    _scheduler.start()
    logger.info(f"Scheduler initialized (timezone: {tz})")


def is_scheduler_worker() -> bool:
    """True when this process owns the APScheduler instance."""
    return _scheduler is not None


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    global _scheduler
    # WR-07: serialize with the reschedule/poll consumers so an in-flight rebuild
    # never dereferences a scheduler that was nulled mid-flight.
    with _reschedule_lock:
        if _scheduler is not None:
            _scheduler.shutdown(wait=False)
            _scheduler = None
            logger.info("Scheduler shutdown")


def _load_schedules_from_db():
    """Load all active list schedules from database and register with APScheduler."""
    if _app is None:
        logger.error("Cannot load schedules: app not initialized")
        return

    with _app.app_context():
        try:
            lists = List.active_scheduled_query().all()

            for list_obj in lists:
                try:
                    schedule_list(list_obj.id, list_obj.schedule_cron)
                    logger.info(f"Loaded schedule for list {list_obj.id}: {list_obj.schedule_cron}")
                except (ValueError, KeyError) as e:
                    logger.error(f"Failed to load schedule for list {list_obj.id}: {e}")

            logger.info(f"Loaded {len(lists)} scheduled lists")
        except OperationalError as e:
            logger.error(f"Failed to load schedules from database: {e}")


def reconcile_scheduler_jobs(tz_name, *, blocking=True) -> ReconcileResult:
    """Reconcile the live jobstore to the desired {job_id: trigger} set for ``tz_name``.

    One idempotent pass: compute the desired triggers from the active-scheduled lists,
    build every trigger up front, then apply the diff against the live jobs — add/replace
    what is present, remove what is absent. Running it twice with no DB change makes zero
    effective jobstore changes.

    Forward-only by construction: add_job is called without next_run_time, so the next
    fire is computed from now and misfire_grace_time is never consulted. The "remove
    absent" arm is the entire orphan-sweep responsibility.

    Returns a ReconcileResult. ``deferred=True`` means a transient decline (no scheduler
    in this process, lock contention, or a locked DB): nothing was applied and the caller
    or the poll should retry. ``_last_reconciled_tz`` only advances on a non-deferred pass.
    """
    global _last_reconciled_tz, _unbuildable_crons

    # WR-05: bind once. A concurrent shutdown_scheduler() nulls the global.
    scheduler = _scheduler
    if scheduler is None or _app is None:
        pending = 0
        if _app is not None:
            with _app.app_context():
                try:
                    pending = List.active_scheduled_query().count()
                except OperationalError:
                    pending = 0
        logger.debug("Scheduler not running in this worker; nothing to reconcile in-process")
        return ReconcileResult(deferred=False, pending=pending)

    acquired = _reschedule_lock.acquire(blocking=blocking)
    if not acquired:
        # A concurrent reconcile owns the outcome; the poll will see _last_reconciled_tz
        # unchanged and retry.
        logger.debug("Reconcile already in progress; deferring this attempt")
        return ReconcileResult(deferred=True)

    try:
        target = coerce_zone(tz_name)
        if target is None:
            # An unresolvable name is not retryable; the caller already fell back.
            logger.error("Cannot reconcile scheduler jobs: timezone %r does not resolve", tz_name)
            return ReconcileResult(deferred=False)

        with _app.app_context():
            try:
                rows = List.active_scheduled_query().all()
            except OperationalError as e:
                # A locked or unavailable DB is transient: defer, advance no state, let
                # the poll retry. No finite allowance to consume.
                logger.error(f"Failed to load schedules for scheduler reconcile: {e}")
                return ReconcileResult(deferred=True)

            # Build every trigger before any jobstore mutation, so construction can never
            # half-apply the diff.
            desired: dict[str, CronTrigger] = {}
            unbuildable: dict[int, str] = {}
            for row in rows:
                job_id = f"list_{row.id}"
                try:
                    desired[job_id] = CronTrigger.from_crontab(
                        _posix_cron_to_apscheduler(row.schedule_cron), timezone=target
                    )
                except (ValueError, KeyError):
                    unbuildable[row.id] = row.schedule_cron

            live_ids = {job.id for job in scheduler.get_jobs() if job.id.startswith("list_")}
            applied = 0
            removed = 0
            for job_id, trigger in desired.items():
                scheduler.add_job(
                    _run_scheduled_import,
                    trigger=trigger,
                    id=job_id,
                    args=[int(job_id[5:])],
                    name=f"List {job_id[5:]} import",
                    replace_existing=True,
                )
                applied += 1
            for job_id in live_ids - desired.keys():
                try:
                    scheduler.remove_job(job_id)
                    removed += 1
                except JobLookupError:
                    pass

            # Single assignment, after the apply loop: kept so get_next_run_time's
            # non-worker fallback and future schedule_list() calls default correctly. No
            # convergence logic reads it any more.
            scheduler.timezone = target
            _last_reconciled_tz = tz_name
            if unbuildable and set(unbuildable) != set(_unbuildable_crons):
                logger.warning(
                    "%d scheduled list(s) have a cron that builds no trigger and are not scheduled: %s",
                    len(unbuildable),
                    ", ".join(f"list {lid} ({cron!r})" for lid, cron in sorted(unbuildable.items())),
                )
            _unbuildable_crons = unbuildable

        logger.info(
            "Reconciled scheduler jobs into %s: %d applied, %d removed, %d unbuildable",
            tz_name,
            applied,
            removed,
            len(unbuildable),
        )
        return ReconcileResult(applied=applied, removed=removed, unbuildable=unbuildable, deferred=False, pending=0)
    finally:
        _reschedule_lock.release()


def _tz_poll_tick():
    """Converge the live scheduler onto the effective resolved app timezone."""
    global _tz_poll_last_bad_value

    scheduler = _scheduler
    if scheduler is None or _app is None:
        return

    with _app.app_context():
        try:
            stored = resolve_db_timezone_string(use_cache=False)
            if stored:
                try:
                    astimezone(stored)
                    desired = stored
                    _tz_poll_last_bad_value = None
                except (ValueError, TypeError, zoneinfo.ZoneInfoNotFoundError):
                    desired = get_app_timezone_fallback_name()
                    if _tz_poll_last_bad_value != stored:
                        logger.warning("Configured timezone %r could not be loaded; using %s", stored, desired)
                        _tz_poll_last_bad_value = stored
            else:
                desired = get_app_timezone_fallback_name()
                _tz_poll_last_bad_value = None

            if desired == (_last_reconciled_tz or ""):
                # The last non-deferred reconcile already targeted this zone. A deferred
                # (transient DB/lock) pass leaves _last_reconciled_tz unchanged, so this
                # tick retries.
                return

            reconcile_scheduler_jobs(desired, blocking=False)
        except (OperationalError, SQLAlchemyError) as e:
            logger.error(f"Timezone poll failed: {e}", exc_info=True)


def schedule_list(list_id, cron_expression):
    """
    Schedule a list for automatic import execution.

    Args:
        list_id: ID of the list to schedule
        cron_expression: Cron expression (e.g., "0 0 * * *")

    Raises:
        ValueError: If cron expression is invalid
    """
    # WR-05: bind once so a concurrent shutdown_scheduler() cannot null the global
    # between the guard below and any dereference that follows it.
    scheduler = _scheduler
    if scheduler is None:
        logger.debug("Scheduler not running in this worker — schedule saved to DB, skipping in-process update")
        return

    # Validate cron expression
    validation = validate_cron_expression(cron_expression)
    if not validation["valid"]:
        raise ValueError(f"Invalid cron expression: {validation['error']}")

    # Create job ID
    job_id = f"list_{list_id}"

    # CR-02: build the trigger before touching the existing job. If construction
    # fails (cronsim and APScheduler do not accept the same grammar), the list
    # keeps its current schedule instead of being silently unscheduled forever.
    try:
        trigger = CronTrigger.from_crontab(_posix_cron_to_apscheduler(cron_expression), timezone=scheduler.timezone)
    except (ValueError, KeyError) as e:
        logger.error(f"Failed to build trigger for list {list_id}: {e}")
        raise

    # WR-07: replace_existing makes the swap a single jobstore operation. The previous
    # remove-then-add left the list with no job at all if add_job raised, discarding the
    # old schedule the CR-02 comment above promises to keep.
    try:
        scheduler.add_job(
            _run_scheduled_import,
            trigger=trigger,
            id=job_id,
            args=[list_id],
            name=f"List {list_id} import",
            replace_existing=True,
        )
        logger.info(f"Scheduled list {list_id} with cron: {cron_expression}")
    except (ValueError, KeyError) as e:
        logger.error(f"Failed to schedule list {list_id}: {e}")
        raise


def unschedule_list(list_id):
    """
    Remove a list from the schedule.

    Args:
        list_id: ID of the list to unschedule
    """
    # WR-05: bind once (see schedule_list).
    scheduler = _scheduler
    if scheduler is None:
        logger.warning("Scheduler not initialized, cannot unschedule")
        return

    job_id = f"list_{list_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Unscheduled list {list_id}")


def _run_scheduled_import(list_id):
    """
    Execute a scheduled list import.

    Runs within app context, checks global pause state and overlap detection.

    Args:
        list_id: ID of the list to import
    """
    if _app is None:
        logger.error("Cannot run scheduled import: app not initialized")
        return

    with _app.app_context():
        try:
            # Check global pause state
            if is_scheduler_paused():
                logger.info(f"Scheduler paused, skipping list {list_id}")
                return

            # Get list details
            list_obj = db.session.get(List, list_id)
            if not list_obj:
                logger.error(f"List {list_id} not found, removing from schedule")
                unschedule_list(list_id)
                return

            if not list_obj.is_active:
                logger.info(f"List {list_id} is inactive, skipping")
                return

            # Pre-flight: validate target service is reachable
            service_config = ServiceConfig.query.filter_by(service=list_obj.target_service).first()
            if not service_config or not service_config.api_key_encrypted:
                logger.error(
                    f"Service {list_obj.target_service} not configured, "
                    f"skipping scheduled import for list {list_id} ({list_obj.name})"
                )
                return

            try:
                api_key = decrypt_data(service_config.api_key_encrypted)
                if not validate_api_key(service_config.base_url, api_key):
                    logger.warning(
                        f"Service {list_obj.target_service} is unreachable, "
                        f"skipping scheduled import for list {list_id} ({list_obj.name})"
                    )
                    return
            except (RequestException, ValueError, InvalidToken) as e:
                logger.error(f"Error validating {list_obj.target_service} for list {list_id}: {e}")
                return

            # Check for overlap (skip if already running)
            if is_list_running(list_id):
                logger.warning(f"List {list_id} ({list_obj.name}) already running, skipping scheduled execution")
                return

            # Submit job
            logger.info(f"Starting scheduled import for list {list_id} ({list_obj.name})")
            submit_job(list_id, list_obj.name, _app, triggered_by="scheduled")

        except (OperationalError, RequestException) as e:
            logger.error(f"Error running scheduled import for list {list_id}: {e}", exc_info=True)


def pause_scheduler():
    """Pause all scheduled job execution (global pause toggle)."""
    # WR-05: bind once (see schedule_list).
    scheduler = _scheduler
    if scheduler is None:
        logger.warning("Scheduler not initialized, cannot pause")
        return

    if _app is None:
        logger.error("Cannot pause scheduler: app not initialized")
        return

    with _app.app_context():
        try:
            # Update database
            config = ServiceConfig.query.first()
            if config:
                config.scheduler_paused = True
                db.session.commit()

            # Pause scheduler
            scheduler.pause()
            logger.info("Scheduler paused")
        except (OperationalError, RuntimeError) as e:
            logger.error(f"Failed to pause scheduler: {e}")
            raise


def resume_scheduler():
    """Resume all scheduled job execution."""
    # WR-05: bind once (see schedule_list).
    scheduler = _scheduler
    if scheduler is None:
        logger.warning("Scheduler not initialized, cannot resume")
        return

    if _app is None:
        logger.error("Cannot resume scheduler: app not initialized")
        return

    with _app.app_context():
        try:
            # Update database
            config = ServiceConfig.query.first()
            if config:
                config.scheduler_paused = False
                db.session.commit()

            # Resume scheduler
            scheduler.resume()
            logger.info("Scheduler resumed")
        except (OperationalError, RuntimeError) as e:
            logger.error(f"Failed to resume scheduler: {e}")
            raise


def is_scheduler_paused():
    """
    Check if scheduler is globally paused.

    Returns:
        bool: True if paused, False otherwise
    """
    if _app is None:
        return True  # Default to paused if app not initialized

    try:
        config = ServiceConfig.query.first()
        return config.scheduler_paused if config else False
    except OperationalError as e:
        logger.error(f"Failed to check scheduler pause state: {e}")
        return True  # Default to paused on error


def get_next_run_time(list_id):
    """
    Get the next scheduled run time for a list.

    This function works in both scheduler and non-scheduler workers:
    - In scheduler worker: Returns next_run_time from APScheduler job (fast, accurate)
    - In non-scheduler worker: Calculates next run time from cron expression (fallback)

    Args:
        list_id: ID of the list

    Returns:
        datetime: Next run time (timezone-aware) or None if not scheduled
    """
    # WR-05: bind once (see schedule_list).
    scheduler = _scheduler
    if scheduler is not None:
        # Scheduler worker: get next run time from APScheduler (preferred path)
        job_id = f"list_{list_id}"
        job = scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None

    # Non-scheduler worker fallback: calculate from cron expression
    # This ensures next-run calculation works on non-scheduler Gunicorn workers
    try:
        # Query list from database to get cron expression
        list_obj = db.session.get(List, list_id)
        if not list_obj or not list_obj.schedule_cron or not list_obj.is_active:
            return None

        # Calculate next run time using CronSim
        scheduler_tz = _get_scheduler_timezone()
        cron = CronSim(list_obj.schedule_cron, datetime.now(scheduler_tz))
        cron.advance()
        # CronSim strips ZoneInfo tzinfo from non-UTC seeds; reattach it.
        if cron.dt.tzinfo is None:
            return cron.dt.replace(tzinfo=scheduler_tz)
        return cron.dt
    except (ValueError, StopIteration, CronSimError) as e:
        logger.debug(f"Failed to calculate next run time for list {list_id}: {e}")
        return None


def validate_cron_expression(cron_expr):
    """
    Validate a cron expression and provide details.

    Args:
        cron_expr: Cron expression string (e.g., "0 0 * * *")

    Returns:
        dict with:
            - valid (bool): Whether expression is valid
            - error (str or None): Error message if invalid
            - description (str): Human-readable description
            - next_runs (list): Next 3 run times as ISO strings
            next_runs values use isoformat() with UTC offset when the scheduler timezone is non-UTC.
    """
    result = {"valid": False, "error": None, "description": "", "next_runs": []}

    try:
        # Validate with cronsim
        scheduler_tz = _get_scheduler_timezone()
        cron = CronSim(cron_expr, datetime.now(scheduler_tz))

        # Get human-readable description
        try:
            description = get_description(cron_expr)
            result["description"] = description
        except (ValueError, KeyError):
            result["description"] = cron_expr

        # Get next 3 run times using advance()
        next_runs = []
        for _ in range(3):
            cron.advance()
            dt = cron.dt
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=scheduler_tz)
            next_runs.append(dt.isoformat())
            # Move forward 1 second to get the next occurrence
            cron.tick()

        # cronsim and APScheduler do not accept the same grammar. An expression cronsim
        # parses but CronTrigger cannot build (e.g. "0 2 L * *") must be rejected here so
        # it can never be stored on a list and reach the reconcile as an unbuildable row.
        try:
            CronTrigger.from_crontab(_posix_cron_to_apscheduler(cron_expr))
        except (ValueError, KeyError):
            result["error"] = "Cron expression is valid syntax but builds no scheduler trigger"
            result["description"] = "Invalid cron expression"
            return result

        result["next_runs"] = next_runs
        result["valid"] = True

    except (ValueError, KeyError, CronSimError, StopIteration) as e:
        # CronSim.advance() raises StopIteration for an expression that parses but matches
        # nothing within 50 years. get_next_run_time() has always caught it; catch it here
        # too so the validation endpoint returns "invalid cron" instead of a 500.
        result["error"] = str(e) or "Cron expression has no run times within the next 50 years"
        result["description"] = "Invalid cron expression"

    return result
