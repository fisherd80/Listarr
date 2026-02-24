"""
Route tests for jobs_routes.py - Jobs page endpoints.

Tests cover:
- GET /jobs - Jobs page rendering
- GET /api/jobs - Paginated job list with filters
- GET /api/jobs/recent - 5 most recent jobs for dashboard widget
- GET /api/jobs/<id> - Job detail with items
- POST /api/jobs/<id>/rerun - Rerun a failed job
- POST /api/jobs/clear - Clear all non-running jobs
- POST /api/jobs/clear/<list_id> - Clear jobs for specific list
- GET /api/jobs/running - Get currently running jobs

Isolation pattern: Use db.session directly (no nested with app.app_context()
blocks). The session-scoped app fixture keeps an app context open for the
entire session; nested contexts corrupt Flask's ContextVar stack.

Note on rerun endpoint: submit_job and is_list_running are imported INSIDE
the rerun_job() function body (deferred import to avoid circular imports).
This means they do NOT exist on the listarr.routes.jobs_routes module.
Patch at listarr.services.job_executor.submit_job (the source module).
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from listarr import db
from listarr.models.jobs_model import Job, JobItem
from listarr.models.lists_model import List


def _make_list(name="Test List", service="RADARR", list_type="trending_movies"):
    """Create and flush a List without committing."""
    lst = List(
        name=name,
        target_service=service,
        tmdb_list_type=list_type,
        filters_json={},
        is_active=True,
    )
    db.session.add(lst)
    db.session.flush()
    return lst


def _make_job(list_obj, status="completed", items_added=0, items_skipped=0):
    """Create a Job for the given list. Does not commit."""
    job = Job(
        list_id=list_obj.id,
        list_name=list_obj.name,
        status=status,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc) if status != "running" else None,
        items_added=items_added,
        items_skipped=items_skipped,
    )
    db.session.add(job)
    return job


class TestJobsPage:
    """Tests for GET /jobs page."""

    def test_renders_jobs_page(self, client):
        """Jobs page renders with 200 status."""
        response = client.get("/jobs")
        assert response.status_code == 200


class TestGetJobs:
    """Tests for GET /api/jobs endpoint."""

    def test_returns_empty_list_when_no_jobs(self, client):
        """Returns empty list when no jobs exist."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.get_json()
        assert data["jobs"] == []
        assert data["total"] == 0

    def test_returns_paginated_jobs(self, client, app):
        """Returns paginated job list."""
        test_list = _make_list()
        for i in range(30):
            _make_job(test_list, status="completed")
        db.session.commit()

        response = client.get("/api/jobs?page=1&per_page=10")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["jobs"]) == 10
        assert data["total"] == 30
        assert data["pages"] == 3

    def test_filters_by_status(self, client, app):
        """Filters jobs by status."""
        test_list = _make_list()
        _make_job(test_list, status="completed")
        _make_job(test_list, status="completed")
        _make_job(test_list, status="failed")
        db.session.commit()

        response = client.get("/api/jobs?status=failed")
        data = response.get_json()
        assert data["total"] == 1
        assert data["jobs"][0]["status"] == "failed"

    def test_filters_by_list_id(self, client, app):
        """Filters jobs by list_id."""
        list1 = _make_list(name="List 1")
        list2 = _make_list(name="List 2")
        _make_job(list1, status="completed")
        _make_job(list1, status="completed")
        _make_job(list2, status="completed")
        db.session.commit()
        list1_id = list1.id

        response = client.get(f"/api/jobs?list_id={list1_id}")
        data = response.get_json()
        assert data["total"] == 2

    def test_max_per_page_enforced_at_50(self, client, app):
        """per_page is capped at 50."""
        test_list = _make_list()
        for i in range(60):
            _make_job(test_list, status="completed")
        db.session.commit()

        response = client.get("/api/jobs?per_page=100")
        data = response.get_json()
        assert len(data["jobs"]) == 50

    def test_default_pagination(self, client, app):
        """Default page=1, per_page=25."""
        test_list = _make_list()
        for i in range(30):
            _make_job(test_list, status="completed")
        db.session.commit()

        response = client.get("/api/jobs")
        data = response.get_json()
        assert len(data["jobs"]) == 25
        assert data["current_page"] == 1


