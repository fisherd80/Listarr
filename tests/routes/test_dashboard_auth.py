"""
Authentication tests for dashboard routes.

Tests verify that @login_required decorators are properly applied to dashboard endpoints.
"""

import pytest


class TestDashboardAuthenticationRequired:
    """Tests for authentication requirements on dashboard endpoints."""

    def test_dashboard_page_requires_authentication(self, app_with_auth):
        """Dashboard page redirects to login when not authenticated."""
        # Create user first so redirect goes to /login not /setup
        with app_with_auth.app_context():
            from listarr import db
            from listarr.models.user_model import User

            user = User(username="testuser")
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()

        # Create client without logging in
        with app_with_auth.test_client() as client:
            response = client.get("/", follow_redirects=False)
            assert response.status_code == 302
            assert "/login" in response.location

    def test_dashboard_stats_requires_authentication(self, app_with_auth):
        """Dashboard stats API redirects to login when not authenticated."""
        # Create user first
        with app_with_auth.app_context():
            from listarr import db
            from listarr.models.user_model import User

            user = User(username="testuser")
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()

        with app_with_auth.test_client() as client:
            response = client.get("/api/dashboard/stats")
            # Flask-Login redirects unauthenticated requests (302)
            assert response.status_code == 302
            assert "/login" in response.location

    def test_dashboard_recent_jobs_requires_authentication(self, app_with_auth):
        """Dashboard recent jobs API redirects to login when not authenticated."""
        # Create user first
        with app_with_auth.app_context():
            from listarr import db
            from listarr.models.user_model import User

            user = User(username="testuser")
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()

        with app_with_auth.test_client() as client:
            response = client.get("/api/dashboard/recent-jobs")
            # Flask-Login redirects unauthenticated requests (302)
            assert response.status_code == 302
            assert "/login" in response.location

    def test_dashboard_upcoming_requires_authentication(self, app_with_auth):
        """Dashboard upcoming API redirects to login when not authenticated."""
        # Create user first
        with app_with_auth.app_context():
            from listarr import db
            from listarr.models.user_model import User

            user = User(username="testuser")
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()

        with app_with_auth.test_client() as client:
            response = client.get("/api/dashboard/upcoming")
            # Flask-Login redirects unauthenticated requests (302)
            assert response.status_code == 302
            assert "/login" in response.location
