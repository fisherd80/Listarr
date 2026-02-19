"""
Route tests for dashboard_routes.py - Dashboard page endpoints.

Tests cover:
- GET / - Dashboard page rendering
- GET /api/dashboard/stats - Dashboard statistics (cache-based)
- GET /api/dashboard/recent-jobs - Recent jobs retrieval
- GET /api/dashboard/upcoming - Upcoming scheduled jobs
- Service status determination (online/offline/not_configured)
- Error handling and graceful degradation

Isolation pattern: Use db.session directly (no nested with app.app_context()
blocks). The session-scoped app fixture keeps an app context open for the
entire session; nested contexts corrupt Flask's ContextVar stack.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from listarr import db
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.services.crypto_utils import encrypt_data


class TestDashboardPage:
    """Tests for GET / endpoint."""

    def test_renders_dashboard_page(self, client):
        """Dashboard page renders with 200 status."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Dashboard" in response.data

    def test_includes_javascript(self, client):
        """Dashboard includes dashboard.js."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"dashboard.js" in response.data

    def test_includes_csrf_token(self, client):
        """Dashboard includes CSRF token meta tag."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"csrf-token" in response.data


class TestDashboardStats:
    """Tests for GET /api/dashboard/stats endpoint."""

    def test_returns_default_not_configured_state(self, client):
        """Returns not_configured state when no services are set up."""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        assert data["radarr"]["configured"] is False
        assert data["radarr"]["status"] == "not_configured"
        assert data["radarr"]["version"] is None
        assert data["radarr"]["total_movies"] == 0
        assert data["radarr"]["missing_movies"] == 0
        assert data["radarr"]["added_by_listarr"] == 0

        assert data["sonarr"]["configured"] is False
        assert data["sonarr"]["status"] == "not_configured"
        assert data["sonarr"]["version"] is None
        assert data["sonarr"]["total_series"] == 0
        assert data["sonarr"]["missing_episodes"] == 0
        assert data["sonarr"]["added_by_listarr"] == 0

    def test_response_structure(self, client):
        """Stats response has expected keys for both services."""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        assert "radarr" in data
        assert "sonarr" in data
        assert "configured" in data["radarr"]
        assert "status" in data["radarr"]
        assert "version" in data["radarr"]
        assert "total_movies" in data["radarr"]
        assert "missing_movies" in data["radarr"]
        assert "added_by_listarr" in data["radarr"]
        assert "total_series" in data["sonarr"]
        assert "missing_episodes" in data["sonarr"]
        assert "added_by_listarr" in data["sonarr"]

    def test_refresh_param_forces_cache_refresh(self, client, app, temp_instance_path):
        """?refresh=true triggers refresh_dashboard_cache."""
        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.services.dashboard_cache.get_radarr_system_status") as mock_status,
            patch("listarr.services.dashboard_cache.get_movie_count") as mock_count,
            patch("listarr.services.dashboard_cache.get_missing_movies_count") as mock_missing,
        ):
            mock_status.return_value = {"version": "4.5.2"}
            mock_count.return_value = 10
            mock_missing.return_value = 1
            response = client.get("/api/dashboard/stats?refresh=true")

        assert response.status_code == 200
        data = response.get_json()
        assert "radarr" in data
        assert "sonarr" in data

    def test_radarr_configured_and_online(self, client, app, temp_instance_path):
        """Radarr configured and reachable shows online status."""
        from listarr.services.dashboard_cache import refresh_dashboard_cache

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.services.dashboard_cache.get_radarr_system_status") as mock_status,
            patch("listarr.services.dashboard_cache.get_movie_count") as mock_count,
            patch("listarr.services.dashboard_cache.get_missing_movies_count") as mock_missing,
        ):
            mock_status.return_value = {"version": "4.5.2.7388"}
            mock_count.return_value = 150
            mock_missing.return_value = 12
            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")
        data = response.get_json()
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "online"
        assert data["radarr"]["version"] == "4.5.2.7388"
        assert data["radarr"]["total_movies"] == 150
        assert data["radarr"]["missing_movies"] == 12

    def test_radarr_configured_but_offline(self, client, app, temp_instance_path):
        """Radarr configured but unreachable shows offline status."""
        from requests.exceptions import RequestException

        from listarr.services.dashboard_cache import refresh_dashboard_cache

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with patch("listarr.services.dashboard_cache.get_radarr_system_status") as mock_status:
            mock_status.side_effect = RequestException("Connection refused")
            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")
        data = response.get_json()
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "offline"
        assert data["radarr"]["version"] is None
        assert data["radarr"]["total_movies"] == 0

    def test_sonarr_configured_and_online(self, client, app, temp_instance_path):
        """Sonarr configured and reachable shows online status."""
        from listarr.services.dashboard_cache import refresh_dashboard_cache

        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.services.dashboard_cache.get_sonarr_system_status") as mock_status,
            patch("listarr.services.dashboard_cache.get_series_count") as mock_count,
            patch("listarr.services.dashboard_cache.get_missing_episodes_count") as mock_missing,
        ):
            mock_status.return_value = {"version": "3.0.10.1567"}
            mock_count.return_value = 85
            mock_missing.return_value = 7
            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")
        data = response.get_json()
        assert data["sonarr"]["configured"] is True
        assert data["sonarr"]["status"] == "online"
        assert data["sonarr"]["version"] == "3.0.10.1567"
        assert data["sonarr"]["total_series"] == 85
        assert data["sonarr"]["missing_episodes"] == 7

    def test_both_services_configured(self, client, app, temp_instance_path):
        """Both services configured and online."""
        from listarr.services.dashboard_cache import refresh_dashboard_cache

        radarr_enc = encrypt_data("radarr_key", instance_path=temp_instance_path)
        sonarr_enc = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        db.session.add(ServiceConfig(service="RADARR", base_url="http://r:7878", api_key_encrypted=radarr_enc))
        db.session.add(ServiceConfig(service="SONARR", base_url="http://s:8989", api_key_encrypted=sonarr_enc))
        db.session.commit()

        with (
            patch("listarr.services.dashboard_cache.get_radarr_system_status") as mock_r,
            patch("listarr.services.dashboard_cache.get_sonarr_system_status") as mock_s,
            patch("listarr.services.dashboard_cache.get_movie_count") as mock_mc,
            patch("listarr.services.dashboard_cache.get_missing_movies_count") as mock_mm,
            patch("listarr.services.dashboard_cache.get_series_count") as mock_sc,
            patch("listarr.services.dashboard_cache.get_missing_episodes_count") as mock_me,
        ):
            mock_r.return_value = {"version": "4.5.2"}
            mock_s.return_value = {"version": "3.0.10"}
            mock_mc.return_value = 100
            mock_mm.return_value = 5
            mock_sc.return_value = 50
            mock_me.return_value = 3
            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")
        data = response.get_json()
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "online"
        assert data["sonarr"]["configured"] is True
        assert data["sonarr"]["status"] == "online"

    def test_added_by_listarr_counts_completed_jobs(self, client, app, temp_instance_path):
        """added_by_listarr is sum of items_added across jobs for that service."""
        from listarr.services.dashboard_cache import refresh_dashboard_cache

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        db.session.add(ServiceConfig(service="RADARR", base_url="http://r:7878", api_key_encrypted=encrypted))

        radarr_list = List(
            name="Test Movies",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
        )
        db.session.add(radarr_list)
        db.session.flush()

        job1 = Job(
            list_id=radarr_list.id,
            status="completed",
            items_added=45,
            items_skipped=5,
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
        )
        job2 = Job(
            list_id=radarr_list.id,
            status="completed",
            items_added=25,
            items_skipped=5,
            started_at=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 14, 10, 3, 0, tzinfo=timezone.utc),
        )
        # Failed job with 0 items — should not contribute
        job3 = Job(
            list_id=radarr_list.id,
            status="failed",
            items_added=0,
            items_skipped=0,
            started_at=datetime(2024, 1, 13, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 13, 10, 0, 30, tzinfo=timezone.utc),
        )
        db.session.add_all([job1, job2, job3])
        db.session.commit()

        with (
            patch("listarr.services.dashboard_cache.get_radarr_system_status") as mock_status,
            patch("listarr.services.dashboard_cache.get_movie_count") as mock_count,
            patch("listarr.services.dashboard_cache.get_missing_movies_count") as mock_missing,
        ):
            mock_status.return_value = {"version": "4.5.2"}
            mock_count.return_value = 150
            mock_missing.return_value = 12
            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")
        data = response.get_json()
        # 45 + 25 = 70 items added
        assert data["radarr"]["added_by_listarr"] == 70