class TestGetRecentJobs:
    """Tests for GET /api/jobs/recent endpoint."""

    def test_returns_empty_when_no_jobs(self, client):
        """Returns empty list when no jobs exist."""
        response = client.get("/api/jobs/recent")
        assert response.status_code == 200
        data = response.get_json()
        assert data["jobs"] == []

    def test_returns_max_5_jobs(self, client, app):
        """Returns at most 5 recent jobs."""
        test_list = _make_list()
        for i in range(10):
            _make_job(test_list, status="completed")
        db.session.commit()

        response = client.get("/api/jobs/recent")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["jobs"]) == 5

    def test_includes_target_service_from_list(self, client, app):
        """Includes target_service from the related List."""
        radarr_list = _make_list(name="Radarr List", service="RADARR")
        _make_job(radarr_list, status="completed")
        db.session.commit()

        response = client.get("/api/jobs/recent")
        data = response.get_json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["target_service"] == "RADARR"

    def test_handles_deleted_list(self, client, app):
        """Returns null target_service when list no longer exists."""
        test_list = _make_list()
        job = _make_job(test_list, status="completed")
        db.session.commit()
        job_id = job.id

        # Delete the list
        db.session.delete(test_list)
        db.session.commit()

        response = client.get("/api/jobs/recent")
        data = response.get_json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["target_service"] is None


class TestGetJobDetail:
    """Tests for GET /api/jobs/<id> endpoint."""

    def test_returns_job_with_items(self, client, app):
        """Returns job detail including its items."""
        test_list = _make_list()
        job = _make_job(test_list, status="completed", items_added=2)
        db.session.flush()
        job_id = job.id

        item1 = JobItem(job_id=job_id, tmdb_id=101, title="Movie 1", status="added")
        item2 = JobItem(job_id=job_id, tmdb_id=102, title="Movie 2", status="skipped")
        db.session.add_all([item1, item2])
        db.session.commit()

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["list_name"] == "Test List"
        assert len(data["items"]) == 2

    def test_returns_404_for_missing_job(self, client):
        """Returns 404 when job does not exist."""
        response = client.get("/api/jobs/99999")
        assert response.status_code == 404


class TestRerunJob:
    """Tests for POST /api/jobs/<id>/rerun endpoint."""

    def test_rerun_failed_job_returns_202(self, client, app):
        """Reruns a failed job and returns 202."""
        test_list = _make_list()
        job = _make_job(test_list, status="failed")
        db.session.commit()
        job_id = job.id

        with (
            patch("listarr.services.job_executor.submit_job") as mock_submit,
            patch("listarr.services.job_executor.is_list_running") as mock_running,
        ):
            mock_running.return_value = False
            mock_submit.return_value = 99

            response = client.post(f"/api/jobs/{job_id}/rerun")

        assert response.status_code == 202
        data = response.get_json()
        assert data["success"] is True
        assert data["job_id"] == 99

    def test_rerun_non_failed_job_returns_400(self, client, app):
        """Returns 400 when trying to rerun a non-failed job."""
        test_list = _make_list()
        job = _make_job(test_list, status="completed")
        db.session.commit()
        job_id = job.id

        response = client.post(f"/api/jobs/{job_id}/rerun")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "only rerun failed jobs" in data["message"].lower()

    def test_rerun_missing_list_returns_400(self, client, app):
        """Returns 400 when job's list no longer exists."""
        test_list = _make_list()
        job = _make_job(test_list, status="failed")
        db.session.commit()
        job_id = job.id
        list_obj = List.query.get(test_list.id)
        db.session.delete(list_obj)
        db.session.commit()

        response = client.post(f"/api/jobs/{job_id}/rerun")
        assert response.status_code == 400
        data = response.get_json()
        assert "no longer exists" in data["message"].lower()

    def test_rerun_inactive_list_returns_400(self, client, app):
        """Returns 400 when job's list is inactive."""
        test_list = List(
            name="Inactive List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
            is_active=False,
        )
        db.session.add(test_list)
        db.session.flush()

        job = _make_job(test_list, status="failed")
        db.session.commit()
        job_id = job.id

        response = client.post(f"/api/jobs/{job_id}/rerun")
        assert response.status_code == 400
        data = response.get_json()
        assert "not active" in data["message"].lower()

    def test_rerun_already_running_returns_400(self, client, app):
        """Returns 400 when list already has a running job."""
        test_list = _make_list()
        job = _make_job(test_list, status="failed")
        db.session.commit()
        job_id = job.id

        with patch("listarr.services.job_executor.is_list_running") as mock_running:
            mock_running.return_value = True
            response = client.post(f"/api/jobs/{job_id}/rerun")

        assert response.status_code == 400
        data = response.get_json()
        assert "already has a job running" in data["message"].lower()


