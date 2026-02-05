"""
Job Executor Service
Orchestrates background job execution with database persistence, retry logic, and timeout handling.
"""

import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from listarr import db
from listarr.models.jobs_model import Job, JobItem
from listarr.models.lists_model import List
from listarr.services.import_service import import_list

logger = logging.getLogger(__name__)

# Configuration
MAX_WORKERS = 3
JOB_TIMEOUT_SECONDS = 600  # 10 minutes
RETRY_ATTEMPTS = 3
RETRY_DELAYS = [5, 10, 20]  # seconds

# Global executor (lazy init)
_executor = None
_stop_events = {}
_stop_events_lock = threading.Lock()


def get_executor():
    """Get or create the ThreadPoolExecutor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="job_")
    return _executor


def is_list_running(list_id):
    """Check if a job for this list is currently running (database check)."""
    return Job.query.filter_by(list_id=list_id, status="running").first() is not None


def get_job_status(list_id):
    """
    Get the current job status for a list.

    Returns:
        dict with status info or None if no recent job
    """
    # Get most recent job for this list
    job = Job.query.filter_by(list_id=list_id).order_by(Job.started_at.desc()).first()
    if not job:
        return None
    return job.to_dict()


def submit_job(list_id, list_name, app, triggered_by="manual"):
    """
    Submit a job for execution with timeout monitoring.

    Args:
        list_id: ID of the list to import
        list_name: Name of the list (denormalized for persistence)
        app: Flask app instance (use app._get_current_object())
        triggered_by: 'manual' or 'scheduled'

    Returns:
        int: Job ID

    Raises:
        ValueError: If job already running for this list
    """
    # Check if already running (database check for persistence)
    if is_list_running(list_id):
        raise ValueError(f"Job already running for list {list_id}")

    # Create job record first (within app context)
    with app.app_context():
        job = Job(
            list_id=list_id,
            list_name=list_name,
            status="running",
            started_at=datetime.now(timezone.utc),
            triggered_by=triggered_by,
            retry_count=0,
            items_found=0,
            items_added=0,
            items_skipped=0,
            items_failed=0,
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    # Create stop event for timeout
    stop_event = threading.Event()
    with _stop_events_lock:
        _stop_events[job_id] = stop_event

    # Submit job to executor
    future = get_executor().submit(_execute_job, job_id, list_id, stop_event, app)

    # Set up timeout timer
    timer = threading.Timer(JOB_TIMEOUT_SECONDS, lambda: _trigger_timeout(job_id))
    timer.daemon = True  # Don't block app shutdown
    timer.start()

    def cleanup(f):
        timer.cancel()
        with _stop_events_lock:
            _stop_events.pop(job_id, None)

    future.add_done_callback(cleanup)

    return job_id


def _trigger_timeout(job_id):
    """Signal timeout for a job."""
    with _stop_events_lock:
        stop_event = _stop_events.get(job_id)
        if stop_event:
            logger.warning(f"Job {job_id} timeout triggered")
            stop_event.set()


def _execute_job(job_id, list_id, stop_event, app):
    """
    Execute the job in a background thread.

    Uses app context and handles all job lifecycle.
    """
    with app.app_context():
        start_time = datetime.now(timezone.utc)
        try:
            # Check for timeout before starting
            if stop_event.is_set():
                _mark_job_failed(
                    job_id,
                    "Job timed out before execution",
                    "Timeout occurred before job could start",
                )
                return

            # Run the import
            result = import_list(list_id)

            # Check for timeout after import
            if stop_event.is_set():
                _mark_job_timeout(job_id, result, start_time)
                return

            # Update job with results
            _mark_job_completed(job_id, result, start_time)

            # Update list's last_run_at
            list_obj = List.query.get(list_id)
            if list_obj:
                list_obj.last_run_at = datetime.now(timezone.utc)
                db.session.commit()

        except Exception as e:
            logger.error(f"Job {job_id} failed with exception: {e}", exc_info=True)
            error_details = traceback.format_exc()
            _mark_job_failed(job_id, str(e), error_details, start_time)


def _mark_job_completed(job_id, result, start_time):
    """Mark job as completed with results."""
    job = Job.query.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found when marking completed")
        return

    end_time = datetime.now(timezone.utc)
    job.status = "completed"
    job.completed_at = end_time
    job.duration = int((end_time - start_time).total_seconds())

    if result:
        job.items_found = result.total
        job.items_added = len(result.added)
        job.items_skipped = len(result.skipped)
        job.items_failed = len(result.failed)

        # Store job items
        _store_job_items(job_id, result)

    db.session.commit()
    logger.info(
        f"Job {job_id} completed: {job.items_added} added, {job.items_skipped} skipped, {job.items_failed} failed"
    )


def _mark_job_failed(job_id, error_message, error_details, start_time=None):
    """Mark job as failed with error info."""
    job = Job.query.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found when marking failed")
        return

    end_time = datetime.now(timezone.utc)
    job.status = "failed"
    job.completed_at = end_time
    job.error_message = error_message
    job.error_details = error_details

    if start_time:
        job.duration = int((end_time - start_time).total_seconds())

    db.session.commit()
    logger.error(f"Job {job_id} failed: {error_message}")


def _mark_job_timeout(job_id, result, start_time):
    """Mark job as failed due to timeout, preserving partial results."""
    job = Job.query.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found when marking timeout")
        return

    end_time = datetime.now(timezone.utc)
    job.status = "failed"
    job.completed_at = end_time
    job.duration = int((end_time - start_time).total_seconds())
    job.error_message = "Job timed out"
    job.error_details = f"Job exceeded {JOB_TIMEOUT_SECONDS} second timeout limit. Partial results may have been saved."

    if result:
        job.items_found = result.total
        job.items_added = len(result.added)
        job.items_skipped = len(result.skipped)
        job.items_failed = len(result.failed)

        # Store partial results
        _store_job_items(job_id, result)

    db.session.commit()
    logger.warning(f"Job {job_id} timed out with partial results")


def _store_job_items(job_id, result):
    """Store individual item results in JobItem table."""
    # Store added items
    for item in result.added:
        job_item = JobItem(
            job_id=job_id,
            tmdb_id=item.get("tmdb_id"),
            title=item.get("title", "Unknown"),
            status="added",
            message=None,
        )
        db.session.add(job_item)

    # Store skipped items
    for item in result.skipped:
        job_item = JobItem(
            job_id=job_id,
            tmdb_id=item.get("tmdb_id"),
            title=item.get("title", "Unknown"),
            status="skipped",
            message=item.get("reason"),
        )
        db.session.add(job_item)

    # Store failed items
    for item in result.failed:
        job_item = JobItem(
            job_id=job_id,
            tmdb_id=item.get("tmdb_id"),
            title=item.get("title", "Unknown"),
            status="failed",
            message=item.get("reason"),
        )
        db.session.add(job_item)
