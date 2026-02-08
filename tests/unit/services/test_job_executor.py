"""
Tests for job executor service.

Tests cover:
- is_list_running() function - database check for running jobs
- get_job_status() function - retrieve most recent job status
- submit_job() function - job submission with duplicate rejection
- get_executor() function - ThreadPoolExecutor lazy initialization
"""

import threading
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from listarr.services.job_executor import (
    IDLE_TIMEOUT_SECONDS,
    ActivityTracker,
    _execute_job,
    _monitor_idle,
    get_executor,
    get_job_status,
    is_list_running,
    submit_job,
)


class TestIsListRunning:
    """Tests for is_list_running function."""

    def test_returns_false_when_no_jobs(self, app):
        """No jobs exist for list."""
        with app.app_context():
            result = is_list_running(999)
            assert result is False

    def test_returns_false_when_job_completed(self, app):
        """Job exists but is completed."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with app.app_context():
            job = Job(
                list_id=1,
                list_name="Test",
                status="completed",
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

            result = is_list_running(1)
            assert result is False

    def test_returns_true_when_job_running(self, app):
        """Job exists and is running."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with app.app_context():
            job = Job(
                list_id=2,
                list_name="Test",
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

            result = is_list_running(2)
            assert result is True

    def test_returns_false_when_job_failed(self, app):
        """Failed job should not count as running."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with app.app_context():
            job = Job(
                list_id=3,
                list_name="Test",
                status="failed",
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

            result = is_list_running(3)
            assert result is False


class TestGetJobStatus:
    """Tests for get_job_status function."""

    def test_returns_none_when_no_jobs(self, app):
        """No jobs exist for list."""
        with app.app_context():
            result = get_job_status(999)
            assert result is None

    def test_returns_most_recent_job(self, app):
        """Returns most recent job for list."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with app.app_context():
            # Create older job
            old_job = Job(
                list_id=3,
                list_name="Test",
                status="completed",
                started_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            db.session.add(old_job)
            db.session.commit()

            # Create newer job
            new_job = Job(
                list_id=3,
                list_name="Test",
                status="running",
                started_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
            )
            db.session.add(new_job)
            db.session.commit()

            result = get_job_status(3)
            assert result is not None
            assert result["status"] == "running"

    def test_returns_dict_with_all_fields(self, app):
        """Returns job dict with all expected fields."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with app.app_context():
            job = Job(
                list_id=4,
                list_name="Test List",
                status="completed",
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
                duration=300,
                triggered_by="manual",
                retry_count=0,
                items_found=50,
                items_added=45,
                items_skipped=5,
                items_failed=0,
            )
            db.session.add(job)
            db.session.commit()

            result = get_job_status(4)
            assert result is not None
            assert result["list_id"] == 4
            assert result["list_name"] == "Test List"
            assert result["status"] == "completed"
            assert result["duration"] == 300
            assert result["triggered_by"] == "manual"
            assert result["items_found"] == 50
            assert result["items_added"] == 45
            assert result["items_skipped"] == 5
            assert result["items_failed"] == 0


class TestSubmitJob:
    """Tests for submit_job function."""

    def test_raises_when_already_running(self, app):
        """Raises ValueError when job already running."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with app.app_context():
            # Create running job
            job = Job(
                list_id=4,
                list_name="Test",
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(job)
            db.session.commit()

        with pytest.raises(ValueError, match="already running"):
            submit_job(4, "Test", app)

    def test_creates_job_record(self, app):
        """Creates job record in database."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with patch("listarr.services.job_executor.get_executor") as mock_executor:
            mock_executor.return_value.submit = MagicMock()

            job_id = submit_job(5, "Test List", app, triggered_by="manual")

            with app.app_context():
                job = Job.query.get(job_id)
                assert job is not None
                assert job.list_id == 5
                assert job.list_name == "Test List"
                assert job.status == "running"
                assert job.triggered_by == "manual"

    def test_creates_job_with_scheduled_trigger(self, app):
        """Creates job with scheduled trigger type."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with patch("listarr.services.job_executor.get_executor") as mock_executor:
            mock_executor.return_value.submit = MagicMock()

            job_id = submit_job(6, "Scheduled List", app, triggered_by="scheduled")

            with app.app_context():
                job = Job.query.get(job_id)
                assert job is not None
                assert job.triggered_by == "scheduled"

    def test_submits_to_executor(self, app):
        """Submits job to ThreadPoolExecutor."""
        with patch("listarr.services.job_executor.get_executor") as mock_executor:
            mock_submit = MagicMock()
            mock_executor.return_value.submit = mock_submit

            submit_job(7, "Test List", app)

            # Verify executor.submit was called
            mock_submit.assert_called_once()


class TestGetExecutor:
    """Tests for get_executor function."""

    def test_returns_thread_pool_executor(self):
        """Returns a ThreadPoolExecutor instance."""
        from concurrent.futures import ThreadPoolExecutor

        executor = get_executor()
        assert executor is not None
        assert isinstance(executor, ThreadPoolExecutor)

    def test_returns_same_instance_on_subsequent_calls(self):
        """Returns the same executor instance (singleton pattern)."""
        executor1 = get_executor()
        executor2 = get_executor()
        assert executor1 is executor2


class TestJobLifecycle:
    """Integration tests for job lifecycle management."""

    def test_job_initialized_with_zero_counts(self, app):
        """Job is created with zero item counts."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with patch("listarr.services.job_executor.get_executor") as mock_executor:
            mock_executor.return_value.submit = MagicMock()

            job_id = submit_job(8, "Test", app)

            with app.app_context():
                job = Job.query.get(job_id)
                assert job.items_found == 0
                assert job.items_added == 0
                assert job.items_skipped == 0
                assert job.items_failed == 0

    def test_job_initialized_with_zero_retry_count(self, app):
        """Job is created with zero retry count."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with patch("listarr.services.job_executor.get_executor") as mock_executor:
            mock_executor.return_value.submit = MagicMock()

            job_id = submit_job(9, "Test", app)

            with app.app_context():
                job = Job.query.get(job_id)
                assert job.retry_count == 0

    def test_job_has_started_at_timestamp(self, app):
        """Job is created with started_at timestamp."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with patch("listarr.services.job_executor.get_executor") as mock_executor:
            mock_executor.return_value.submit = MagicMock()

            job_id = submit_job(10, "Test", app)

            with app.app_context():
                job = Job.query.get(job_id)
                assert job.started_at is not None
                assert isinstance(job.started_at, datetime)


class TestActivityTracker:
    """Tests for ActivityTracker class."""

    def test_initial_idle_seconds_near_zero(self):
        """ActivityTracker initializes with idle_seconds near zero."""
        import time

        tracker = ActivityTracker()
        assert tracker.idle_seconds < 1.0

    def test_update_resets_idle(self):
        """update() resets idle_seconds to near zero."""
        import time

        tracker = ActivityTracker()
        time.sleep(0.1)
        tracker.update()
        assert tracker.idle_seconds < 0.1

    def test_idle_seconds_increases_over_time(self):
        """idle_seconds increases as time passes."""
        import time

        tracker = ActivityTracker()
        time.sleep(0.2)
        assert tracker.idle_seconds >= 0.2

    def test_thread_safe_update(self):
        """ActivityTracker handles concurrent updates safely."""
        import threading

        tracker = ActivityTracker()

        def update_many():
            for _ in range(100):
                tracker.update()

        thread1 = threading.Thread(target=update_many)
        thread2 = threading.Thread(target=update_many)

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # No crash = success
        assert tracker.idle_seconds >= 0


class TestIdleTimeout:
    """Tests for idle timeout monitoring."""

    def test_submit_job_creates_activity_tracker(self, app):
        """submit_job passes ActivityTracker to executor."""
        from unittest.mock import ANY

        with patch("listarr.services.job_executor.get_executor") as mock_executor:
            mock_submit = MagicMock()
            mock_executor.return_value.submit = mock_submit

            submit_job(11, "Test", app)

            # Verify _execute_job was called with ActivityTracker instance
            mock_submit.assert_called_once()
            args = mock_submit.call_args[0]
            # args[0] is the function _execute_job
            # Then come the actual arguments
            assert args[1] == 1  # job_id (auto-incremented in test DB)
            assert args[2] == 11  # list_id
            assert isinstance(args[3], threading.Event)  # stop_event
            assert isinstance(args[4], ActivityTracker)  # activity_tracker
            assert args[5] == app

    def test_monitor_stops_on_monitor_stop_event(self):
        """_monitor_idle exits immediately when monitor_stop is set."""
        import threading
        import time

        tracker = ActivityTracker()
        stop_event = threading.Event()
        monitor_stop = threading.Event()

        # Set monitor_stop immediately
        monitor_stop.set()

        # Call _monitor_idle
        _monitor_idle(999, tracker, monitor_stop)

        # stop_event should NOT be set (no timeout triggered)
        assert not stop_event.is_set()

    def test_idle_job_triggers_timeout(self):
        """_monitor_idle sets stop_event when job is idle."""
        import threading
        import time

        from listarr.services.job_executor import _stop_events, _stop_events_lock

        tracker = ActivityTracker()
        stop_event = threading.Event()
        monitor_stop = threading.Event()

        # Set last_activity to simulate idle timeout
        tracker._last_activity = time.time() - (IDLE_TIMEOUT_SECONDS + 10)

        # Register stop_event
        job_id = 12345
        with _stop_events_lock:
            _stop_events[job_id] = stop_event

        # Call _monitor_idle (should trigger immediately)
        _monitor_idle(job_id, tracker, monitor_stop)

        # stop_event should be set
        assert stop_event.is_set()

        # Cleanup
        with _stop_events_lock:
            _stop_events.pop(job_id, None)


class TestImportStopEvent:
    """Tests for import service stop_event integration."""

    def test_import_movies_checks_stop_event(self, app):
        """_import_movies respects stop_event."""
        import threading

        from listarr.services.import_service import _import_movies

        stop_event = threading.Event()
        stop_event.set()  # Signal stop before import

        settings = {
            "root_folder": "/movies",
            "quality_profile_id": 1,
            "monitored": True,
            "search_on_add": True,
            "tags": [],
        }

        tmdb_items = [{"id": 1, "title": "Test Movie"}]

        result = _import_movies(
            tmdb_items,
            "http://localhost:7878",
            "fake_key",
            settings,
            "tmdb_key",
            stop_event=stop_event,
            activity_tracker=None,
        )

        # Should have stopped immediately (no processing)
        assert result.total == 0

    def test_import_movies_updates_activity_tracker(self, app):
        """_import_movies updates activity_tracker on progress."""
        import threading

        from listarr.services.import_service import _import_movies

        activity_tracker = ActivityTracker()
        stop_event = threading.Event()

        settings = {
            "root_folder": "/movies",
            "quality_profile_id": 1,
            "monitored": True,
            "search_on_add": True,
            "tags": [],
        }

        tmdb_items = [
            {"id": 100, "title": "Movie 1"},
            {"id": 200, "title": "Movie 2"},
        ]

        with patch("listarr.services.radarr_service.get_existing_movie_tmdb_ids") as mock_existing:
            # Return all IDs to skip (triggers activity update)
            mock_existing.return_value = {100, 200}

            result = _import_movies(
                tmdb_items,
                "http://localhost:7878",
                "fake_key",
                settings,
                "tmdb_key",
                stop_event=stop_event,
                activity_tracker=activity_tracker,
            )

        # Should have skipped both items
        assert result.skipped == [
            {"tmdb_id": 100, "title": "Movie 1", "reason": "already_exists"},
            {"tmdb_id": 200, "title": "Movie 2", "reason": "already_exists"},
        ]

        # Activity tracker should show recent activity
        assert activity_tracker.idle_seconds < 1.0

    def test_import_series_checks_stop_event(self, app):
        """_import_series respects stop_event."""
        import threading

        from listarr.services.import_service import _import_series

        stop_event = threading.Event()
        stop_event.set()  # Signal stop before import

        settings = {
            "root_folder": "/tv",
            "quality_profile_id": 1,
            "monitored": True,
            "search_on_add": True,
            "season_folder": True,
            "tags": [],
        }

        tmdb_items = [{"id": 1, "name": "Test Series"}]

        result = _import_series(
            tmdb_items,
            "http://localhost:8989",
            "fake_key",
            settings,
            "tmdb_key",
            stop_event=stop_event,
            activity_tracker=None,
        )

        # Should have stopped immediately (no processing)
        assert result.total == 0
