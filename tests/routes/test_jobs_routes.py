"""Tests for jobs routes."""

from datetime import datetime, timezone

import pytest


class TestGetJobs:
    """Tests for GET /api/jobs endpoint."""

    def test_returns_empty_list_when_no_jobs(self, client, app):
        """Returns empty list when no jobs exist."""
        response = client.get('/api/jobs')
        assert response.status_code == 200
        data = response.get_json()
        assert data['jobs'] == []
        assert data['total'] == 0

    def test_returns_paginated_jobs(self, client, app):
        """Returns paginated job list."""
        from listarr import db
        from listarr.models.jobs_model import Job

        with app.app_context():
            for i in range(30):
                job = Job(
                    list_id=1,
                    list_name=f'Test List {i}',
                    status='completed',
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.get('/api/jobs?page=1&per_page=10')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['jobs']) == 10
        assert data['total'] == 30
        assert data['pages'] == 3

    def test_filters_by_status(self, client, app):
        """Filters jobs by status."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            for status in ['completed', 'completed', 'failed']:
                job = Job(
                    list_id=1,
                    list_name='Test',
                    status=status,
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.get('/api/jobs?status=failed')
        data = response.get_json()
        assert data['total'] == 1
        assert data['jobs'][0]['status'] == 'failed'

    def test_filters_by_list_id(self, client, app):
        """Filters jobs by list_id."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            for list_id in [1, 1, 2]:
                job = Job(
                    list_id=list_id,
                    list_name=f'List {list_id}',
                    status='completed',
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.get('/api/jobs?list_id=1')
        data = response.get_json()
        assert data['total'] == 2

    def test_enforces_max_per_page(self, client, app):
        """Enforces max 50 per_page limit."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            for i in range(60):
                job = Job(
                    list_id=1,
                    list_name='Test',
                    status='completed',
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.get('/api/jobs?per_page=100')
        data = response.get_json()
        # Should be capped at 50
        assert len(data['jobs']) == 50


class TestGetRecentJobs:
    """Tests for GET /api/jobs/recent endpoint."""

    def test_returns_max_5_jobs(self, client, app):
        """Returns at most 5 recent jobs."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            for i in range(10):
                job = Job(
                    list_id=1,
                    list_name='Test',
                    status='completed',
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.get('/api/jobs/recent')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['jobs']) == 5

    def test_returns_empty_list_when_no_jobs(self, client):
        """Returns empty list when no jobs exist."""
        response = client.get('/api/jobs/recent')
        assert response.status_code == 200
        data = response.get_json()
        assert data['jobs'] == []

    def test_includes_target_service(self, client, app):
        """Includes target_service from related list."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
        from listarr.models.lists_model import List
=======
        from listarr.models.jobs_model import Job
        from listarr.models.lists_model import List
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            list_obj = List(
                name='Test List',
                target_service='radarr',
                tmdb_list_type='trending_movies',
                filters_json={},
                is_active=True
            )
            db.session.add(list_obj)
            db.session.commit()
            list_id = list_obj.id

            job = Job(
                list_id=list_id,
                list_name='Test List',
                status='completed',
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(job)
            db.session.commit()

        response = client.get('/api/jobs/recent')
        data = response.get_json()
        assert len(data['jobs']) == 1
        assert data['jobs'][0]['target_service'] == 'radarr'


class TestGetJobDetail:
    """Tests for GET /api/jobs/<id> endpoint."""

    def test_returns_404_for_missing_job(self, client):
        """Returns 404 when job doesn't exist."""
        response = client.get('/api/jobs/999')
        assert response.status_code == 404

    def test_returns_job_with_items(self, client, app):
        """Returns job detail with items."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job, JobItem
=======
        from listarr.models.jobs_model import Job, JobItem
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            job = Job(
                list_id=1,
                list_name='Test',
                status='completed',
                started_at=datetime.now(timezone.utc),
                items_added=2
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            for i in range(2):
                item = JobItem(
                    job_id=job_id,
                    tmdb_id=100 + i,
                    title=f'Movie {i}',
                    status='added'
                )
                db.session.add(item)
            db.session.commit()

        response = client.get(f'/api/jobs/{job_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['list_name'] == 'Test'
        assert len(data['items']) == 2

    def test_returns_job_without_items(self, client, app):
        """Returns job even when no items exist."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            job = Job(
                list_id=1,
                list_name='Test',
                status='completed',
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = client.get(f'/api/jobs/{job_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['items'] == []


class TestRerunJob:
    """Tests for POST /api/jobs/<id>/rerun endpoint."""

    def test_returns_404_for_missing_job(self, client):
        """Returns 404 when job doesn't exist."""
        response = client.post('/api/jobs/999/rerun')
        assert response.status_code == 404

    def test_rejects_non_failed_job(self, client, app):
        """Cannot rerun completed jobs."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            job = Job(
                list_id=1,
                list_name='Test',
                status='completed',
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = client.post(f'/api/jobs/{job_id}/rerun')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'only rerun failed jobs' in data['error'].lower()

    def test_rejects_when_list_deleted(self, client, app):
        """Cannot rerun when list no longer exists."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            job = Job(
                list_id=9999,  # Non-existent list
                list_name='Deleted List',
                status='failed',
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = client.post(f'/api/jobs/{job_id}/rerun')
        assert response.status_code == 400
        data = response.get_json()
        assert 'no longer exists' in data['error'].lower()

    def test_rejects_inactive_list(self, client, app):
        """Cannot rerun when list is inactive."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
        from listarr.models.lists_model import List
=======
        from listarr.models.jobs_model import Job
        from listarr.models.lists_model import List
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            list_obj = List(
                name='Test List',
                target_service='radarr',
                tmdb_list_type='trending_movies',
                filters_json={},
                is_active=False
            )
            db.session.add(list_obj)
            db.session.commit()
            list_id = list_obj.id

            job = Job(
                list_id=list_id,
                list_name='Test List',
                status='failed',
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = client.post(f'/api/jobs/{job_id}/rerun')
        assert response.status_code == 400
        data = response.get_json()
        assert 'not active' in data['error'].lower()


class TestClearJobs:
    """Tests for clear endpoints."""

    def test_clear_all_jobs(self, client, app):
        """Clears all non-running jobs."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            for status in ['completed', 'failed', 'running']:
                job = Job(
                    list_id=1,
                    list_name='Test',
                    status=status,
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.post('/api/jobs/clear')
        assert response.status_code == 200
        data = response.get_json()
        assert data['deleted_count'] == 2  # completed + failed, not running

        # Verify running job still exists
        with app.app_context():
            remaining = Job.query.all()
            assert len(remaining) == 1
            assert remaining[0].status == 'running'

    def test_clear_list_jobs(self, client, app):
        """Clears jobs for specific list."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            for list_id in [1, 1, 2]:
                job = Job(
                    list_id=list_id,
                    list_name=f'List {list_id}',
                    status='completed',
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.post('/api/jobs/clear/1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['deleted_count'] == 2

        # Verify list 2 job still exists
        with app.app_context():
            remaining = Job.query.all()
            assert len(remaining) == 1
            assert remaining[0].list_id == 2

    def test_clear_list_jobs_preserves_running(self, client, app):
        """Clear per-list preserves running jobs."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            for status in ['completed', 'running']:
                job = Job(
                    list_id=1,
                    list_name='Test',
                    status=status,
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.post('/api/jobs/clear/1')
        data = response.get_json()
        assert data['deleted_count'] == 1

        with app.app_context():
            remaining = Job.query.all()
            assert len(remaining) == 1
            assert remaining[0].status == 'running'


class TestGetRunningJobs:
    """Tests for GET /api/jobs/running endpoint."""

    def test_returns_empty_when_no_running_jobs(self, client):
        """Returns empty list when no running jobs."""
        response = client.get('/api/jobs/running')
        assert response.status_code == 200
        data = response.get_json()
        assert data['running_jobs'] == []

    def test_returns_running_jobs(self, client, app):
        """Returns list of running jobs."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            for status in ['running', 'completed', 'running']:
                job = Job(
                    list_id=1,
                    list_name='Test',
                    status=status,
                    started_at=datetime.now(timezone.utc)
                )
                db.session.add(job)
            db.session.commit()

        response = client.get('/api/jobs/running')
        data = response.get_json()
        assert len(data['running_jobs']) == 2

    def test_includes_job_metadata(self, client, app):
        """Running jobs include job_id, list_id, list_name."""
<<<<<<< HEAD
        from listarr import db
        from listarr.models.jobs_model import Job
=======
        from listarr.models.jobs_model import Job
        from listarr import db
>>>>>>> origin/develop

        with app.app_context():
            job = Job(
                list_id=5,
                list_name='My Test List',
                status='running',
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = client.get('/api/jobs/running')
        data = response.get_json()
        assert len(data['running_jobs']) == 1
        assert data['running_jobs'][0]['job_id'] == job_id
        assert data['running_jobs'][0]['list_id'] == 5
        assert data['running_jobs'][0]['list_name'] == 'My Test List'


class TestJobsPage:
    """Tests for GET /jobs page."""

    def test_jobs_page_renders(self, client):
        """Jobs page renders successfully."""
        response = client.get('/jobs')
        assert response.status_code == 200