class TestDashboardRecentJobs:
    """Tests for GET /api/dashboard/recent-jobs endpoint."""

    def test_returns_empty_when_no_jobs(self, client):
        """Returns empty jobs array when database has no jobs."""
        response = client.get("/api/dashboard/recent-jobs")
        assert response.status_code == 200
        data = response.get_json()
        assert "jobs" in data
        assert len(data["jobs"]) == 0

    def test_returns_jobs_ordered_by_completed_at_desc(self, client, app):
        """Recent jobs are ordered newest first."""
        test_list = List(
            name="Test List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
        )
        db.session.add(test_list)
        db.session.flush()

        job1 = Job(
            list_id=test_list.id,
            status="completed",
            items_added=10,
            started_at=datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 10, 10, 5, 0, tzinfo=timezone.utc),
        )
        job2 = Job(
            list_id=test_list.id,
            status="completed",
            items_added=20,
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
        )
        job3 = Job(
            list_id=test_list.id,
            status="completed",
            items_added=30,
            started_at=datetime(2024, 1, 12, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 12, 10, 5, 0, tzinfo=timezone.utc),
        )
        db.session.add_all([job1, job2, job3])
        db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        data = response.get_json()
        assert len(data["jobs"]) == 3
        # Ordered by completed_at desc: job2 (Jan 15), job3 (Jan 12), job1 (Jan 10)
        assert "20 added" in data["jobs"][0]["summary"]
        assert "30 added" in data["jobs"][1]["summary"]
        assert "10 added" in data["jobs"][2]["summary"]

    def test_limits_to_5_jobs(self, client, app):
        """Only the 5 most recent finished jobs are returned."""
        test_list = List(
            name="Test List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
        )
        db.session.add(test_list)
        db.session.flush()

        for i in range(10):
            job = Job(
                list_id=test_list.id,
                status="completed",
                items_added=i + 1,
                started_at=datetime(2024, 1, i + 1, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, i + 1, 10, 5, 0, tzinfo=timezone.utc),
            )
            db.session.add(job)
        db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        data = response.get_json()
        assert len(data["jobs"]) == 5

    def test_handles_deleted_list(self, client, app):
        """Jobs whose list was deleted fall back to list_name."""
        test_list = List(
            name="Deleted List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
        )
        db.session.add(test_list)
        db.session.flush()
        list_id = test_list.id

        job = Job(
            list_id=list_id,
            list_name="Deleted List",
            status="completed",
            items_added=10,
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
        )
        db.session.add(job)
        db.session.commit()

        # Delete the list
        db.session.delete(test_list)
        db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        data = response.get_json()
        assert len(data["jobs"]) == 1
        # Should use denormalized list_name from Job
        assert data["jobs"][0]["job_name"] == "Deleted List"
        assert data["jobs"][0]["service"] == "Unknown"

    def test_handles_null_list_id(self, client, app):
        """Jobs with list_id=None use fallback name."""
        job = Job(
            list_id=None,
            status="completed",
            items_added=10,
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

        response = client.get("/api/dashboard/recent-jobs")
        data = response.get_json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_name"] == f"Job #{job_id}"
        assert data["jobs"][0]["service"] == "Unknown"

    def test_only_returns_finished_jobs(self, client, app):
        """Only jobs with completed_at set are returned (not running/pending)."""
        test_list = List(
            name="Test List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
        )
        db.session.add(test_list)
        db.session.flush()

        finished = Job(
            list_id=test_list.id,
            status="completed",
            items_added=10,
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
        )
        running = Job(
            list_id=test_list.id,
            status="running",
            items_added=0,
            started_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            completed_at=None,
        )
        db.session.add_all([finished, running])
        db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        data = response.get_json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "completed"

    def test_completed_job_summary_format(self, client, app):
        """Completed job summaries show added/skipped counts."""
        test_list = List(
            name="Test List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
        )
        db.session.add(test_list)
        db.session.flush()

        job_both = Job(
            list_id=test_list.id,
            status="completed",
            items_added=15,
            items_skipped=5,
            completed_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        job_only_added = Job(
            list_id=test_list.id,
            status="completed",
            items_added=10,
            items_skipped=0,
            completed_at=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
        )
        job_only_skipped = Job(
            list_id=test_list.id,
            status="completed",
            items_added=0,
            items_skipped=5,
            completed_at=datetime(2024, 1, 13, 10, 0, 0, tzinfo=timezone.utc),
        )
        job_empty = Job(
            list_id=test_list.id,
            status="completed",
            items_added=0,
            items_skipped=0,
            completed_at=datetime(2024, 1, 12, 10, 0, 0, tzinfo=timezone.utc),
        )
        db.session.add_all([job_both, job_only_added, job_only_skipped, job_empty])
        db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        data = response.get_json()
        assert len(data["jobs"]) == 4
        assert "15 added" in data["jobs"][0]["summary"]
        assert "5 skipped" in data["jobs"][0]["summary"]
        assert data["jobs"][1]["summary"] == "10 added"
        assert data["jobs"][2]["summary"] == "5 skipped"
        assert data["jobs"][3]["summary"] == "No items processed"

    def test_failed_job_summary_format(self, client, app):
        """Failed job summary shows error message."""
        test_list = List(
            name="Test List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
        )
        db.session.add(test_list)
        db.session.flush()

        job = Job(
            list_id=test_list.id,
            status="failed",
            items_added=0,
            error_message="Connection timeout",
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 0, 30, tzinfo=timezone.utc),
        )
        db.session.add(job)
        db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        data = response.get_json()
        assert len(data["jobs"]) == 1
        assert "Connection timeout" in data["jobs"][0]["summary"]
        assert "Failed" in data["jobs"][0]["summary"]

    def test_truncates_long_error_messages(self, client, app):
        """Long error messages are truncated at 100 chars."""
        test_list = List(
            name="Test List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
        )
        db.session.add(test_list)
        db.session.flush()

        long_error = "A" * 200
        job = Job(
            list_id=test_list.id,
            status="failed",
            items_added=0,
            error_message=long_error,
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 0, 30, tzinfo=timezone.utc),
        )
        db.session.add(job)
        db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        data = response.get_json()
        summary = data["jobs"][0]["summary"]
        assert summary.endswith("...")
        # "Failed: " + 100 chars + "..."
        assert len(summary) < 120


