"""
Scheduler Service
Manages APScheduler for automated list imports with cron schedules.
"""

import atexit
import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from cron_descriptor import get_description
from cronsim import CronSim
from cronsim.cronsim import CronSimError
from cryptography.fernet import InvalidToken
from requests.exceptions import RequestException
from sqlalchemy.exc import OperationalError

from listarr import db
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.services.arr_service import validate_api_key
from listarr.services.crypto_utils import decrypt_data
from listarr.services.job_executor import is_list_running, submit_job

logger = logging.getLogger(__name__)

# Module-level scheduler instance (singleton pattern like job_executor)
_scheduler = None
_app = None


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

    # Get timezone from environment or default to UTC
    tz = os.environ.get("TZ", "UTC")

    # Create scheduler with configuration
    _scheduler = BackgroundScheduler(
        timezone=tz,
        job_defaults={
            "coalesce": True,  # Combine multiple missed runs into one
            "max_instances": 1,  # Only one instance of each job at a time
            "misfire_grace_time": 60,  # Jobs can run up to 60s late
        },
    )

    # Register shutdown handler
    atexit.register(lambda: shutdown_scheduler())

    # Load existing schedules from database
    _load_schedules_from_db()

    # Start the scheduler
    _scheduler.start()
    logger.info(f"Scheduler initialized (timezone: {tz})")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    global _scheduler
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


def schedule_list(list_id, cron_expression):
    """
    Schedule a list for automatic import execution.

    Args:
        list_id: ID of the list to schedule
        cron_expression: Cron expression (e.g., "0 0 * * *")

    Raises:
        ValueError: If cron expression is invalid
        RuntimeError: If scheduler not initialized
    """
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized")

    # Validate cron expression
    validation = validate_cron_expression(cron_expression)
    if not validation["valid"]:
        raise ValueError(f"Invalid cron expression: {validation['error']}")

    # Create job ID
    job_id = f"list_{list_id}"

    # Remove existing job if present (for updates)
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    # Add job with cron trigger
    try:
        trigger = CronTrigger.from_crontab(cron_expression)
        _scheduler.add_job(
            _run_scheduled_import,
            trigger=trigger,
            id=job_id,
            args=[list_id],
            name=f"List {list_id} import",
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
    if _scheduler is None:
        logger.warning("Scheduler not initialized, cannot unschedule")
        return

    job_id = f"list_{list_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
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
    if _scheduler is None:
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
            _scheduler.pause()
            logger.info("Scheduler paused")
        except (OperationalError, RuntimeError) as e:
            logger.error(f"Failed to pause scheduler: {e}")
            raise


def resume_scheduler():
    """Resume all scheduled job execution."""
    if _scheduler is None:
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
            _scheduler.resume()
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
    if _scheduler is not None:
        # Scheduler worker: get next run time from APScheduler (preferred path)
        job_id = f"list_{list_id}"
        job = _scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None

    # Non-scheduler worker fallback: calculate from cron expression
    # This ensures dashboard works on all Gunicorn workers
    try:
        # Query list from database to get cron expression
        list_obj = List.query.get(list_id)
        if not list_obj or not list_obj.schedule_cron or not list_obj.is_active:
            return None

        # Calculate next run time using CronSim
        cron = CronSim(list_obj.schedule_cron, datetime.now(timezone.utc))
        cron.advance()
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
    """
    result = {"valid": False, "error": None, "description": "", "next_runs": []}

    try:
        # Validate with cronsim
        cron = CronSim(cron_expr, datetime.now(timezone.utc))

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
            next_runs.append(cron.dt.isoformat())
            # Move forward 1 second to get the next occurrence
            cron.tick()

        result["next_runs"] = next_runs
        result["valid"] = True

    except (ValueError, KeyError) as e:
        result["error"] = str(e)
        result["description"] = "Invalid cron expression"

    return result
