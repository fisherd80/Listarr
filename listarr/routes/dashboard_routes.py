from flask import current_app, jsonify, render_template, request
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import joinedload

from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.routes import bp
from listarr.services.dashboard_cache import (
    get_dashboard_cache,
    refresh_dashboard_cache,
)
from listarr.services.scheduler import get_next_run_time
from listarr.utils.time_utils import format_relative_time


@bp.route("/")
def dashboard_page():
    return render_template("dashboard.html")


@bp.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """
    Returns cached dashboard statistics for display.

    Query Parameters:
        refresh (bool): If true, forces a cache refresh before returning data

    Returns:
        JSON response with structure:
        {
            "radarr": {
                "configured": bool,
                "status": "online" | "offline" | "not_configured",
                "version": str | null,
                "total_movies": int,
                "missing_movies": int,
                "added_by_listarr": int
            },
            "sonarr": {
                "configured": bool,
                "status": "online" | "offline" | "not_configured",
                "version": str | null,
                "total_series": int,
                "missing_episodes": int,
                "added_by_listarr": int
            }
        }
    """
    # Check if refresh is requested
    refresh = request.args.get("refresh", "false").lower() == "true"

    if refresh:
        # Force refresh of cache
        current_app.logger.info("Dashboard cache refresh requested")
        cache_data = refresh_dashboard_cache()
    else:
        # Return cached data (calculated at startup)
        cache_data = get_dashboard_cache()

    return jsonify(cache_data)


@bp.route("/api/dashboard/recent-jobs", methods=["GET"])
def recent_jobs():
    """
    Returns the last 5 executed jobs for dashboard display.

    Returns:
        JSON response with structure:
        {
            "jobs": [
                {
                    "id": int,
                    "job_name": str,
                    "service": str,
                    "status": str,
                    "started_at": str,
                    "completed_at": str | null,
                    "executed_at": str,
                    "summary": str,
                    "error_message": str | null
                }
            ]
        }
    """
    try:
        # Query last 5 finished jobs with eager-loaded list relationship
        # This eliminates N+1 queries by fetching list data in single query
        jobs = (
            Job.query.options(joinedload(Job.list))
            .filter(Job.completed_at.isnot(None))
            .order_by(Job.completed_at.desc(), Job.started_at.desc())
            .limit(5)
            .all()
        )

        jobs_data = []
        for job in jobs:
            # Get list information from eager-loaded relationship
            if job.list:
                job_name = job.list.name
                service = job.list.target_service
            elif job.list_name:
                # List was deleted but we have denormalized name
                job_name = job.list_name
                service = "Unknown"
            else:
                # No list information available
                job_name = f"Job #{job.id}"
                service = "Unknown"

            # Format summary based on status
            if job.status == "completed":
                # Build summary parts conditionally
                parts = []
                if job.items_added > 0:
                    parts.append(f"{job.items_added} added")
                if job.items_skipped > 0:
                    parts.append(f"{job.items_skipped} skipped")

                if len(parts) == 0:
                    # No items processed
                    summary = "No items processed"
                else:
                    # Join parts with comma and space
                    summary = ", ".join(parts)
            elif job.status == "failed":
                error_msg = job.error_message or "Unknown error"
                # Truncate long error messages
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                summary = f"Failed: {error_msg}"
            elif job.status == "running":
                summary = "Running..."
            elif job.status == "pending":
                summary = "Pending..."
            else:
                summary = f"Status: {job.status}"

            # Determine executed_at (use completed_at if available, otherwise started_at)
            executed_at = job.completed_at if job.completed_at else job.started_at

            # Format dates to ISO format strings
            started_at_str = job.started_at.isoformat() if job.started_at else None
            completed_at_str = job.completed_at.isoformat() if job.completed_at else None
            executed_at_str = executed_at.isoformat() if executed_at else None

            jobs_data.append(
                {
                    "id": job.id,
                    "job_name": job_name,
                    "service": service,
                    "status": job.status,
                    "started_at": started_at_str,
                    "completed_at": completed_at_str,
                    "executed_at": executed_at_str,
                    "summary": summary,
                    "error_message": job.error_message,
                }
            )

        return jsonify({"jobs": jobs_data})

    except OperationalError as e:
        current_app.logger.error(f"Error fetching recent jobs: {e}", exc_info=True)
        # Return empty jobs array on error
        return jsonify({"jobs": []})


@bp.route("/api/dashboard/upcoming", methods=["GET"])
def upcoming_jobs():
    """
    Returns the next 5 scheduled jobs for dashboard display.

    Returns:
        JSON response with structure:
        {
            "upcoming": [
                {
                    "list_id": int,
                    "list_name": str,
                    "service": str,
                    "next_run": str (ISO format),
                    "next_run_relative": str
                }
            ],
            "scheduler_paused": bool
        }
    """
    try:
        # Check if scheduler is paused
        config = ServiceConfig.query.first()
        scheduler_paused = config.scheduler_paused if config else False

        # Query all lists with schedules that are active (exclude manual-only lists)
        scheduled_lists = List.query.filter(
            List.schedule_cron.isnot(None),
            List.schedule_cron != "",
            List.is_active == True,  # noqa: E712
        ).all()

        # Get next run times and sort by soonest
        upcoming = []
        for list_obj in scheduled_lists:
            next_run = get_next_run_time(list_obj.id)
            if next_run:
                upcoming.append(
                    {
                        "list_id": list_obj.id,
                        "list_name": list_obj.name,
                        "service": list_obj.target_service,
                        "next_run": next_run.isoformat(),
                        "next_run_relative": format_relative_time(next_run),
                        "_sort_key": next_run,  # For sorting
                    }
                )

        # Sort by next run time (soonest first)
        upcoming.sort(key=lambda x: x["_sort_key"])

        # Remove sort key and limit to 5
        for item in upcoming:
            del item["_sort_key"]
        upcoming = upcoming[:5]

        return jsonify({"upcoming": upcoming, "scheduler_paused": scheduler_paused})

    except OperationalError as e:
        current_app.logger.error(f"Error fetching upcoming jobs: {e}", exc_info=True)
        # Return empty array on error
        return jsonify({"upcoming": [], "scheduler_paused": False})
