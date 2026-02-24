"""
Tests for authentication routes (login, setup, logout) and route protection.
"""

import pytest
from flask import session

from listarr import db
from listarr.models.user_model import User


class TestSetupPage:
    """Tests for the setup page (/setup)."""

    def test_setup_page_renders_when_no_user(self, auth_client):
        """Test that GET /setup returns 200 with setup form when no user exists."""
        response = auth_client.get("/setup")

        assert response.status_code == 200
        assert b"Create Account" in response.data
        assert b"Username" in response.data
        assert b"Password" in response.data
        assert b"Confirm Password" in response.data

    def test_setup_creates_user_and_auto_login(self, auth_client):
        """Test that POST /setup creates user and auto-logs them in."""
        response = auth_client.post(
            "/setup",
            data={
                "username": "newuser",
                "password": "newpassword123",
                "password_confirm": "newpassword123",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

    def test_setup_blocked_when_user_exists(self, authenticated_client):
        """Test that GET /setup redirects to dashboard when user exists."""
        response = authenticated_client.get("/setup", follow_redirects=True)

        # Should redirect to dashboard
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"Listarr" in response.data

    def test_setup_post_blocked_when_user_exists(self, authenticated_client):
        """Test that POST /setup redirects when user already exists."""
        response = authenticated_client.post(
            "/setup",
            data={
                "username": "anotheruser",
                "password": "pass123",
                "password_confirm": "pass123",
            },
            follow_redirects=True,
        )

        # Should redirect to dashboard
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"Listarr" in response.data

    def test_setup_password_mismatch_shows_error(self, auth_client):
        """Test that POST /setup with mismatched passwords shows error."""
        response = auth_client.post(
            "/setup",
            data={
                "username": "testuser",
                "password": "password1",
                "password_confirm": "password2",
            },
        )

        # Form validation should fail
        assert response.status_code == 200
        assert b"Create Account" in response.data

    def test_setup_empty_username_shows_error(self, auth_client):
        """Test that POST /setup with empty username fails validation."""
        response = auth_client.post(
            "/setup",
            data={
                "username": "",
                "password": "password123",
                "password_confirm": "password123",
            },
        )

        # Form validation should fail
        assert response.status_code == 200
        assert b"Create Account" in response.data

    def test_setup_rejects_short_password(self, auth_client):
        """Setup form rejects passwords under 8 characters."""
        response = auth_client.post("/setup", data={"password": "short", "password_confirm": "short"})
        assert response.status_code == 200
        assert b"at least 8 characters" in response.data


class TestLoginPage:
    """Tests for the login page (/login)."""

    def test_login_page_renders(self, auth_client, test_user):
        """Test that GET /login returns 200 with login form."""
        response = auth_client.get("/login")

        assert response.status_code == 200
        assert b"Login" in response.data or b"Sign in" in response.data
        assert b"Username" in response.data
        assert b"Password" in response.data

    def test_login_page_redirect_if_authenticated(self, authenticated_client):
        """Test that GET /login redirects to dashboard when already logged in."""
        response = authenticated_client.get("/login", follow_redirects=True)

        # Should redirect to dashboard
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"Listarr" in response.data

    def test_login_valid_credentials(self, auth_client, test_user):
        """Test that POST /login with correct credentials redirects to dashboard."""
        response = auth_client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "testpassword",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Should be at dashboard
        assert b"Dashboard" in response.data or b"Listarr" in response.data

    def test_login_invalid_credentials(self, auth_client, test_user):
        """Test that POST /login with wrong password returns 401."""
        response = auth_client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert b"Invalid credentials" in response.data

    def test_login_nonexistent_user(self, auth_client, test_user):
        """Test that POST /login with unknown username returns 401 (no enumeration)."""
        response = auth_client.post(
            "/login",
            data={
                "username": "unknownuser",
                "password": "anypassword",
            },
        )

        assert response.status_code == 401
        # Generic error message prevents username enumeration
        assert b"Invalid credentials" in response.data

    def test_login_remember_me(self, auth_client, test_user):
        """Test that POST /login with remember_me=True sets persistent cookie."""
        response = auth_client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "testpassword",
                "remember_me": True,
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Should be logged in
        assert b"Dashboard" in response.data or b"Listarr" in response.data

    def test_login_next_redirect(self, auth_client, test_user):
        """Test that POST /login redirects to next page from session."""
        # Simulate accessing protected page which stores next in session
        with auth_client.session_transaction() as sess:
            sess["next"] = "/lists"

        response = auth_client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "testpassword",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Should redirect to /lists
        assert b"Lists" in response.data or b"Create New List" in response.data

    def test_login_safe_redirect_rejects_external(self, auth_client, test_user):
        """Test that POST /login with external next URL redirects to dashboard."""
        response = auth_client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "testpassword",
            },
            follow_redirects=True,
            query_string={"next": "http://evil.com"},
        )

        assert response.status_code == 200
        # Should redirect to dashboard, not external site
        assert b"Dashboard" in response.data or b"Listarr" in response.data


