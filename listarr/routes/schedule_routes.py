"""Schedule routes - API endpoints for schedule management."""

from apscheduler.jobstores.base import JobLookupError
from flask import current_app, jsonify, render_template
from flask_login import login_required
from sqlalchemy.exc import IntegrityError, OperationalError

from listarr import db
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.routes import bp
from listarr.services.job_executor import is_list_running
from listarr.services.scheduler import get_next_run_time, pause_scheduler, resume_scheduler

# Badge colors matching listarr/templates/macros/status.html
_STATUS_COLORS = {
    "running": "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    "paused": "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    "scheduled": "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    "manual only": "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
}
_DEFAULT_COLOR = "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
_SPINNER_SVG = (
    '<svg class="animate-spin -ml-1 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" '
    'fill="none" viewBox="0 0 24 24">'
    '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4">'
    "</circle>"
    '<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4'
    'zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>'
    "</svg>"
)


def _render_status_badge(status):
    """Render a status badge HTML string matching the Jinja2 macro colors."""
    color = _STATUS_COLORS.get(status.lower(), _DEFAULT_COLOR)
    base = (
        f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs '
        f'font-medium {color} status-badge" data-status="{status}">'
    )
    if status.lower() == "running":
        return f"{base}{_SPINNER_SVG}{status}</span>"
    return f"{base}{status}</span>"


@bp.route("/schedule")
@login_required
def schedule_page():
    """
    Render the Schedule management page.

    Displays all lists with their schedule status, next run time, and last run summary.
    """
    # Get global pause state
    config = ServiceConfig.query.first()
    scheduler_paused = config.scheduler_paused if config else False

    # Query all lists
    lists = List.query.order_by(List.name).all()

    # Build schedule data for each list
    schedule_data = []
    for list_obj in lists:
        # Determine status
        status = _get_list_status(list_obj, scheduler_paused)

        # Get next run time
        next_run = None
        if list_obj.schedule_cron and not scheduler_paused:
            next_run_dt = get_next_run_time(list_obj.id)
            if next_run_dt:
                next_run = next_run_dt.isoformat()

        # Get last run info
        last_run = None
        items_count = None
        if list_obj.last_run_at:
            last_run = list_obj.last_run_at.isoformat()
            # Get most recent job for items count
            recent_job = Job.query.filter_by(list_id=list_obj.id).order_by(Job.started_at.desc()).first()
            if recent_job and recent_job.status == "completed":
                items_count = {
                    "added": recent_job.items_added or 0,
                    "skipped": recent_job.items_skipped or 0,
                }

        schedule_data.append(
            {
                "id": list_obj.id,
                "name": list_obj.name,
                "target_service": list_obj.target_service,
                "status": status,
                "next_run": next_run,
                "last_run": last_run,
                "items_count": items_count,
                "has_schedule": bool(list_obj.schedule_cron),
                "schedule_cron": list_obj.schedule_cron or "",
            }
        )

    return render_template(
        "schedule.html",
        lists=schedule_data,
        scheduler_paused=scheduler_paused,
    )


def _get_list_status(list_obj, scheduler_paused):
    """
    Determine the current status of a list.

    Args:
        list_obj: List model instance
        scheduler_paused: Whether scheduler is globally paused

    Returns:
        str: Status string (Running, Paused, Scheduled, Manual only)
    """
    # Check if job is currently running
    if is_list_running(list_obj.id):
        return "Running"

    # Check if globally paused and list has schedule
    if scheduler_paused and list_obj.schedule_cron:
        return "Paused"

    # Check if list has a schedule
    if list_obj.schedule_cron:
        return "Scheduled"

    # No schedule configured
    return "Manual only"


@bp.route("/api/schedule/pause", methods=["POST"])
@login_required
def pause_schedule():
    """
    Pause all scheduled jobs globally.

    Returns:
        JSON: {success: true} on success
    """
    try:
        pause_scheduler()
        return jsonify({"success": True})
    except (OperationalError, RuntimeError) as e:
        current_app.logger.error(f"Error pausing scheduler: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to pause scheduler. Please try again."}), 500


