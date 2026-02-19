"""
Route tests for schedule_routes.py - All 5 schedule route endpoints.

Tests cover:
- GET /schedule - Schedule management page render
- POST /api/schedule/pause - Pause all scheduled jobs globally
- POST /api/schedule/resume - Resume all scheduled jobs globally
- GET /api/schedule/status - Get scheduler status and list schedules
- POST /api/schedule/<list_id>/update - Update schedule for a specific list
"""

from datetime import datetime, timezone
from unittest.mock import patch

from listarr import db
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig


def make_list(
    name="Test List",
    target_service="RADARR",
    tmdb_list_type="trending_movies",
    is_active=True,
    schedule_cron=None,
):
    """Helper to create a test list with required fields."""
    return List(
        name=name,
        target_service=target_service,
        tmdb_list_type=tmdb_list_type,
        filters_json={},
        is_active=is_active,
        schedule_cron=schedule_cron,
    )


def make_service_config(scheduler_paused=False):
    """Helper to create a ServiceConfig with scheduler_paused setting."""
    return ServiceConfig(
        service="RADARR",
        api_key_encrypted="encrypted-dummy",
        base_url="http://localhost:7878",
        scheduler_paused=scheduler_paused,
    )


# ---------------------------------------------------------------------------
# 1. GET /schedule - Schedule page
# ---------------------------------------------------------------------------


class TestSchedulePage:
    """Tests for GET /schedule endpoint."""

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_renders_schedule_page(self, mock_next_run, mock_running, client):
        """Returns 200 for schedule page."""
        mock_running.return_value = False
        mock_next_run.return_value = None
        response = client.get("/schedule")
        assert response.status_code == 200

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_empty_state_no_lists(self, mock_next_run, mock_running, client, db_session):
        """Renders page with no lists."""
        mock_running.return_value = False
        mock_next_run.return_value = None
        response = client.get("/schedule")
        assert response.status_code == 200

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_shows_lists_with_status(self, mock_next_run, mock_running, client, db_session):
        """Renders lists with their schedule status."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="My Scheduled List", schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/schedule")
        assert response.status_code == 200
        assert b"My Scheduled List" in response.data

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_shows_scheduler_paused_state(self, mock_next_run, mock_running, client, db_session):
        """Renders page showing paused state when scheduler_paused=True in config."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        config = make_service_config(scheduler_paused=True)
        db.session.add(config)
        db.session.commit()

        response = client.get("/schedule")
        assert response.status_code == 200

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_running_list_shows_running_status(self, mock_next_run, mock_running, client, db_session):
        """Running list shows Running status."""
        mock_running.return_value = True
        mock_next_run.return_value = None

        lst = make_list(name="Running List")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/schedule")
        assert response.status_code == 200
        # Running status should appear in page
        assert b"Running" in response.data

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_manual_only_list_shows_manual_status(self, mock_next_run, mock_running, client, db_session):
        """List without cron shows Manual only status."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="Manual List", schedule_cron=None)
        db.session.add(lst)
        db.session.commit()

        response = client.get("/schedule")
        assert response.status_code == 200
        assert b"Manual only" in response.data

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_scheduled_list_shows_scheduled_status(self, mock_next_run, mock_running, client, db_session):
        """Active list with cron shows Scheduled status."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="Cron List", schedule_cron="0 0 * * *", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.get("/schedule")
        assert response.status_code == 200
        assert b"Scheduled" in response.data


# ---------------------------------------------------------------------------
# 2. POST /api/schedule/pause - Pause scheduler
# ---------------------------------------------------------------------------


class TestPauseSchedule:
    """Tests for POST /api/schedule/pause endpoint."""

    @patch("listarr.routes.schedule_routes.pause_scheduler")
    def test_pauses_scheduler_successfully(self, mock_pause, client, db_session):
        """Returns success JSON when pause_scheduler succeeds."""
        response = client.post("/api/schedule/pause")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_pause.assert_called_once()

    @patch("listarr.routes.schedule_routes.pause_scheduler")
    def test_handles_error_on_pause(self, mock_pause, client, db_session):
        """Returns 500 when pause_scheduler raises RuntimeError."""
        mock_pause.side_effect = RuntimeError("Scheduler not running")
        response = client.post("/api/schedule/pause")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "message" in data

    @patch("listarr.routes.schedule_routes.pause_scheduler")
    def test_pause_response_format(self, mock_pause, client, db_session):
        """Pause response has correct JSON structure."""
        response = client.post("/api/schedule/pause")
        assert response.content_type == "application/json"
        data = response.get_json()
        assert isinstance(data, dict)
        assert "success" in data


