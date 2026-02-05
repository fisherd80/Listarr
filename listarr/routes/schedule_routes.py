"""Schedule routes - API endpoints for schedule management."""

from flask import jsonify, render_template

from listarr import csrf
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.routes import bp
from listarr.services.job_executor import is_list_running
from listarr.services.scheduler import get_next_run_time, pause_scheduler, resume_scheduler


@bp.route("/schedule")
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
@csrf.exempt
def pause_schedule():
    """
    Pause all scheduled jobs globally.

    Returns:
        JSON: {success: true} on success
    """
    try:
        pause_scheduler()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/schedule/resume", methods=["POST"])
@csrf.exempt
def resume_schedule():
    """
    Resume all scheduled jobs globally.

    Returns:
        JSON: {success: true} on success
    """
    try:
        resume_scheduler()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/schedule/status")
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
                "next_run": next_run,
                "last_run": last_run,
                "items_count": items_count,
                "has_schedule": bool(list_obj.schedule_cron),
            }
        )

    return jsonify(
        {
            "paused": scheduler_paused,
            "lists": schedule_data,
        }
    )
