"""
Route tests for lists_routes.py - List import job endpoints.

Tests cover:
- POST /lists/<id>/run - Trigger list import via job_executor
- GET /lists/<id>/status - Get job status from database
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from listarr import db
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List


def create_test_list(name, is_active=True, last_run_at=None):
    """Helper to create a test list with required fields."""
    return List(
        name=name,
        target_service="RADARR",
        tmdb_list_type="trending_movies",
        filters_json={},
        is_active=is_active,
        last_run_at=last_run_at,
    )


class TestRunListImport:
    """Tests for POST /lists/<id>/run endpoint."""

    def test_returns_404_for_missing_list(self, client):
        """Returns 404 when list doesn't exist."""
        response = client.post("/lists/999/run")
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "not found" in data["message"]

    def test_returns_400_for_inactive_list(self, client, app):
        """Returns 400 when list is inactive."""
        with app.app_context():
            test_list = create_test_list("Inactive List", is_active=False)
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

        response = client.post(f"/lists/{list_id}/run")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "not active" in data["message"]

    def test_returns_400_when_already_running(self, client, app):
        """Returns 400 when job already running for this list."""
        with app.app_context():
            test_list = create_test_list("Running List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

            # Create running job
            job = Job(
                list_id=list_id,
                list_name="Running List",
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

        response = client.post(f"/lists/{list_id}/run")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "already running" in data["message"]

    @patch("listarr.routes.lists_routes.submit_job")
    def test_submits_job_successfully(self, mock_submit, client, app):
        """Returns 202 when job submitted successfully."""
        mock_submit.return_value = 123  # job_id

        with app.app_context():
            test_list = create_test_list("Test List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

        response = client.post(f"/lists/{list_id}/run")
        assert response.status_code == 202
        data = response.get_json()
        assert data["success"] is True
        assert data["job_id"] == 123
        assert data["status"] == "started"

    @patch("listarr.routes.lists_routes.submit_job")
    def test_handles_value_error_from_submit(self, mock_submit, client, app):
        """Returns 400 when submit_job raises ValueError."""
        mock_submit.side_effect = ValueError("Job already running for list 1")

        with app.app_context():
            test_list = create_test_list("Test List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

        response = client.post(f"/lists/{list_id}/run")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        # Generic error message (specific errors not exposed per security policy)
        assert "Invalid request" in data["message"]

    @patch("listarr.routes.lists_routes.submit_job")
    def test_handles_unexpected_exception(self, mock_submit, client, app):
        """Returns 500 when submit_job raises unexpected exception."""
        mock_submit.side_effect = RuntimeError("Database connection lost")

        with app.app_context():
            test_list = create_test_list("Test List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

        response = client.post(f"/lists/{list_id}/run")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to start job" in data["message"]


class TestGetListStatus:
    """Tests for GET /lists/<id>/status endpoint."""

    def test_returns_404_for_missing_list(self, client):
        """Returns 404 when list doesn't exist."""
        response = client.get("/lists/999/status")
        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"]

    def test_returns_idle_when_no_jobs(self, client, app):
        """Returns idle status when no jobs exist for list."""
        with app.app_context():
            test_list = create_test_list("No Jobs List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

        response = client.get(f"/lists/{list_id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "idle"
        assert data["list_id"] == list_id

    def test_returns_running_when_job_running(self, client, app):
        """Returns running status when job is currently running."""
        with app.app_context():
            test_list = create_test_list("Running Status List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

            job = Job(
                list_id=list_id,
                list_name="Running Status List",
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

        response = client.get(f"/lists/{list_id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "running"
        assert data["list_id"] == list_id

    def test_returns_completed_with_results(self, client, app):
        """Returns completed status with result summary."""
        with app.app_context():
            test_list = create_test_list("Completed List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

            job = Job(
                list_id=list_id,
                list_name="Completed List",
                status="completed",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                items_found=10,
                items_added=5,
                items_skipped=3,
                items_failed=2,
            )
            db.session.add(job)
            db.session.commit()

        response = client.get(f"/lists/{list_id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "completed"
        assert data["list_id"] == list_id
        assert "result" in data
        assert data["result"]["summary"]["total"] == 10
        assert data["result"]["summary"]["added_count"] == 5
        assert data["result"]["summary"]["skipped_count"] == 3
        assert data["result"]["summary"]["failed_count"] == 2

    def test_returns_failed_with_error_message(self, client, app):
        """Returns failed status with error message."""
        with app.app_context():
            test_list = create_test_list("Failed List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

            job = Job(
                list_id=list_id,
                list_name="Failed List",
                status="failed",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                error_message="TMDB API unavailable",
            )
            db.session.add(job)
            db.session.commit()

        response = client.get(f"/lists/{list_id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "failed"
        assert data["list_id"] == list_id
        assert data["error"] == "TMDB API unavailable"

    def test_includes_last_run_at_timestamp(self, client, app):
        """Includes last_run_at timestamp from list model."""
        run_time = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        with app.app_context():
            test_list = create_test_list("With Last Run", last_run_at=run_time)
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

        response = client.get(f"/lists/{list_id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["last_run_at"] is not None
        assert "2026-01-15" in data["last_run_at"]

    def test_returns_most_recent_job_status(self, client, app):
        """Returns status from most recent job when multiple exist."""
        with app.app_context():
            test_list = create_test_list("Multiple Jobs List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

            # Old completed job
            old_job = Job(
                list_id=list_id,
                list_name="Multiple Jobs List",
                status="completed",
                started_at=datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 1, 10, 10, 5, 0, tzinfo=timezone.utc),
                items_found=5,
                items_added=5,
                items_skipped=0,
                items_failed=0,
            )
            db.session.add(old_job)

            # New running job
            new_job = Job(
                list_id=list_id,
                list_name="Multiple Jobs List",
                status="running",
                started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            )
            db.session.add(new_job)
            db.session.commit()

        response = client.get(f"/lists/{list_id}/status")
        assert response.status_code == 200
        data = response.get_json()
        # Should return the most recent job (running)
        assert data["status"] == "running"

    def test_maps_unknown_status_to_idle(self, client, app):
        """Unknown job statuses are mapped to idle for frontend."""
        with app.app_context():
            test_list = create_test_list("Pending List")
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

            # Job with status that's not running/completed/failed
            job = Job(
                list_id=list_id,
                list_name="Pending List",
                status="pending",  # Not a standard status
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

        response = client.get(f"/lists/{list_id}/status")
        assert response.status_code == 200
        data = response.get_json()
        # Unknown status should map to idle
        assert data["status"] == "idle"
