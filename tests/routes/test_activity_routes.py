"""
Route tests for activity_routes.py - Activity page endpoints.

Tests cover:
- GET /activity - Activity page rendering
- GET /api/activity - Paginated activity list with filters
- GET /api/activity/<id> - Activity detail with items
- POST /api/activity/<id>/rerun - Rerun a failed activity
- POST /api/activity/clear - Clear all non-running activities
- POST /api/activity/clear/<list_id> - Clear activities for specific list
- GET /api/activity/running - Get currently running activities
- GET /activity/<run_id> - Activity run detail stub

Isolation pattern: Use db.session directly (no nested with app.app_context()
blocks). The session-scoped app fixture keeps an app context open for the
entire session; nested contexts corrupt Flask's ContextVar stack.

Note on rerun endpoint: submit_job and is_list_running are imported INSIDE
the rerun_activity() function body (deferred import to avoid circular imports).
This means they do NOT exist on the listarr.routes.activity_routes module.
Patch at listarr.services.job_executor.submit_job (the source module).

Phase 7 baseline (captured 2026-04-21):
- Overall coverage: 49% (2883 statements, 1483 missed)
- Target: 65% (CI threshold 60%)
- Top uncovered (input for Plan 05 gap closure decision):
  * listarr/routes/lists_routes.py: 17%
  * listarr/services/import_service.py: 48%
  * listarr/services/tmdb_cache.py: 30%
  * listarr/routes/settings_routes.py: 28%
  * listarr/routes/activity_routes.py: 94%
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


class TestActivityPage:
    """Tests for GET /activity page."""

    def test_renders_activity_page(self, client):
        """Activity page renders with 200 status."""
        response = client.get("/activity")
        assert response.status_code == 200


class TestGetActivity:
    """Tests for GET /api/activity endpoint."""

    def test_returns_empty_list_when_no_jobs(self, client):
        """Returns empty list when no jobs exist."""
        response = client.get("/api/activity")
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

        response = client.get("/api/activity?page=1&per_page=10")
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

        response = client.get("/api/activity?status=failed")
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

        response = client.get(f"/api/activity?list_id={list1_id}")
        data = response.get_json()
        assert data["total"] == 2

    def test_max_per_page_enforced_at_50(self, client, app):
        """per_page is capped at 50."""
        test_list = _make_list()
        for i in range(60):
            _make_job(test_list, status="completed")
        db.session.commit()

        response = client.get("/api/activity?per_page=100")
        data = response.get_json()
        assert len(data["jobs"]) == 50

    def test_default_pagination(self, client, app):
        """Default page=1, per_page=25."""
        test_list = _make_list()
        for i in range(30):
            _make_job(test_list, status="completed")
        db.session.commit()

        response = client.get("/api/activity")
        data = response.get_json()
        assert len(data["jobs"]) == 25
        assert data["current_page"] == 1


class TestGetActivityListDeleted:
    """Tests for list_deleted field in GET /api/activity response."""

    def test_list_deleted_true_for_orphaned_job(self, client, app):
        """Returns true when the job's list_id points to a deleted list."""
        test_list = _make_list()
        job = _make_job(test_list)
        db.session.flush()
        list_id = test_list.id
        job_id = job.id

        db.session.delete(test_list)
        db.session.commit()

        response = client.get("/api/activity")

        assert response.status_code == 200
        data = response.get_json()
        assert data["jobs"][0]["id"] == job_id
        assert data["jobs"][0]["list_deleted"] is True
        assert data["jobs"][0]["list_id"] == list_id

    def test_list_deleted_false_for_existing_list(self, client, app):
        """Returns false when the job's list still exists."""
        test_list = _make_list()
        _make_job(test_list)
        db.session.commit()

        response = client.get("/api/activity")

        assert response.status_code == 200
        data = response.get_json()
        assert data["jobs"][0]["list_deleted"] is False

    def test_list_deleted_false_for_null_list_id(self, client, app):
        """Returns false when the job never had a list_id."""
        job = Job(
            list_id=None,
            list_name="Orphan",
            status="completed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.session.add(job)
        db.session.commit()

        response = client.get("/api/activity")

        assert response.status_code == 200
        data = response.get_json()
        assert data["jobs"][0]["list_deleted"] is False


class TestGetActivityDetail:
    """Tests for GET /api/activity/<id> endpoint."""

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

        response = client.get(f"/api/activity/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["list_name"] == "Test List"
        assert len(data["items"]) == 2

    def test_returns_404_for_missing_job(self, client):
        """Returns 404 when job does not exist."""
        response = client.get("/api/activity/99999")
        assert response.status_code == 404


class TestRerunActivity:
    """Tests for POST /api/activity/<id>/rerun endpoint."""

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

            response = client.post(f"/api/activity/{job_id}/rerun")

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

        response = client.post(f"/api/activity/{job_id}/rerun")
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

        response = client.post(f"/api/activity/{job_id}/rerun")
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

        response = client.post(f"/api/activity/{job_id}/rerun")
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
            response = client.post(f"/api/activity/{job_id}/rerun")

        assert response.status_code == 400
        data = response.get_json()
        assert "already has a job running" in data["message"].lower()


class TestClearAllActivity:
    """Tests for POST /api/activity/clear endpoint."""

    def test_clears_completed_and_failed_jobs(self, client, app):
        """Clears completed and failed jobs but not running ones."""
        test_list = _make_list()
        _make_job(test_list, status="completed")
        _make_job(test_list, status="failed")
        _make_job(test_list, status="running")
        db.session.commit()

        response = client.post("/api/activity/clear")
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

        client.post("/api/activity/clear")

        remaining = Job.query.all()
        assert len(remaining) == 1
        assert remaining[0].id == running_id

    def test_returns_deleted_count(self, client, app):
        """Returns the count of deleted jobs."""
        test_list = _make_list()
        for _ in range(5):
            _make_job(test_list, status="completed")
        db.session.commit()

        response = client.post("/api/activity/clear")
        data = response.get_json()
        assert data["deleted_count"] == 5


class TestClearListActivity:
    """Tests for POST /api/activity/clear/<list_id> endpoint."""

    def test_clears_jobs_for_specific_list(self, client, app):
        """Only clears completed/failed jobs for the specified list."""
        list1 = _make_list(name="List 1")
        list2 = _make_list(name="List 2")
        _make_job(list1, status="completed")
        _make_job(list1, status="completed")
        _make_job(list2, status="completed")
        db.session.commit()
        list1_id = list1.id

        response = client.post(f"/api/activity/clear/{list1_id}")
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

        response = client.post(f"/api/activity/clear/{list_id}")
        data = response.get_json()
        assert data["deleted_count"] == 1

        remaining = Job.query.all()
        assert len(remaining) == 1
        assert remaining[0].id == running_id


class TestGetRunningActivity:
    """Tests for GET /api/activity/running endpoint."""

    def test_returns_empty_when_no_running_jobs(self, client):
        """Returns empty list when no running jobs exist."""
        response = client.get("/api/activity/running")
        assert response.status_code == 200
        data = response.get_json()
        assert data["running_jobs"] == []

    def test_returns_running_jobs(self, client, app):
        """Returns only running jobs."""
        first_list = _make_list(name="Running List 1")
        second_list = _make_list(name="Running List 2")
        _make_job(first_list, status="running")
        _make_job(second_list, status="running")
        _make_job(first_list, status="completed")
        db.session.commit()

        response = client.get("/api/activity/running")
        data = response.get_json()
        assert len(data["running_jobs"]) == 2
        for job in data["running_jobs"]:
            assert "job_id" in job
            assert "list_id" in job
            assert "list_name" in job


class TestActivityRunDetail:
    """Tests for /activity/<run_id> stub route."""

    def test_run_detail_returns_200(self, client):
        """Activity run detail stub returns 200."""
        response = client.get("/activity/1")
        assert response.status_code == 200
        assert b"Run Detail" in response.data


class TestAuthEnforcementActivity:
    """
    Auth enforcement for every @login_required route in activity_routes.py.

    Per D-03 (audit every @login_required route), D-04 (HTML -> 302 /login),
    D-05 (JSON -> 401), D-06 (use app_with_auth + auth_client).

    test_user is required because app_with_auth does NOT create a session-level
    user; without one, check_setup() redirects to /setup, not /login (Pitfall 1).
    """

    def test_activity_page_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/activity")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_activity_run_detail_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/activity/1")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_api_activity_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/api/activity", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 401

    def test_api_activity_detail_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/api/activity/1", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 401

    def test_api_activity_rerun_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/api/activity/1/rerun", json={})
        assert response.status_code == 401

    def test_api_activity_clear_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/api/activity/clear", json={})
        assert response.status_code == 401

    def test_api_activity_clear_list_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/api/activity/clear/1", json={})
        assert response.status_code == 401

    def test_api_activity_running_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/api/activity/running", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 401


class TestCsrfProtectionActivity:
    """
    CSRF rejection for every POST endpoint in activity_routes.py.

    Per D-07 (every POST gets a CSRF test), D-08 (status 400 is sufficient;
    no body assertion), D-09 (use client_with_csrf + submit POST without token).

    LOGIN_DISABLED=True in app_with_csrf, so these requests reach the CSRF
    check rather than the @login_required gate.
    """

    def test_api_activity_rerun_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/api/activity/1/rerun", json={})
        assert response.status_code == 400

    def test_api_activity_clear_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/api/activity/clear", json={})
        assert response.status_code == 400

    def test_api_activity_clear_list_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/api/activity/clear/1", json={})
        assert response.status_code == 400
