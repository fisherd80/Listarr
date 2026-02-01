"""
Integration tests for Dashboard functionality.

Tests cover:
- Full end-to-end workflows for dashboard data aggregation
- Database operations with ServiceConfig
- Radarr/Sonarr API integration with real mocking
- Error recovery and graceful degradation
- Multi-service data aggregation
- Stats calculation and formatting
- Recent jobs display
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from listarr import db
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.services.crypto_utils import encrypt_data


class TestDashboardEndToEndWorkflow:
    """Integration tests for complete dashboard workflows."""

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_missing_movies_count")
    def test_full_dashboard_load_with_radarr_only(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test complete workflow: configure Radarr → load dashboard → verify stats."""
        mock_status.return_value = {"version": "4.5.2.7388", "instanceName": "Radarr"}
        mock_count.return_value = 150
        mock_missing.return_value = 12

        # Step 1: Configure Radarr
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

        # Step 2: Load dashboard page
        response = client.get("/")
        assert response.status_code == 200
        assert b"Dashboard" in response.data
        assert b"Radarr" in response.data

        # Step 3: Fetch dashboard stats
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        # Verify Radarr stats
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "online"
        assert data["radarr"]["version"] == "4.5.2.7388"
        assert data["radarr"]["total_movies"] == 150
        assert data["radarr"]["missing_movies"] == 12
        assert "added_by_listarr" in data["radarr"]

        # Verify Sonarr is not configured
        assert data["sonarr"]["configured"] is False
        assert data["sonarr"]["status"] == "not_configured"

    @patch("listarr.services.dashboard_cache.get_sonarr_system_status")
    @patch("listarr.services.dashboard_cache.get_series_count")
    @patch("listarr.services.dashboard_cache.get_missing_episodes_count")
    def test_full_dashboard_load_with_sonarr_only(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test complete workflow: configure Sonarr → load dashboard → verify stats."""
        mock_status.return_value = {"version": "3.0.10.1567", "instanceName": "Sonarr"}
        mock_count.return_value = 85
        mock_missing.return_value = 7

        # Step 1: Configure Sonarr
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

        # Step 2: Load dashboard page
        response = client.get("/")
        assert response.status_code == 200
        assert b"Dashboard" in response.data
        assert b"Sonarr" in response.data

        # Step 3: Fetch dashboard stats
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        # Verify Sonarr stats
        assert data["sonarr"]["configured"] is True
        assert data["sonarr"]["status"] == "online"
        assert data["sonarr"]["version"] == "3.0.10.1567"
        assert data["sonarr"]["total_series"] == 85
        assert data["sonarr"]["missing_episodes"] == 7
        assert "added_by_listarr" in data["sonarr"]

        # Verify Radarr is not configured
        assert data["radarr"]["configured"] is False
        assert data["radarr"]["status"] == "not_configured"

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_missing_movies_count")
    @patch("listarr.services.dashboard_cache.get_sonarr_system_status")
    @patch("listarr.services.dashboard_cache.get_series_count")
    @patch("listarr.services.dashboard_cache.get_missing_episodes_count")
    def test_full_dashboard_load_with_both_services(
        self,
        mock_sonarr_missing,
        mock_sonarr_count,
        mock_sonarr_status,
        mock_radarr_missing,
        mock_radarr_count,
        mock_radarr_status,
        app,
        client,
        temp_instance_path,
    ):
        """Test complete workflow: configure both services → load dashboard → verify all stats."""
        # Mock Radarr
        mock_radarr_status.return_value = {
            "version": "4.5.2.7388",
            "instanceName": "Radarr",
        }
        mock_radarr_count.return_value = 150
        mock_radarr_missing.return_value = 12

        # Mock Sonarr
        mock_sonarr_status.return_value = {
            "version": "3.0.10.1567",
            "instanceName": "Sonarr",
        }
        mock_sonarr_count.return_value = 85
        mock_sonarr_missing.return_value = 7

        # Step 1: Configure both services
        with app.app_context():
            radarr_encrypted = encrypt_data(
                "radarr_key", instance_path=temp_instance_path
            )
            radarr_config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=radarr_encrypted,
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

        # Step 2: Fetch dashboard stats
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        # Verify both services are configured and online
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "online"
        assert data["radarr"]["total_movies"] == 150
        assert data["radarr"]["missing_movies"] == 12
        assert "added_by_listarr" in data["radarr"]

        assert data["sonarr"]["configured"] is True
        assert data["sonarr"]["status"] == "online"
        assert data["sonarr"]["total_series"] == 85
        assert data["sonarr"]["missing_episodes"] == 7
        assert "added_by_listarr" in data["sonarr"]

    def test_dashboard_load_with_no_services_configured(self, client):
        """Test dashboard loads successfully when no services are configured."""
        # Step 1: Load dashboard page
        response = client.get("/")
        assert response.status_code == 200
        assert b"Dashboard" in response.data

        # Step 2: Fetch dashboard stats
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        # Verify both services show as not configured
        assert data["radarr"]["configured"] is False
        assert data["radarr"]["status"] == "not_configured"
        assert data["radarr"]["total_movies"] == 0
        assert data["radarr"]["missing_movies"] == 0

        assert data["sonarr"]["configured"] is False
        assert data["sonarr"]["status"] == "not_configured"
        assert data["sonarr"]["total_series"] == 0
        assert data["sonarr"]["missing_episodes"] == 0

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_missing_movies_count")
    def test_radarr_offline_shows_offline_status(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test that offline Radarr service shows 'offline' status."""
        # Mock service as unreachable
        mock_status.side_effect = Exception("Connection refused")
        mock_count.side_effect = Exception("Connection refused")
        mock_missing.side_effect = Exception("Connection refused")

        # Configure Radarr
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

        # Fetch dashboard stats
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        # Verify Radarr shows as offline
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "offline"
        assert data["radarr"]["total_movies"] == 0
        assert data["radarr"]["missing_movies"] == 0
        assert data["radarr"]["version"] is None
        assert "added_by_listarr" in data["radarr"]


class TestRecentJobsWorkflow:
    """Integration tests for recent jobs display."""

    def test_recent_jobs_with_no_jobs(self, client):
        """Test recent jobs endpoint with no jobs in database."""
        response = client.get("/api/dashboard/recent-jobs")
        assert response.status_code == 200
        data = response.get_json()
        assert "jobs" in data
        assert len(data["jobs"]) == 0

    def test_recent_jobs_with_completed_jobs(self, app, client):
        """Test recent jobs displays completed jobs."""
        with app.app_context():
            # Create a list
            test_list = List(
                name="Test Movie List",
                target_service="RADARR",
                tmdb_list_type="trending_movies",
                filters_json={},
            )
            db.session.add(test_list)
            db.session.commit()

            # Create completed jobs
            job1 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=50,
                items_added=45,
                items_skipped=5,
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            )
            job2 = Job(
                list_id=test_list.id,
                status="completed",
                items_found=30,
                items_added=28,
                items_skipped=2,
                started_at=datetime(2024, 1, 14, 9, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 14, 9, 3, 0, tzinfo=timezone.utc),
            )
            db.session.add(job1)
            db.session.add(job2)
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        assert response.status_code == 200
        data = response.get_json()

        assert len(data["jobs"]) == 2
        # Jobs should be ordered by completed_at desc (newest first)
        assert data["jobs"][0]["job_name"] == "Test Movie List"
        assert data["jobs"][0]["service"] == "RADARR"
        assert data["jobs"][0]["status"] == "completed"
        assert "45 added" in data["jobs"][0]["summary"]
        assert "5 skipped" in data["jobs"][0]["summary"]

    def test_recent_jobs_with_failed_jobs(self, app, client):
        """Test recent jobs displays failed jobs with error messages."""
        with app.app_context():
            # Create a list
            test_list = List(
                name="Test TV List",
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
                error_message="Connection to Sonarr failed: timeout",
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

    def test_recent_jobs_limit_to_five(self, app, client):
        """Test that recent jobs endpoint only returns last 5 jobs."""
        with app.app_context():
            # Create a list
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
                    items_found=10,
                    items_added=10,
                    items_skipped=0,
                    started_at=datetime(2024, 1, i + 1, 10, 0, 0, tzinfo=timezone.utc),
                    completed_at=datetime(2024, 1, i + 1, 10, 5, 0, tzinfo=timezone.utc),
                )
                db.session.add(job)
            db.session.commit()

        response = client.get("/api/dashboard/recent-jobs")
        assert response.status_code == 200
        data = response.get_json()

        # Should only return 5 most recent jobs
        assert len(data["jobs"]) == 5

    def test_recent_jobs_with_no_list_association(self, app, client):
        """Test recent jobs handles jobs without associated lists."""
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
        # Should show fallback job name
        assert data["jobs"][0]["job_name"] == f"Job #{job_id}"
        assert data["jobs"][0]["service"] == "Unknown"