class TestDashboardUpcoming:
    """Tests for GET /api/dashboard/upcoming endpoint."""

    def test_returns_empty_when_no_scheduled_lists(self, client):
        """Returns empty upcoming array when no lists have schedules."""
        response = client.get("/api/dashboard/upcoming")
        assert response.status_code == 200
        data = response.get_json()
        assert "upcoming" in data
        assert data["upcoming"] == []
        assert "scheduler_paused" in data

    def test_returns_scheduled_lists(self, client, app):
        """Returns lists with cron schedules and next run times."""
        scheduled_list = List(
            name="Scheduled List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
            schedule_cron="0 * * * *",
            is_active=True,
        )
        db.session.add(scheduled_list)
        db.session.commit()
        list_id = scheduled_list.id

        next_run = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        with patch("listarr.routes.dashboard_routes.get_next_run_time") as mock_next:
            mock_next.return_value = next_run
            response = client.get("/api/dashboard/upcoming")

        data = response.get_json()
        assert len(data["upcoming"]) == 1
        assert data["upcoming"][0]["list_id"] == list_id
        assert data["upcoming"][0]["list_name"] == "Scheduled List"
        assert data["upcoming"][0]["service"] == "RADARR"

    def test_includes_scheduler_paused_state(self, client, app):
        """Returns scheduler_paused flag from ServiceConfig."""
        config = ServiceConfig(
            service="RADARR",
            api_key_encrypted="enc_key",
            base_url="http://r:7878",
            scheduler_paused=True,
        )
        db.session.add(config)
        db.session.commit()

        response = client.get("/api/dashboard/upcoming")
        data = response.get_json()
        assert data["scheduler_paused"] is True

    def test_only_includes_active_lists_with_cron(self, client, app):
        """Only active lists with non-empty cron are included."""
        inactive_list = List(
            name="Inactive List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
            schedule_cron="0 * * * *",
            is_active=False,
        )
        no_cron_list = List(
            name="No Cron List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
            schedule_cron=None,
            is_active=True,
        )
        active_list = List(
            name="Active List",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={},
            schedule_cron="0 * * * *",
            is_active=True,
        )
        db.session.add_all([inactive_list, no_cron_list, active_list])
        db.session.commit()

        next_run = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        with patch("listarr.routes.dashboard_routes.get_next_run_time") as mock_next:
            mock_next.return_value = next_run
            response = client.get("/api/dashboard/upcoming")

        data = response.get_json()
        # Only the active list with cron should appear
        assert len(data["upcoming"]) == 1
        assert data["upcoming"][0]["list_name"] == "Active List"
