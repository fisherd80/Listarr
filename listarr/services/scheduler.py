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
    get_app_timezone_fallback_name,
    get_app_timezone_name,
    resolve_db_timezone_string,
    tz_key,
)

logger = logging.getLogger(__name__)

# Module-level scheduler instance (singleton pattern like job_executor)
_scheduler = None
_app = None
_reschedule_lock = threading.Lock()
_tz_poll_last_bad_value = None

# CR-01: a rebuild that leaves stale triggers behind must not look "converged" to the
# poll, but the two ways it can fail need opposite handling and a single retry counter
# cannot tell them apart.
#
#   transient     - the scheduler was busy, the app was not ready, or the DB was locked.
#                   Nothing about the failure is specific to any list, and retrying on
#                   the next poll is both free and the only thing that can fix it. These
#                   retry indefinitely: a bounded budget spent on transient contention is
#                   precisely how lists get stranded on the old timezone, because a busy
#                   import can hold SQLite's write lock for longer than the budget lasts.
#
#   deterministic - one list's cron expression builds no APScheduler trigger. Re-running
#                   the identical (list id, cron) pair can never succeed, so the list is
#                   quarantined: logged loudly the first time, excluded from the "retry
#                   needed" signal, and automatically re-attempted the moment its cron
#                   changes or the operator saves the timezone again.
#
# _reschedule_incomplete therefore means "stale triggers remain for a reason a retry can
# still fix". A quarantined list never sets it, so the poll neither spins forever on an
# unbuildable cron nor gives up on a recoverable failure. There is no budget to exhaust.
_reschedule_incomplete = False

# list id -> the cron expression that could not be built. Mutated only under
# _reschedule_lock; rebound wholesale by reset_reschedule_state().
_reschedule_quarantine = {}

# The quarantine is a standing fault, so restate it periodically rather than logging it
# once and going quiet. 60 ticks of the 60s poll is roughly hourly.
_QUARANTINE_REMINDER_TICKS = 60
_quarantine_reminder_countdown = 0