class TestDashboardErrorRecovery:
    """Integration tests for error recovery scenarios."""

    @patch("listarr.services.dashboard_cache.decrypt_data")
    def test_dashboard_handles_decryption_error(self, mock_decrypt, app, client, temp_instance_path):
        """Test that dashboard handles decryption errors gracefully."""
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

        # Dashboard page should still load
        response = client.get("/")
        assert response.status_code == 200

        # Stats endpoint should handle error gracefully
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()

        # Should show Radarr as configured but offline due to decryption error
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "offline"

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    def test_dashboard_handles_api_timeout(self, mock_status, app, client, temp_instance_path):
        """Test that dashboard handles API timeouts gracefully."""
        mock_status.side_effect = TimeoutError("Request timeout")

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

        # Should show as offline due to timeout
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "offline"

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_movie_count")
    def test_dashboard_handles_partial_api_failure(self, mock_count, mock_status, app, client, temp_instance_path):
        """Test dashboard handles partial API failures (status succeeds, count fails)."""
        mock_status.return_value = {"version": "4.5.2.7388"}
        mock_count.side_effect = Exception("Count API failed")

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

        # Should show as online (status succeeded)
        assert data["radarr"]["status"] == "online"
        assert data["radarr"]["version"] == "4.5.2.7388"
        # But counts should be 0 due to failure
        assert data["radarr"]["total_movies"] == 0

    def test_dashboard_handles_database_error_for_jobs(self, app, client):
        """Test that recent jobs endpoint handles database errors gracefully."""
        with app.app_context():
            with patch("listarr.routes.dashboard_routes.Job.query") as mock_query:
                mock_query.outerjoin.side_effect = Exception("Database error")

                response = client.get("/api/dashboard/recent-jobs")
                # Should return 200 with empty jobs array (graceful error handling)
                assert response.status_code == 200
                data = response.get_json()
                assert data["jobs"] == []


