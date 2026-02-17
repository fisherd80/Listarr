from urllib.parse import urljoin, urlparse

from flask import current_app, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from listarr import db
from listarr.forms.auth_forms import LoginForm, SetupForm
from listarr.models.user_model import User
from listarr.routes import bp


def is_safe_redirect_url(target):
    """Validate redirect URL to prevent open redirect attacks."""
    if not target:
        return False
    ref_url = urlparse(urljoin(request.host_url, target))
    test_url = urlparse(request.host_url)
    return ref_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@bp.route("/login", methods=["GET", "POST"])
def login_page():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard_page"))

    form = LoginForm()
    error = None

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            error = "Invalid credentials"
            return render_template("auth/login.html", form=form, error=error), 401

        login_user(user, remember=form.remember_me.data)

        # Get next page from session or query string
        next_page = session.pop("next", None) or request.args.get("next")

        # Validate redirect URL to prevent open redirect attacks
        if not is_safe_redirect_url(next_page):
            next_page = url_for("main.dashboard_page")

        return redirect(next_page)

    return render_template("auth/login.html", form=form, error=error)


@bp.route("/setup", methods=["GET", "POST"])
def setup_page():
    """First-run setup wizard."""
    # Block if user already exists
    if User.query.first() is not None:
        return redirect(url_for("main.dashboard_page"))

    form = SetupForm()

    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Auto-login user
        login_user(user)
        current_app.logger.info(f"Initial user created: {user.username}")

        return redirect(url_for("main.dashboard_page"))

    return render_template("auth/setup.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Logout user."""
    logout_user()
    return redirect(url_for("main.login_page"))


@bp.route("/health")
def health_check():
    """Health check endpoint for Docker HEALTHCHECK."""
    return jsonify({"status": "ok"}), 200


@bp.before_app_request
def check_setup():
    """Redirect to setup page if no users exist."""
    # Allow static files, auth routes, and health check
    if request.endpoint and (
        request.endpoint.startswith("static")
        or request.endpoint in ("main.login_page", "main.setup_page", "main.health_check")
    ):
        return

    # Skip if endpoint is None (Flask internals)
    if request.endpoint is None:
        return

    # Redirect to setup if no users exist
    if User.query.first() is None:
        return redirect(url_for("main.setup_page"))