def _clear_quarantine(list_id):
    """Drop a standing verdict the moment the list is successfully scheduled or removed.

    WR-01: the quarantine used to be re-evaluated only inside reschedule_all_lists(),
    which runs only when the zone diverges or a transient failure is outstanding.
    Correcting the cron does neither - the edit routes call schedule_list() directly - so
    the hourly WARN went on claiming the list "is still firing on the previous zone" long
    after the very remedy it recommends had been applied. The same leak kept entries alive
    for lists that were later deleted or deactivated.

    Deliberately does not take _reschedule_lock: that lock is a non-reentrant Lock and
    reschedule_all_lists() holds it while calling schedule_list(), so acquiring here would
    self-deadlock. dict.pop on the live global is atomic under the GIL, which is all the
    mutual exclusion a single key removal needs.
    """
    _reschedule_quarantine.pop(list_id, None)


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
        try:
            return zoneinfo.ZoneInfo(stored)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError):
            logger.warning("Configured timezone %r could not be loaded by scheduler; falling back", stored)

    if scheduler is not None:
        return scheduler.timezone

    try:
        return zoneinfo.ZoneInfo(os.environ.get("TZ", "UTC"))
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError):
        return timezone.utc


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

    _scheduler.add_job(
        _tz_poll_tick,
        trigger="interval",
        seconds=60,
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


def reschedule_is_incomplete() -> bool:
    """True when a transient failure left stale triggers and a retry is still pending.

    This is deliberately *not* set by a quarantined list (see get_unschedulable_lists);
    those cannot be fixed by retrying, so folding them in here would make the poll spin.
    """
    return _reschedule_incomplete


def get_unschedulable_lists() -> dict:
    """Return {list id: cron} for lists whose cron builds no trigger in the current zone.

    These lists keep their previous trigger, so they continue firing on the *old*
    timezone until the expression is corrected. Exposed so the condition has a consumer
    beyond the log (CR-01); reset_reschedule_state() re-arms them for another attempt.
    """
    return dict(_reschedule_quarantine)


def reset_reschedule_state() -> None:
    """Clear the quarantine so an explicit user-initiated save re-attempts every list.

    WR-08: a deliberate recovery action must not get fewer attempts than the automatic
    poll. Clearing also re-arms the per-list error log, so the operator sees a fresh
    diagnosis for a still-broken cron instead of silence.
    """
    global _reschedule_quarantine, _quarantine_reminder_countdown
    _reschedule_quarantine = {}
    _quarantine_reminder_countdown = 0


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
            # Query all lists with schedules that are active
            lists = List.query.filter(List.schedule_cron.isnot(None), List.is_active == True).all()  # noqa: E712

            for list_obj in lists:
                try:
                    schedule_list(list_obj.id, list_obj.schedule_cron)
                    logger.info(f"Loaded schedule for list {list_obj.id}: {list_obj.schedule_cron}")
                except (ValueError, KeyError) as e:
                    logger.error(f"Failed to load schedule for list {list_obj.id}: {e}")

            logger.info(f"Loaded {len(lists)} scheduled lists")
        except OperationalError as e:
            logger.error(f"Failed to load schedules from database: {e}")


def _drop_orphaned_list_jobs(scheduler):
    """Remove list jobs no live list owns, which are therefore still on the previous zone.

    WR-02: assigning scheduler.timezone changes nothing about jobs that already exist —
    APScheduler only consults it while *constructing* a trigger. So any list_* job outside
    the "active and scheduled" query keeps its old-zone CronTrigger forever, and the
    convergence check (which only compares scheduler.timezone) reports success anyway.

    This is reachable today: deactivating a list from a non-scheduler gunicorn worker
    makes unschedule_list() a no-op in that process, so the job survives here. Leaving it
    would fire imports for an inactive list, in the wrong timezone, indefinitely.

    WR-03: the caller used to pass the id set from the query that opened the rebuild, and
    every job outside that snapshot was deleted. On the scheduler worker the request
    threads share this process, so a user saving a schedule mid-rebuild had their
    brand-new, perfectly valid job classified as an orphan and removed — and because the
    rebuild then marked itself converged, the poll never put it back. The list stayed
    unscheduled until the next restart.

    Reading the ids here, and specifically *after* snapshotting the job set, closes that
    race without a lock. Every mutator in lists_routes commits the row before it calls
    schedule_list(), so a job present in `candidates` implies its row was committed
    strictly earlier, and the query below runs strictly later — it cannot miss it. (The
    pysqlite driver issues bare SELECTs outside a transaction, so this second read is not
    pinned to a snapshot taken by the first one.) A job added *after* `candidates` is
    taken is simply not considered, which is the safe direction to err.
    """
    candidates = [job.id for job in scheduler.get_jobs() if job.id.startswith("list_")]
    if not candidates:
        return

    live = {
        f"list_{row.id}"
        for row in List.query.filter(
            List.schedule_cron.isnot(None),
            List.is_active == True,  # noqa: E712
        ).all()
    }

    for job_id in candidates:
        if job_id in live:
            continue
        logger.warning("Removing orphaned scheduler job %s during timezone rebuild", job_id)
        try:
            scheduler.remove_job(job_id)
        except JobLookupError:
            # Already gone (another worker or a concurrent unschedule won the race).
            pass


def reschedule_all_lists(tz_str, blocking=True):
    """Rebuild every active scheduled list in the requested timezone.

    Triggers are rebuilt, not mutated, and each list failure is counted without
    aborting the full walk. _reschedule_lock serializes the scheduler timezone
    assignment and the complete rebuild loop. This remains forward-only by
    construction: add_job without next_run_time computes the next fire from now,
    so misfire_grace_time is never consulted for rebuilt jobs.
    """
    global _reschedule_incomplete, _reschedule_quarantine

    scheduler = _scheduler
    if scheduler is None:
        logger.debug("Scheduler not running in this worker; skipping in-process timezone reschedule")
        return (0, 0)
    if _app is None:
        logger.error("Cannot reschedule lists: app not initialized")
        return (0, 0)

    acquired = _reschedule_lock.acquire(blocking=blocking)
    if not acquired:
        # The lock holder owns the convergence state; do not overwrite it here.
        logger.debug("Reschedule already in progress; skipping this attempt")
        return (0, 0)

    n_ok = 0
    n_fail = 0
    try:
        try:
            new_tz = astimezone(tz_str)
        except (ValueError, TypeError, zoneinfo.ZoneInfoNotFoundError) as e:
            logger.error(f"Could not apply scheduler timezone {tz_str!r}: {e}")
            return (0, 0)

        with _app.app_context():
            try:
                lists = List.query.filter(List.schedule_cron.isnot(None), List.is_active == True).all()  # noqa: E712
            except OperationalError as e:
                # CR-01: a locked or unavailable DB is transient. Leave scheduler.timezone
                # untouched so the poll still sees a divergence, and flag the retry as
                # still-needed — this path must never consume a finite allowance, because
                # the contention that causes it routinely outlasts one.
                logger.error(f"Failed to load schedules for timezone reschedule: {e}")
                _reschedule_incomplete = True
                return (0, 0)

            # The timezone assignment is the commit of the rebuild, not its prelude.
            #
            # IN-08: BaseScheduler.timezone is normally set by configure(), which refuses
            # to run while the scheduler is started — hence the direct assignment. It is
            # not documented as a mutable attribute, so this leans on an internal detail:
            # validated against APScheduler 3.11.3 (pinned with == in requirements.txt),
            # where add_job reads self.timezone only at trigger-construction time, which
            # is exactly what the rebuild loop below relies on.
            #
            # If a future bump turns timezone into a read-only property, the real signal
            # is tests/integration/test_scheduler_bump_smoke.py, which drives a real
            # BackgroundScheduler through this path for that purpose.
            #
            # WR-02: flag *before* the commit, clear only after the walk completes. The
            # previous shape enumerated the failures it expected to see - (ValueError,
            # KeyError) per list - and implicitly classified everything else as success,
            # because _reschedule_incomplete was still False when the unexpected exception
            # unwound past it. That left scheduler.timezone already advanced with an
            # un-rebuilt remainder behind it, which _tz_poll_tick() reads as converged
            # forever: exactly the stale-trigger state this machinery exists to prevent.
            #
            # Setting it here makes the classification total by construction rather than by
            # enumeration. Anything that escapes - a lazy attribute load on list_obj, a
            # non-JobLookupError from _drop_orphaned_list_jobs(), an exception type
            # schedule_list() grows later - leaves the retry signal armed, and the poll
            # tries again in ~60s. Unknown means recoverable, which is the safe default:
            # the cost of a needless retry is one rebuild, the cost of a missed one is
            # imports firing in the wrong timezone indefinitely.
            _reschedule_incomplete = True
            scheduler.timezone = new_tz
            quarantine = {}
            for list_obj in lists:
                cron = list_obj.schedule_cron
                try:
                    schedule_list(list_obj.id, cron)
                    n_ok += 1
                except (ValueError, KeyError) as e:
                    n_fail += 1
                    # CR-01: deterministic. This exact (list, cron) pair will fail
                    # identically forever, so quarantine it rather than retry it, and
                    # say so once per distinct pair instead of once per poll tick.
                    quarantine[list_obj.id] = cron
                    if _reschedule_quarantine.get(list_obj.id) != cron:
                        logger.error(
                            "List %s cannot be rescheduled into %s: %s. Its cron %r builds no "
                            "APScheduler trigger, so the list keeps its previous trigger and "
                            "will keep firing on the old timezone until the expression is "
                            "corrected. Every other list was rebuilt.",
                            list_obj.id,
                            tz_str,
                            e,
                            cron,
                        )

            _drop_orphaned_list_jobs(scheduler)

        # The loop ran to completion, so nothing recoverable is outstanding. Entries for
        # lists that have since been deleted or deactivated drop out with the rebind.
        # Reaching this statement is the only thing that clears the WR-02 flag set above.
        _reschedule_quarantine = quarantine
        _reschedule_incomplete = False
        logger.info(f"Rescheduled {n_ok} lists into {tz_str} ({n_fail} failed)")
        return (n_ok, n_fail)
    finally:
        _reschedule_lock.release()


def _warn_about_quarantined_lists():
    """Restate any standing quarantine so a bad cron cannot fail silently forever.

    CR-01: the previous design gave up permanently with a bare return and no log. The
    quarantine is a real, operator-actionable fault, so it is reported on the first poll
    tick that observes it and roughly hourly thereafter until it is resolved.
    """
    global _quarantine_reminder_countdown

    if not _reschedule_quarantine:
        _quarantine_reminder_countdown = 0
        return

    if _quarantine_reminder_countdown > 0:
        _quarantine_reminder_countdown -= 1
        return

    logger.warning(
        "%d scheduled list(s) cannot be rebuilt in the application timezone and are still "
        "firing on the previous zone: %s. Correct the cron expression(s), or re-save the "
        "timezone to force another attempt.",
        len(_reschedule_quarantine),
        ", ".join(f"list {list_id} ({cron!r})" for list_id, cron in sorted(_reschedule_quarantine.items())),
    )
    _quarantine_reminder_countdown = _QUARANTINE_REMINDER_TICKS


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

            _warn_about_quarantined_lists()

            converged = tz_key(desired) == tz_key(scheduler.timezone)
            if converged and not _reschedule_incomplete:
                # Either everything is applied, or the only thing left is a quarantined
                # cron that another identical attempt cannot fix. Both mean "do nothing".
                return

            # Anything else is recoverable by construction: a divergent zone, or a
            # transient DB/lock failure. Retry unconditionally — a no-op attempt (lock
            # held by a concurrent save) costs nothing and forfeits nothing.
            reschedule_all_lists(desired, blocking=False)
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
        # WR-01: this list now has a trigger built in the *current* scheduler timezone,
        # so any standing "cannot be rebuilt" verdict against it is obsolete.
        _clear_quarantine(list_id)
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

    # WR-01: unconditional, and outside the get_job() guard. A list that is being
    # deactivated or deleted has no schedule to rebuild, so a standing verdict about it is
    # meaningless whether or not a job happened to be registered in this process.
    _clear_quarantine(list_id)


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
            list_obj = List.query.get(list_id)
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
        list_obj = List.query.get(list_id)
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

        result["next_runs"] = next_runs
        result["valid"] = True

    except (ValueError, KeyError, CronSimError, StopIteration) as e:
        # WR-02: CronSim.advance() raises StopIteration for an expression that parses but
        # matches nothing within 50 years. get_next_run_time() has always caught it; this
        # call site did not, so the same expression was a handled "invalid cron" there and
        # an unhandled 500 out of the validation endpoint here - and, via schedule_list(),
        # an exception outside the (ValueError, KeyError) classification in
        # reschedule_all_lists(). Treat it as what it is: an unusable expression.
        result["error"] = str(e) or "Cron expression has no run times within the next 50 years"
        result["description"] = "Invalid cron expression"

    return result