class TestClearAllJobs:
    """Tests for POST /api/jobs/clear endpoint."""

    def test_clears_completed_and_failed_jobs(self, client, app):
        """Clears completed and failed jobs but not running ones."""
        test_list = _make_list()
        _make_job(test_list, status="completed")
        _make_job(test_list, status="failed")
        _make_job(test_list, status="running")
        db.session.commit()

        response = client.post("/api/jobs/clear")
        assert response.status_code == 200
        data = response.get_json()
        assert data["deleted_count"] == 2

    def test_preserves_running_jobs(self, client, app):
        """Running jobs survive a global clear."""
        test_list = _make_list()
        _make_job(test_list, status="completed")
        running = _make_job(test_list, status="running")
        db.session.commit()
        running_id = running.id

        client.post("/api/jobs/clear")

        remaining = Job.query.all()
        assert len(remaining) == 1
        assert remaining[0].id == running_id

    def test_returns_deleted_count(self, client, app):
        """Returns the count of deleted jobs."""
        test_list = _make_list()
        for _ in range(5):
            _make_job(test_list, status="completed")
        db.session.commit()

        response = client.post("/api/jobs/clear")
        data = response.get_json()
        assert data["deleted_count"] == 5


class TestClearListJobs:
    """Tests for POST /api/jobs/clear/<list_id> endpoint."""

    def test_clears_jobs_for_specific_list(self, client, app):
        """Only clears completed/failed jobs for the specified list."""
        list1 = _make_list(name="List 1")
        list2 = _make_list(name="List 2")
        _make_job(list1, status="completed")
        _make_job(list1, status="completed")
        _make_job(list2, status="completed")
        db.session.commit()
        list1_id = list1.id

        response = client.post(f"/api/jobs/clear/{list1_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["deleted_count"] == 2

        remaining = Job.query.all()
        assert len(remaining) == 1

    def test_preserves_running_jobs_for_list(self, client, app):
        """Running jobs for a list survive a per-list clear."""
        test_list = _make_list()
        _make_job(test_list, status="completed")
        running = _make_job(test_list, status="running")
        db.session.commit()
        list_id = test_list.id
        running_id = running.id

        response = client.post(f"/api/jobs/clear/{list_id}")
        data = response.get_json()
        assert data["deleted_count"] == 1

        remaining = Job.query.all()
        assert len(remaining) == 1
        assert remaining[0].id == running_id


class TestGetRunningJobs:
    """Tests for GET /api/jobs/running endpoint."""

    def test_returns_empty_when_no_running_jobs(self, client):
        """Returns empty list when no running jobs exist."""
        response = client.get("/api/jobs/running")
        assert response.status_code == 200
        data = response.get_json()
        assert data["running_jobs"] == []

    def test_returns_running_jobs(self, client, app):
        """Returns only running jobs."""
        test_list = _make_list()
        _make_job(test_list, status="running")
        _make_job(test_list, status="running")
        _make_job(test_list, status="completed")
        db.session.commit()

        response = client.get("/api/jobs/running")
        data = response.get_json()
        assert len(data["running_jobs"]) == 2
        for job in data["running_jobs"]:
            assert "job_id" in job
            assert "list_id" in job
            assert "list_name" in job
