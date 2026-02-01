"""
Tests for job executor service.

Tests cover:
- is_list_running() function - database check for running jobs
- get_job_status() function - retrieve most recent job status
- submit_job() function - job submission with duplicate rejection
- get_executor() function - ThreadPoolExecutor lazy initialization
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from listarr.services.job_executor import (
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
