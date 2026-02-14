"""Jobs routes - API endpoints for job history and management."""

from flask import current_app, jsonify, render_template, request
from flask_login import login_required

from listarr import csrf, db
from listarr.models.jobs_model import Job, JobItem
from listarr.models.lists_model import List
from listarr.routes import bp


@bp.route("/jobs")
@login_required
def jobs_page():
    """Render the Jobs page."""
    return render_template("jobs.html")


@bp.route("/api/jobs")
@login_required
def get_jobs():
    """
    Get paginated job history with optional filters.

    Query params:
        page: int (default 1)
        per_page: int (default 25, max 50)
        list_id: int (optional filter)
        status: string (optional filter: running/completed/failed)

    Returns:
        JSON with jobs array, total count, pages, current_page
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 25, type=int), 50)
    list_id = request.args.get("list_id", type=int)
    status = request.args.get("status", type=str)

    query = Job.query.order_by(Job.started_at.desc())

    if list_id:
        query = query.filter_by(list_id=list_id)
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "jobs": [job.to_dict() for job in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@bp.route("/api/jobs/recent")
@login_required
def get_recent_jobs():
    """
    Get 5 most recent jobs for dashboard widget.

    Returns:
        JSON with jobs array (max 5)
    """
    jobs = Job.query.order_by(Job.started_at.desc()).limit(5).all()

    # Include list's target_service for display
    result = []
    for job in jobs:
        job_dict = job.to_dict()
        # Get service from list if still exists
        list_obj = List.query.get(job.list_id)
        job_dict["target_service"] = list_obj.target_service if list_obj else None
        result.append(job_dict)

    return jsonify({"jobs": result})


@bp.route("/api/jobs/<int:job_id>")
@login_required
def get_job_detail(job_id):
    """
    Get job detail with item breakdown.

    Returns:
        JSON with job info and items array
    """
    job = Job.query.get_or_404(job_id)

    job_dict = job.to_dict()

    # Get job items
    items = JobItem.query.filter_by(job_id=job_id).all()
    job_dict["items"] = [item.to_dict() for item in items]

    return jsonify(job_dict)


@bp.route("/api/jobs/<int:job_id>/rerun", methods=["POST"])
@csrf.exempt
@login_required
def rerun_job(job_id):
    """
    Rerun a job (triggers new import for the same list).

    Only allows rerun of failed jobs.

    Returns:
        202 with new job_id on success
        400 if job is not failed or list is missing/inactive
        404 if job not found
    """
    job = Job.query.get_or_404(job_id)

    # Only allow rerun of failed jobs
    if job.status != "failed":
        return jsonify({"success": False, "error": "Can only rerun failed jobs"}), 400

    # Check if list still exists
    list_obj = List.query.get(job.list_id)
    if not list_obj:
        return jsonify({"success": False, "error": "List no longer exists"}), 400

    # Check if list is active
    if not list_obj.is_active:
        return (
            jsonify({"success": False, "error": f"List '{list_obj.name}' is not active"}),
            400,
        )

    # Import here to avoid circular import

    from listarr.services.job_executor import is_list_running, submit_job

    # Check if already running
    if is_list_running(list_obj.id):
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"List '{list_obj.name}' already has a job running",
                }
            ),
            400,
        )

    # Submit new job
    try:
        app = current_app._get_current_object()
        new_job_id = submit_job(list_obj.id, list_obj.name, app, triggered_by="manual")

        return (
            jsonify({"success": True, "job_id": new_job_id, "status": "started"}),
            202,
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error rerunning job {job_id}: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to start job"}), 500


@bp.route("/api/jobs/clear", methods=["POST"])
@csrf.exempt
@login_required
def clear_all_jobs():
    """
    Clear all job history (global).

    Only clears completed and failed jobs, not running ones.

    Returns:
        JSON with count of deleted jobs
    """
    # Get IDs of jobs to delete (not running)
    jobs_to_delete = Job.query.filter(Job.status.in_(["completed", "failed"])).all()
    job_ids = [job.id for job in jobs_to_delete]

    if job_ids:
        # Delete job items first (explicit cascade for bulk delete)
        JobItem.query.filter(JobItem.job_id.in_(job_ids)).delete(synchronize_session=False)

        # Then delete jobs
        Job.query.filter(Job.id.in_(job_ids)).delete(synchronize_session=False)

    db.session.commit()

    return jsonify({"success": True, "deleted_count": len(job_ids)})


@bp.route("/api/jobs/clear/<int:list_id>", methods=["POST"])
@csrf.exempt
@login_required
def clear_list_jobs(list_id):
    """
    Clear job history for a specific list.

    Only clears completed and failed jobs, not running ones.

    Returns:
        JSON with count of deleted jobs
    """
    # Get IDs of jobs to delete (not running)
    jobs_to_delete = Job.query.filter(Job.list_id == list_id, Job.status.in_(["completed", "failed"])).all()
    job_ids = [job.id for job in jobs_to_delete]

    if job_ids:
        # Delete job items first (explicit cascade for bulk delete)
        JobItem.query.filter(JobItem.job_id.in_(job_ids)).delete(synchronize_session=False)

        # Then delete jobs
        Job.query.filter(Job.id.in_(job_ids)).delete(synchronize_session=False)

    db.session.commit()

    return jsonify({"success": True, "deleted_count": len(job_ids)})


@bp.route("/api/jobs/running")
@login_required
def get_running_jobs():
    """
    Get all currently running jobs for polling.

    Returns:
        JSON with array of running job IDs
    """
    jobs = Job.query.filter_by(status="running").all()
    return jsonify(
        {"running_jobs": [{"job_id": job.id, "list_id": job.list_id, "list_name": job.list_name} for job in jobs]}
    )
