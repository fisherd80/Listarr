"""
Route tests for dashboard_routes.py - Dashboard page endpoints.

Tests cover:
- GET / - Dashboard page rendering
- GET /api/dashboard/stats - Dashboard statistics aggregation
- GET /api/dashboard/recent-jobs - Recent jobs retrieval
- Service status determination (online/offline/not_configured)
- Error handling and graceful degradation
- Database operations for jobs
- Parallel API calls and data aggregation
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from listarr import db
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.services.crypto_utils import encrypt_data


class TestDashboardPageGET:
    """Tests for GET / endpoint (dashboard home)."""

    def test_dashboard_page_renders_successfully(self, client):
        """Test that dashboard page renders without errors."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"Dashboard" in response.data

    def test_dashboard_page_shows_radarr_card(self, client):
        """Test that dashboard contains Radarr service card."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"Radarr" in response.data
        assert b"Total Movies" in response.data
        assert b"Missing Movies" in response.data

    def test_dashboard_page_shows_sonarr_card(self, client):
        """Test that dashboard contains Sonarr service card."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"Sonarr" in response.data
        assert b"Total Series" in response.data
        assert b"Missing Episodes" in response.data

    def test_dashboard_page_shows_recent_jobs_section(self, client):
        """Test that dashboard contains recent jobs section."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"Recent Jobs" in response.data
        assert b"Last 5 executed list jobs" in response.data

    def test_dashboard_page_includes_refresh_button(self, client):
        """Test that dashboard includes refresh button."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"refresh-dashboard-btn" in response.data
        assert b"Refresh" in response.data

    def test_dashboard_page_includes_javascript(self, client):
        """Test that dashboard.js is included."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"dashboard.js" in response.data

    def test_dashboard_page_includes_csrf_token(self, client):
        """Test that CSRF token meta tag is present."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"csrf-token" in response.data

    def test_dashboard_page_shows_added_by_listarr(self, client):
        """Test that dashboard contains 'Added by Listarr' text."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"Added by Listarr" in response.data
        assert b"radarr-added-by-listarr" in response.data
        assert b"sonarr-added-by-listarr" in response.data


class TestDashboardStatsGET:
    """Tests for GET /api/dashboard/stats endpoint."""

    def test_dashboard_stats_with_no_services_configured(self, client):
        """Test that stats endpoint returns default values when no services configured."""
        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Verify Radarr defaults
        assert data["radarr"]["configured"] is False
        assert data["radarr"]["status"] == "not_configured"
        assert data["radarr"]["version"] is None
        assert data["radarr"]["total_movies"] == 0
        assert data["radarr"]["missing_movies"] == 0
        assert data["radarr"]["added_by_listarr"] == 0

        # Verify Sonarr defaults
        assert data["sonarr"]["configured"] is False
        assert data["sonarr"]["status"] == "not_configured"
        assert data["sonarr"]["version"] is None
        assert data["sonarr"]["total_series"] == 0
        assert data["sonarr"]["missing_episodes"] == 0
        assert data["sonarr"]["added_by_listarr"] == 0

    def test_dashboard_stats_with_refresh_parameter(
        self, app, client, temp_instance_path
    ):
        """Test that ?refresh=true parameter triggers cache refresh."""
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

        # Request with refresh parameter
        response = client.get("/api/dashboard/stats?refresh=true")
        assert response.status_code == 200
        data = response.get_json()

        # Should return valid structure
        assert "radarr" in data
        assert "sonarr" in data

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_missing_movies_count")
    def test_dashboard_stats_added_by_listarr_calculation(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test that added_by_listarr is calculated from completed jobs."""
        mock_status.return_value = {"version": "4.5.2.7388"}
        mock_count.return_value = 150
        mock_missing.return_value = 12

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)

            # Create a Radarr list
            radarr_list = List(
                name="Test Movies",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(radarr_list)
            db.session.flush()

            # Create completed jobs with items_added
            job1 = Job(
                list_id=radarr_list.id,
                status="completed",
                items_found=50,
                items_added=45,
                items_skipped=5,
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            )
            job2 = Job(
                list_id=radarr_list.id,
                status="completed",
                items_found=30,
                items_added=25,
                items_skipped=5,
                started_at=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 14, 10, 3, 0, tzinfo=timezone.utc),
            )
            # Failed job should not be counted
            job3 = Job(
                list_id=radarr_list.id,
                status="failed",
                items_found=0,
                items_added=0,
                items_skipped=0,
                started_at=datetime(2024, 1, 13, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 13, 10, 0, 30, tzinfo=timezone.utc),
            )
            db.session.add_all([job1, job2, job3])
            db.session.commit()

            # Refresh cache to calculate stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        # Should sum items_added from completed jobs only (45 + 25 = 70)
        assert data["radarr"]["added_by_listarr"] == 70

    @patch("listarr.services.dashboard_cache.get_sonarr_system_status")
    @patch("listarr.services.dashboard_cache.get_series_count")
    @patch("listarr.services.dashboard_cache.get_missing_episodes_count")
    def test_dashboard_stats_added_by_listarr_sonarr_calculation(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test that added_by_listarr is calculated for Sonarr from completed jobs."""
        mock_status.return_value = {"version": "3.0.10.1567"}
        mock_count.return_value = 85
        mock_missing.return_value = 7

        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)

            # Create a Sonarr list
            sonarr_list = List(
                name="Test TV Shows",
                target_service="SONARR",
                tmdb_list_type="popular_tv",
                filters_json={},
            )
            db.session.add(sonarr_list)
            db.session.flush()

            # Create completed jobs with items_added
            job1 = Job(
                list_id=sonarr_list.id,
                status="completed",
                items_found=100,
                items_added=95,
                items_skipped=5,
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            )
            job2 = Job(
                list_id=sonarr_list.id,
                status="completed",
                items_found=50,
                items_added=45,
                items_skipped=5,
                started_at=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 14, 10, 3, 0, tzinfo=timezone.utc),
            )
            db.session.add_all([job1, job2])
            db.session.commit()

            # Refresh cache to calculate stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        # Should sum items_added from completed jobs (95 + 45 = 140)
        assert data["sonarr"]["added_by_listarr"] == 140

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_missing_movies_count")
    def test_dashboard_stats_with_radarr_configured_and_online(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test stats endpoint with Radarr configured and reachable."""
        mock_status.return_value = {"version": "4.5.2.7388", "instanceName": "Radarr"}
        mock_count.return_value = 150
        mock_missing.return_value = 12

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "online"
        assert data["radarr"]["version"] == "4.5.2.7388"
        assert data["radarr"]["total_movies"] == 150
        assert data["radarr"]["missing_movies"] == 12
        assert "added_by_listarr" in data["radarr"]
        assert isinstance(data["radarr"]["added_by_listarr"], int)

    @patch("listarr.services.dashboard_cache.get_sonarr_system_status")
    @patch("listarr.services.dashboard_cache.get_series_count")
    @patch("listarr.services.dashboard_cache.get_missing_episodes_count")
    def test_dashboard_stats_with_sonarr_configured_and_online(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test stats endpoint with Sonarr configured and reachable."""
        mock_status.return_value = {"version": "3.0.10.1567", "instanceName": "Sonarr"}
        mock_count.return_value = 85
        mock_missing.return_value = 7

        with app.app_context():
            encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        assert data["sonarr"]["configured"] is True
        assert data["sonarr"]["status"] == "online"
        assert data["sonarr"]["version"] == "3.0.10.1567"
        assert data["sonarr"]["total_series"] == 85
        assert data["sonarr"]["missing_episodes"] == 7
        assert "added_by_listarr" in data["sonarr"]
        assert isinstance(data["sonarr"]["added_by_listarr"], int)

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    def test_dashboard_stats_with_radarr_configured_but_offline(
        self, mock_status, app, client, temp_instance_path
    ):
        """Test stats endpoint when Radarr is configured but unreachable."""
        mock_status.side_effect = Exception("Connection refused")

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "offline"
        assert data["radarr"]["version"] is None
        assert data["radarr"]["total_movies"] == 0
        assert data["radarr"]["missing_movies"] == 0
        assert "added_by_listarr" in data["radarr"]

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    def test_dashboard_stats_when_radarr_returns_empty_status(
        self, mock_status, app, client, temp_instance_path
    ):
        """Test stats endpoint when Radarr returns empty/null status."""
        mock_status.return_value = None

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Empty status should be treated as offline
        assert data["radarr"]["status"] == "offline"
        assert data["radarr"]["version"] is None

    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    def test_dashboard_stats_with_zero_movies(
        self, mock_status, mock_count, app, client, temp_instance_path
    ):
        """Test stats endpoint when Radarr has zero movies."""
        mock_status.return_value = {"version": "4.5.2.7388"}
        mock_count.return_value = 0

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        assert data["radarr"]["status"] == "online"
        assert data["radarr"]["total_movies"] == 0
        assert data["radarr"]["missing_movies"] == 0

    def test_dashboard_stats_with_only_base_url_configured(
        self, app, client, temp_instance_path
    ):
        """Test stats endpoint when service has base_url but no API key."""
        with app.app_context():
            # Use empty string for api_key_encrypted to satisfy NOT NULL constraint
            config = ServiceConfig(
                service="RADARR", base_url="http://localhost:7878", api_key_encrypted=""
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Should be treated as not configured (empty API key)
        assert data["radarr"]["configured"] is False
        assert data["radarr"]["status"] == "not_configured"

    def test_dashboard_stats_with_only_api_key_configured(
        self, app, client, temp_instance_path
    ):
        """Test stats endpoint when service has API key but no base_url."""
        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR", base_url=None, api_key_encrypted=encrypted
            )
            db.session.add(config)
            db.session.commit()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Should be treated as not configured (needs both)
        assert data["radarr"]["configured"] is False
        assert data["radarr"]["status"] == "not_configured"

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_sonarr_system_status")
    def test_dashboard_stats_with_both_services_configured(
        self, mock_sonarr_status, mock_radarr_status, app, client, temp_instance_path
    ):
        """Test stats endpoint with both services configured."""
        mock_radarr_status.return_value = {"version": "4.5.2.7388"}
        mock_sonarr_status.return_value = {"version": "3.0.10.1567"}

        with app.app_context():
            radarr_encrypted = encrypt_data(
                "radarr_key", instance_path=temp_instance_path
            )
            radarr_config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=radarr_encrypted,
            )
            sonarr_encrypted = encrypt_data(
                "sonarr_key", instance_path=temp_instance_path
            )
            sonarr_config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=sonarr_encrypted,
            )
            db.session.add(radarr_config)
            db.session.add(sonarr_config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Both should be configured and online
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "online"
        assert data["sonarr"]["configured"] is True
        assert data["sonarr"]["status"] == "online"

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_sonarr_system_status")
    def test_dashboard_stats_with_one_service_online_one_offline(
        self, mock_sonarr_status, mock_radarr_status, app, client, temp_instance_path
    ):
        """Test stats endpoint with mixed service statuses."""
        mock_radarr_status.return_value = {"version": "4.5.2.7388"}
        mock_sonarr_status.side_effect = Exception("Connection refused")

        with app.app_context():
            radarr_encrypted = encrypt_data(
                "radarr_key", instance_path=temp_instance_path
            )
            radarr_config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=radarr_encrypted,
            )
            sonarr_encrypted = encrypt_data(
                "sonarr_key", instance_path=temp_instance_path
            )
            sonarr_config = ServiceConfig(
                service="SONARR",
                base_url="http://localhost:8989",
                api_key_encrypted=sonarr_encrypted,
            )
            db.session.add(radarr_config)
            db.session.add(sonarr_config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Radarr should be online, Sonarr offline
        assert data["radarr"]["status"] == "online"
        assert data["sonarr"]["status"] == "offline"


class TestRecentJobsGET:
    """Tests for GET /api/dashboard/recent-jobs endpoint."""

    def test_recent_jobs_with_empty_database(self, client):
        """Test recent jobs endpoint with no jobs."""
        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()
        assert "jobs" in data
        assert len(data["jobs"]) == 0

    def test_recent_jobs_with_single_completed_job(self, app, client):
        """Test recent jobs endpoint with one completed job."""
        with app.app_context():
            # Create list
            test_list = List(
                name="Trending Movies",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            # Create job
            job = Job(
                list_id=test_list.id,
                status="completed",
                items_found=50,
                items_added=45,
                items_skipped=5,
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_name"] == "Trending Movies"
        assert data["jobs"][0]["service"] == "RADARR"
        assert data["jobs"][0]["status"] == "completed"
        assert "45 added" in data["jobs"][0]["summary"]
        assert "5 skipped" in data["jobs"][0]["summary"]
        assert data["jobs"][0]["executed_at"] is not None

    def test_recent_jobs_with_failed_job(self, app, client):
        """Test recent jobs endpoint with failed job."""
        with app.app_context():
            # Create list
            test_list = List(
                name="Popular TV Shows",
                target_service="SONARR",
                tmdb_list_type="popular_tv",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            # Create failed job
            job = Job(
                list_id=test_list.id,
                status="failed",
                items_found=0,
                items_added=0,
                items_skipped=0,
                error_message="Connection to Sonarr failed: timeout after 30 seconds",
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 0, 30, tzinfo=timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "failed"
        assert "Connection to Sonarr failed" in data["jobs"][0]["summary"]

    def test_recent_jobs_orders_by_completed_at_desc(self, app, client):
        """Test that recent jobs are ordered by completed_at descending."""
        with app.app_context():
            # Create list
            test_list = List(
                name="Test List",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            # Create jobs with different finished times
            job1 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=10,
                items_added=10,
                items_skipped=0,
                started_at=datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 10, 10, 5, 0, tzinfo=timezone.utc),
            )
            job2 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=20,
                items_added=20,
                items_skipped=0,
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            )
            job3 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=30,
                items_added=30,
                items_skipped=0,
                started_at=datetime(2024, 1, 12, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 12, 10, 5, 0, tzinfo=timezone.utc),
            )
            db.session.add_all([job1, job2, job3])
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        # Should be ordered by completed_at desc (newest first)
        assert len(data["jobs"]) == 3
        assert "20 added" in data["jobs"][0]["summary"]  # job2 (Jan 15)
        assert "30 added" in data["jobs"][1]["summary"]  # job3 (Jan 12)
        assert "10 added" in data["jobs"][2]["summary"]  # job1 (Jan 10)

    def test_recent_jobs_limits_to_five_jobs(self, app, client):
        """Test that recent jobs endpoint limits to 5 jobs."""
        with app.app_context():
            # Create list
            test_list = List(
                name="Test List",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            # Create 10 jobs
            for i in range(10):
                job = Job(
                    list_id=test_list.id,
                    status="completed",
                    items_found=i + 1,
                    items_added=i + 1,
                    items_skipped=0,
                    started_at=datetime(2024, 1, i + 1, 10, 0, 0, tzinfo=timezone.utc),
                    completed_at=datetime(
                        2024, 1, i + 1, 10, 5, 0, tzinfo=timezone.utc
                    ),
                )
                db.session.add(job)
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        # Should only return 5 most recent
        assert len(data["jobs"]) == 5

    def test_recent_jobs_with_job_without_list_id(self, app, client):
        """Test recent jobs handles jobs without associated list."""
        with app.app_context():
            # Create job without list_id
            job = Job(
                list_id=None,
                status="completed",
                items_found=10,
                items_added=10,
                items_skipped=0,
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["jobs"]) == 1
        # Should use fallback name
        assert data["jobs"][0]["job_name"] == f"Job #{job_id}"
        assert data["jobs"][0]["service"] == "Unknown"

    def test_recent_jobs_with_deleted_list(self, app, client):
        """Test recent jobs handles jobs whose list was deleted."""
        with app.app_context():
            # Create list and job, then delete list
            test_list = List(
                name="Deleted List",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()
            list_id = test_list.id

            job = Job(
                list_id=list_id,
                status="completed",
                items_found=10,
                items_added=10,
                items_skipped=0,
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Delete the list
            db.session.delete(test_list)
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["jobs"]) == 1
        # Should use fallback name when list is missing
        assert data["jobs"][0]["job_name"] == f"Job #{job_id}"

    def test_recent_jobs_only_includes_finished_jobs(self, app, client):
        """Test that recent jobs only includes jobs with completed_at timestamp."""
        with app.app_context():
            # Create list
            test_list = List(
                name="Test List",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            # Create finished job
            finished_job = Job(
                list_id=test_list.id,
                status="completed",
                items_found=10,
                items_added=10,
                items_skipped=0,
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            )

            # Create running job (no completed_at)
            running_job = Job(
                list_id=test_list.id,
                status="running",
                items_found=0,
                items_added=0,
                items_skipped=0,
                started_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                completed_at=None,
            )

            db.session.add_all([finished_job, running_job])
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        # Should only return finished job
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "completed"

    def test_recent_jobs_summary_formatting(self, app, client):
        """Test that job summaries are formatted correctly."""
        with app.app_context():
            # Create list
            test_list = List(
                name="Test List",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            # Create job with only added items
            job1 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=10,
                items_added=10,
                items_skipped=0,
                completed_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            )

            # Create job with both added and skipped
            job2 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=20,
                items_added=15,
                items_skipped=5,
                completed_at=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
            )

            # Create job with only skipped
            job3 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=5,
                items_added=0,
                items_skipped=5,
                completed_at=datetime(2024, 1, 13, 10, 0, 0, tzinfo=timezone.utc),
            )

            # Create job with nothing processed
            job4 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=0,
                items_added=0,
                items_skipped=0,
                completed_at=datetime(2024, 1, 12, 10, 0, 0, tzinfo=timezone.utc),
            )

            db.session.add_all([job1, job2, job3, job4])
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["jobs"]) == 4

        # Job with only added
        assert data["jobs"][0]["summary"] == "10 added"

        # Job with both
        assert "15 added" in data["jobs"][1]["summary"]
        assert "5 skipped" in data["jobs"][1]["summary"]

        # Job with only skipped
        assert data["jobs"][2]["summary"] == "5 skipped"

        # Job with nothing
        assert data["jobs"][3]["summary"] == "No items processed"


class TestDashboardErrorHandling:
    """Tests for error handling and edge cases."""

    @patch("listarr.services.dashboard_cache.decrypt_data")
    def test_dashboard_stats_handles_decryption_error(
        self, mock_decrypt, app, client, temp_instance_path
    ):
        """Test that stats endpoint handles decryption errors gracefully."""
        mock_decrypt.side_effect = ValueError("Decryption failed")

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        # Should not crash
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200

        data = response.get_json()
        # Should show as offline due to error
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "offline"

    def test_recent_jobs_handles_database_error(self, app, client):
        """Test that recent jobs endpoint handles database errors gracefully."""
        with app.app_context():
            with patch("listarr.routes.dashboard_routes.Job.query") as mock_query:
                mock_query.outerjoin.side_effect = Exception("Database connection lost")

                response = client.get("/api/dashboard/recent-jobs")

                # Should return 200 with empty jobs array (graceful error handling)
                assert response.status_code == 200
                data = response.get_json()
                assert data["jobs"] == []

    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    def test_dashboard_stats_handles_partial_api_failure(
        self, mock_status, mock_count, app, client, temp_instance_path
    ):
        """Test stats endpoint handles partial API failures."""
        mock_status.return_value = {"version": "4.5.2.7388"}
        mock_count.side_effect = Exception("Count endpoint failed")

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Status succeeded, so should be online
        assert data["radarr"]["status"] == "online"
        assert data["radarr"]["version"] == "4.5.2.7388"
        # But count failed, so should be 0
        assert data["radarr"]["total_movies"] == 0

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    def test_dashboard_stats_handles_timeout(
        self, mock_status, app, client, temp_instance_path
    ):
        """Test stats endpoint handles timeout errors."""
        mock_status.side_effect = TimeoutError("Request timed out")

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to get updated stats
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Should show as offline
        assert data["radarr"]["status"] == "offline"


class TestDashboardDataFormats:
    """Tests for data format and structure."""

    def test_dashboard_stats_includes_added_by_listarr_field(self, client):
        """Test that stats response includes added_by_listarr field."""
        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Verify added_by_listarr field exists for both services
        assert "added_by_listarr" in data["radarr"]
        assert "added_by_listarr" in data["sonarr"]
        assert isinstance(data["radarr"]["added_by_listarr"], int)
        assert isinstance(data["sonarr"]["added_by_listarr"], int)

    def test_recent_jobs_executed_at_is_iso_format(self, app, client):
        """Test that executed_at timestamp is in ISO format."""
        with app.app_context():
            test_list = List(
                name="Test List",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            job = Job(
                list_id=test_list.id,
                status="completed",
                items_found=10,
                items_added=10,
                items_skipped=0,
                completed_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        executed_at = data["jobs"][0]["executed_at"]
        # Verify ISO format
        assert "T" in executed_at
        assert executed_at.endswith("Z") or "+" in executed_at

    def test_dashboard_stats_response_structure(self, client):
        """Test that stats response has expected structure."""
        response = client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.get_json()

        # Verify root keys
        assert "radarr" in data
        assert "sonarr" in data

        # Verify Radarr structure
        assert "configured" in data["radarr"]
        assert "status" in data["radarr"]
        assert "version" in data["radarr"]
        assert "total_movies" in data["radarr"]
        assert "missing_movies" in data["radarr"]
        assert "added_by_listarr" in data["radarr"]

        # Verify Sonarr structure
        assert "configured" in data["sonarr"]
        assert "status" in data["sonarr"]
        assert "version" in data["sonarr"]
        assert "total_series" in data["sonarr"]
        assert "missing_episodes" in data["sonarr"]
        assert "added_by_listarr" in data["sonarr"]

    def test_recent_jobs_response_structure(self, app, client):
        """Test that recent jobs response has expected structure."""
        with app.app_context():
            test_list = List(
                name="Test List",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            job = Job(
                list_id=test_list.id,
                status="completed",
                items_found=10,
                items_added=10,
                items_skipped=0,
                completed_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")

        assert response.status_code == 200
        data = response.get_json()

        # Verify root structure
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

        # Verify job structure
        job_data = data["jobs"][0]
        assert "id" in job_data
        assert "job_name" in job_data
        assert "service" in job_data
        assert "status" in job_data
        assert "executed_at" in job_data
        assert "summary" in job_data