@bp.route("/api/schedule/resume", methods=["POST"])
@login_required
def resume_schedule():
    """
    Resume all scheduled jobs globally.

    Returns:
        JSON: {success: true} on success
    """
    try:
        resume_scheduler()
        return jsonify({"success": True})
    except (OperationalError, RuntimeError) as e:
        current_app.logger.error(f"Error resuming scheduler: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to resume scheduler. Please try again."}), 500


@bp.route("/api/schedule/status")
@login_required
def get_schedule_status():
    """
    Get current scheduler status and list schedule information.

    Returns:
        JSON with:
            - paused (bool): Global pause state
            - lists (array): Schedule info for all lists
    """
    # Get global pause state
    config = ServiceConfig.query.first()
    scheduler_paused = config.scheduler_paused if config else False

    # Query all lists
    lists = List.query.order_by(List.name).all()

    # Build schedule data
    schedule_data = []
    for list_obj in lists:
        status = _get_list_status(list_obj, scheduler_paused)

        next_run = None
        if list_obj.schedule_cron and not scheduler_paused:
            next_run_dt = get_next_run_time(list_obj.id)
            if next_run_dt:
                next_run = next_run_dt.isoformat()

        last_run = None
        items_count = None
        if list_obj.last_run_at:
            last_run = list_obj.last_run_at.isoformat()
            recent_job = Job.query.filter_by(list_id=list_obj.id).order_by(Job.started_at.desc()).first()
            if recent_job and recent_job.status == "completed":
                items_count = {
                    "added": recent_job.items_added or 0,
                    "skipped": recent_job.items_skipped or 0,
                }

        schedule_data.append(
            {
                "id": list_obj.id,
                "name": list_obj.name,
                "target_service": list_obj.target_service,
                "status": status,
                "status_html": _render_status_badge(status),
                "next_run": next_run,
                "last_run": last_run,
                "items_count": items_count,
                "has_schedule": bool(list_obj.schedule_cron),
                "schedule_cron": list_obj.schedule_cron or "",
            }
        )

    return jsonify(
        {
            "paused": scheduler_paused,
            "lists": schedule_data,
        }
    )


@bp.route("/api/schedule/<int:list_id>/update", methods=["POST"])
@login_required
def update_schedule(list_id):
    """
    Update the schedule for a specific list.

    Accepts JSON: {"schedule_cron": "0 0 * * *"} or {"schedule_cron": ""} to remove schedule.

    Returns:
        JSON: {success: true, schedule_cron: "...", status: "...", next_run: "..."}
    """
    from flask import current_app, request

    from listarr.services.scheduler import schedule_list, unschedule_list, validate_cron_expression

    list_obj = List.query.get(list_id)
    if not list_obj:
        return jsonify({"success": False, "error": "List not found"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    new_cron = data.get("schedule_cron", "").strip()

    try:
        # Validate cron expression if provided
        if new_cron:
            validation = validate_cron_expression(new_cron)
            if not validation["valid"]:
                return jsonify({"success": False, "error": f"Invalid cron: {validation['error']}"}), 400

        # Update database
        list_obj.schedule_cron = new_cron if new_cron else None
        db.session.commit()

        # Update scheduler
        try:
            if new_cron and list_obj.is_active:
                schedule_list(list_obj.id, new_cron)
            else:
                unschedule_list(list_obj.id)
        except (ValueError, JobLookupError) as e:
            current_app.logger.warning(f"Scheduler update failed for list {list_id}: {e}")

        # Get updated status
        config = ServiceConfig.query.first()
        scheduler_paused = config.scheduler_paused if config else False
        status = _get_list_status(list_obj, scheduler_paused)

        next_run = None
        if new_cron and not scheduler_paused:
            from listarr.services.scheduler import get_next_run_time

            next_run_dt = get_next_run_time(list_obj.id)
            if next_run_dt:
                next_run = next_run_dt.isoformat()

        return jsonify(
            {
                "success": True,
                "schedule_cron": new_cron or "",
                "status": status,
                "next_run": next_run,
            }
        )

    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating schedule for list {list_id}: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to update schedule"}), 500