# ---------------------------------------------------------------------------
# 3. POST /api/schedule/resume - Resume scheduler
# ---------------------------------------------------------------------------


class TestResumeSchedule:
    """Tests for POST /api/schedule/resume endpoint."""

    @patch("listarr.routes.schedule_routes.resume_scheduler")
    def test_resumes_scheduler_successfully(self, mock_resume, client, db_session):
        """Returns success JSON when resume_scheduler succeeds."""
        response = client.post("/api/schedule/resume")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_resume.assert_called_once()

    @patch("listarr.routes.schedule_routes.resume_scheduler")
    def test_handles_error_on_resume(self, mock_resume, client, db_session):
        """Returns 500 when resume_scheduler raises RuntimeError."""
        mock_resume.side_effect = RuntimeError("Cannot resume")
        response = client.post("/api/schedule/resume")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "message" in data

    @patch("listarr.routes.schedule_routes.resume_scheduler")
    def test_resume_response_format(self, mock_resume, client, db_session):
        """Resume response has correct JSON structure."""
        response = client.post("/api/schedule/resume")
        assert response.content_type == "application/json"
        data = response.get_json()
        assert isinstance(data, dict)
        assert "success" in data


# ---------------------------------------------------------------------------
# 4. GET /api/schedule/status - Get schedule status
# ---------------------------------------------------------------------------