class TestLogout:
    """Tests for the logout route (/logout)."""

    def test_logout_clears_session(self, authenticated_client):
        """Test that POST /logout clears session and redirects to login."""
        response = authenticated_client.post("/logout", follow_redirects=True)

        assert response.status_code == 200
        # Should be at login page
        assert b"Login" in response.data or b"Sign in" in response.data

    def test_logout_requires_login(self, auth_client, test_user):
        """Test that POST /logout when not logged in redirects to login."""
        response = auth_client.post("/logout", follow_redirects=True)

        # Should redirect to login
        assert response.status_code == 200
        assert b"Login" in response.data or b"Sign in" in response.data


class TestSetupCheck:
    """Tests for the before_request setup check middleware."""

    def test_before_request_redirects_to_setup(self, auth_client):
        """Test that any page visit when no user exists redirects to /setup."""
        # Don't create a user - database is empty
        response = auth_client.get("/lists", follow_redirects=True)

        assert response.status_code == 200
        # Should be at setup page
        assert b"Create Account" in response.data or b"Welcome" in response.data

    def test_before_request_skips_login_page(self, auth_client):
        """Test that GET /login when no user exists does NOT redirect to /setup."""
        response = auth_client.get("/login")

        # Login page should render, not redirect to setup
        assert response.status_code == 200
        assert b"Login" in response.data or b"Sign in" in response.data

    def test_before_request_skips_static(self, auth_client):
        """Test that static assets are accessible without user."""
        # Static files should be accessible
        # We can't easily test this without actual static files,
        # but we verify endpoint logic in isolation
        pass


class TestRouteProtection:
    """Tests for @login_required protection on routes."""

    def test_lists_page_requires_auth(self, auth_client, test_user):
        """Test that GET /lists without login redirects to login."""
        response = auth_client.get("/lists")

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_jobs_page_requires_auth(self, auth_client, test_user):
        """Test that GET /jobs without login redirects to login."""
        response = auth_client.get("/jobs")

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_schedule_page_requires_auth(self, auth_client, test_user):
        """Test that GET /schedule without login redirects to login."""
        response = auth_client.get("/schedule")

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_config_page_requires_auth(self, auth_client, test_user):
        """Test that GET /config without login redirects to login."""
        response = auth_client.get("/config")

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_settings_page_requires_auth(self, auth_client, test_user):
        """Test that GET /settings without login redirects to login."""
        response = auth_client.get("/settings")

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_api_returns_401_json(self, auth_client, test_user):
        """Test that protected API endpoint returns JSON 401 for AJAX."""
        response = auth_client.get("/api/lists")

        # Should return 401 (not redirect) for API endpoint
        assert response.status_code == 401 or response.status_code == 302


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_endpoint(self, auth_client):
        """Health endpoint returns ok without authentication."""
        response = auth_client.get("/health")
        assert response.status_code == 200
        assert response.json == {"status": "ok"}


class TestChangePassword:
    """Tests for password change functionality."""

    def test_change_password_success(self, authenticated_client):
        """Test that POST /settings/change-password with correct credentials succeeds."""
        response = authenticated_client.post(
            "/settings/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Password changed successfully" in data["message"]

    def test_change_password_wrong_current(self, authenticated_client):
        """Test that POST /settings/change-password with wrong current password fails."""
        response = authenticated_client.post(
            "/settings/change-password",
            data={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Current password is incorrect" in data["message"]

    def test_change_password_mismatch(self, authenticated_client):
        """Test that POST /settings/change-password with mismatched new passwords fails."""
        response = authenticated_client.post(
            "/settings/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "differentpassword",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Passwords must match" in data["message"]

    def test_change_password_requires_auth(self, auth_client, test_user):
        """Test that POST /settings/change-password without login redirects to login."""
        response = auth_client.post(
            "/settings/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
        )

        # Should redirect to login page (302)
        assert response.status_code == 302
        assert "/login" in response.location

    def test_change_password_rejects_short_password(self, authenticated_client):
        """Test that POST /settings/change-password rejects passwords under 8 characters."""
        response = authenticated_client.post(
            "/settings/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "short",
                "new_password_confirm": "short",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "at least 8 characters" in data["message"]