class TestMultipleRequestsScenarios:
    """Integration tests for scenarios with multiple dashboard requests."""

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_missing_movies_count")
    def test_rapid_succession_dashboard_requests(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test handling of rapid succession dashboard stats requests."""
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
            db.session.commit()

            # Refresh cache once to populate it
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        # Simulate rapid requests (should use cache, not refresh each time)
        for _ in range(5):
            response = client.get("/api/dashboard/stats")
            assert response.status_code == 200
            data = response.get_json()
            assert data["radarr"]["total_movies"] == 150

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    def test_interleaved_dashboard_and_jobs_requests(self, mock_status, app, client, temp_instance_path):
        """Test handling of interleaved dashboard and jobs requests."""
        mock_status.return_value = {"version": "4.5.2.7388"}

        with app.app_context():
            encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
            config = ServiceConfig(
                service="RADARR",
                base_url="http://localhost:7878",
                api_key_encrypted=encrypted,
            )
            db.session.add(config)
            db.session.commit()

            # Refresh cache to populate it
            from listarr.services.dashboard_cache import refresh_dashboard_cache

            refresh_dashboard_cache()

        # Interleave requests
        response1 = client.get("/api/dashboard/stats")
        assert response1.status_code == 200

        response2 = client.get("/api/dashboard/recent-jobs")
        assert response2.status_code == 200

        response3 = client.get("/api/dashboard/stats")
        assert response3.status_code == 200

        response4 = client.get("/api/dashboard/recent-jobs")
        assert response4.status_code == 200

        # All should complete without errors
        assert response1.get_json()["radarr"]["status"] == "online"
        assert "jobs" in response2.get_json()


class TestDashboardCacheRefresh:
    """Integration tests for cache refresh functionality."""

    @patch("listarr.services.dashboard_cache.get_radarr_system_status")
    @patch("listarr.services.dashboard_cache.get_movie_count")
    @patch("listarr.services.dashboard_cache.get_missing_movies_count")
    def test_dashboard_refresh_parameter_triggers_cache_refresh(
        self, mock_missing, mock_count, mock_status, app, client, temp_instance_path
    ):
        """Test that ?refresh=true parameter triggers cache refresh."""
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
            db.session.commit()

        # Request with refresh parameter
        response = client.get("/api/dashboard/stats?refresh=true")
        assert response.status_code == 200
        data = response.get_json()

        # Should return updated stats
        assert data["radarr"]["configured"] is True
        assert data["radarr"]["status"] == "online"
        assert data["radarr"]["total_movies"] == 150
        assert "added_by_listarr" in data["radarr"]

    def test_dashboard_without_refresh_uses_cache(self, client):
        """Test that requests without refresh parameter use cached data."""
        # First request (may trigger initial cache)
        response1 = client.get("/api/dashboard/stats")
        assert response1.status_code == 200

        # Second request should use cache (no refresh)
        response2 = client.get("/api/dashboard/stats")
        assert response2.status_code == 200

        # Both should return valid structure
        data1 = response1.get_json()
        data2 = response2.get_json()

        assert "radarr" in data1
        assert "sonarr" in data1
        assert "radarr" in data2
        assert "sonarr" in data2