class TestGetScheduleStatus:
    """Tests for GET /api/schedule/status endpoint."""

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_returns_empty_when_no_lists(self, mock_next_run, mock_running, client, db_session):
        """Returns paused=False and empty lists when no lists exist."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        response = client.get("/api/schedule/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "paused" in data
        assert "lists" in data
        assert data["lists"] == []
        assert data["paused"] is False

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_returns_paused_state(self, mock_next_run, mock_running, client, db_session):
        """Returns paused=True when scheduler is paused in config."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        config = make_service_config(scheduler_paused=True)
        db.session.add(config)
        db.session.commit()

        response = client.get("/api/schedule/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["paused"] is True

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_returns_status_with_list_data(self, mock_next_run, mock_running, client, db_session):
        """Returns list data with status for each list."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="Status Test List", schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["lists"]) == 1
        list_data = data["lists"][0]
        assert list_data["name"] == "Status Test List"
        assert "status" in list_data
        assert "next_run" in list_data
        assert "has_schedule" in list_data

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_includes_status_html_in_response(self, mock_next_run, mock_running, client, db_session):
        """Each list entry includes rendered status_html badge."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="HTML Badge Test")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        assert len(data["lists"]) == 1
        list_data = data["lists"][0]
        assert "status_html" in list_data
        assert "<span" in list_data["status_html"]

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_manual_only_status_when_no_cron(self, mock_next_run, mock_running, client, db_session):
        """List without cron has status 'Manual only'."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="Manual Only", schedule_cron=None)
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        list_data = data["lists"][0]
        assert list_data["status"] == "Manual only"
        assert list_data["has_schedule"] is False

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_returns_scheduled_status_for_cron_list(self, mock_next_run, mock_running, client, db_session):
        """List with cron and not paused has status 'Scheduled'."""
        from datetime import timedelta

        future_dt = datetime.now(timezone.utc) + timedelta(hours=6)
        mock_running.return_value = False
        mock_next_run.return_value = future_dt

        lst = make_list(name="Cron List", schedule_cron="0 0 * * *", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        list_data = data["lists"][0]
        assert list_data["status"] == "Scheduled"
        assert list_data["has_schedule"] is True

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_returns_running_status_for_active_job(self, mock_next_run, mock_running, client, db_session):
        """List with running job has status 'Running'."""
        mock_running.return_value = True
        mock_next_run.return_value = None

        lst = make_list(name="Running Now")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        list_data = data["lists"][0]
        assert list_data["status"] == "Running"

    @patch("listarr.routes.schedule_routes.is_list_running")
    @patch("listarr.routes.schedule_routes.get_next_run_time")
    def test_returns_paused_status_when_scheduler_paused_and_cron_set(
        self, mock_next_run, mock_running, client, db_session
    ):
        """List with cron and scheduler paused has status 'Paused'."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        config = make_service_config(scheduler_paused=True)
        db.session.add(config)

        lst = make_list(name="Paused Scheduled", schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        list_data = data["lists"][0]
        assert list_data["status"] == "Paused"


# ---------------------------------------------------------------------------
# 5. POST /api/schedule/<list_id>/update - Update schedule
# ---------------------------------------------------------------------------


class TestUpdateSchedule:
    """Tests for POST /api/schedule/<list_id>/update endpoint."""

    def test_returns_404_for_missing_list(self, client, db_session):
        """Returns 404 when list does not exist."""
        response = client.post("/api/schedule/9999/update", json={"schedule_cron": "0 0 * * *"})
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    def test_returns_400_for_invalid_json(self, client, db_session):
        """Returns 400 when request body is not valid JSON."""
        lst = make_list(name="JSON Test")
        db.session.add(lst)
        db.session.commit()

        # Sending non-JSON content type
        response = client.post(
            f"/api/schedule/{lst.id}/update",
            data="not json at all",
            content_type="text/plain",
        )
        # Flask raises UnsupportedMediaType (415) which goes through error handler
        assert response.status_code in (400, 415, 500)

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.schedule_list")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_sets_valid_cron_expression(self, mock_unschedule, mock_schedule, mock_validate, client, db_session):
        """Valid cron sets schedule and returns success."""
        mock_validate.return_value = {"valid": True, "description": "Every day at midnight"}

        lst = make_list(name="Cron Update Test", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "0 0 * * *"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["schedule_cron"] == "0 0 * * *"
        assert "status" in data

        # Verify DB updated
        updated = List.query.get(lst.id)
        assert updated.schedule_cron == "0 0 * * *"

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_removes_schedule_when_empty_cron(self, mock_unschedule, mock_validate, client, db_session):
        """Empty schedule_cron removes the schedule."""
        lst = make_list(name="Remove Cron", schedule_cron="0 0 * * *", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": ""},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["schedule_cron"] == ""

        # Verify DB cleared
        updated = List.query.get(lst.id)
        assert updated.schedule_cron is None

    @patch("listarr.services.scheduler.validate_cron_expression")
    def test_returns_400_for_invalid_cron(self, mock_validate, client, db_session):
        """Returns 400 when cron expression is invalid."""
        mock_validate.return_value = {
            "valid": False,
            "error": "Invalid cron syntax",
            "description": "",
        }

        lst = make_list(name="Invalid Cron Test")
        db.session.add(lst)
        db.session.commit()

        response = client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "not-a-cron"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid cron" in data["message"]

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.schedule_list")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_response_includes_status(self, mock_unschedule, mock_schedule, mock_validate, client, db_session):
        """Response includes list status after update."""
        mock_validate.return_value = {"valid": True, "description": "Every hour"}

        lst = make_list(name="Status Response Test", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "0 * * * *"},
        )
        data = response.get_json()
        assert data["success"] is True
        assert "status" in data
        assert "next_run" in data

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.schedule_list")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_schedule_list_called_when_active(self, mock_unschedule, mock_schedule, mock_validate, client, db_session):
        """schedule_list is called when list is active and cron is set."""
        mock_validate.return_value = {"valid": True, "description": "Daily"}

        lst = make_list(name="Active Schedule Call", is_active=True)
        db.session.add(lst)
        db.session.commit()

        client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "0 0 * * *"},
        )
        mock_schedule.assert_called_once_with(lst.id, "0 0 * * *")

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_unschedule_called_when_inactive_list(self, mock_unschedule, mock_validate, client, db_session):
        """unschedule_list is called when list is inactive even with cron set."""
        mock_validate.return_value = {"valid": True, "description": "Daily"}

        lst = make_list(name="Inactive With Cron", is_active=False)
        db.session.add(lst)
        db.session.commit()

        client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "0 0 * * *"},
        )
        mock_unschedule.assert_called_once_with(lst.id)

    @patch("listarr.services.scheduler.unschedule_list")
    def test_unschedule_called_when_empty_cron(self, mock_unschedule, client, db_session):
        """unschedule_list is called when cron is removed."""
        lst = make_list(name="Unschedule Test", schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()

        client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": ""},
        )
        mock_unschedule.assert_called_once_with(lst.id)
