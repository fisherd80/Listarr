import logging
import os
from datetime import timedelta

__version__ = "2.0.1"

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException

from listarr.services.crypto_utils import load_encryption_key, load_or_generate_secret_key

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()


# Track if we've already logged WAL mode status (avoid log spam)
_wal_mode_logged = False


# Enable SQLite optimizations for better concurrent access
# This listener is registered at module level to catch all engine connections
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    global _wal_mode_logged
    # Only apply to SQLite connections
    if "sqlite" in str(type(dbapi_connection)).lower():
        cursor = dbapi_connection.cursor()
        journal_mode = "WAL"
        try:
            # Try WAL mode first (best for concurrent access)
            cursor.execute("PRAGMA journal_mode=WAL")
            result = cursor.fetchone()
            if result and result[0].upper() != "WAL":
                # WAL mode was requested but filesystem returned different mode
                journal_mode = result[0].upper()
                raise ValueError(f"Filesystem returned {journal_mode} instead of WAL")
        # Intentionally broad: WAL mode must gracefully degrade on any filesystem/driver issue
        except Exception as e:
            # WAL mode can fail on certain filesystems (NFS, FUSE, network shares)
            # Fall back to DELETE mode which is universally supported
            journal_mode = "DELETE"
            try:
                cursor.execute("PRAGMA journal_mode=DELETE")
            # Intentionally broad: WAL mode must gracefully degrade on any filesystem/driver issue
            except Exception:
                journal_mode = "default"
            if not _wal_mode_logged:
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"SQLite WAL mode unavailable ({e}), using {journal_mode} mode. "
                    "This may reduce concurrent performance but ensures stability."
                )
                _wal_mode_logged = True
        # Set busy timeout regardless of journal mode
        cursor.execute("PRAGMA busy_timeout=5000")  # 5 second wait on locks
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # SECURE_COOKIES env var: set to "true" when serving over HTTPS (e.g., behind reverse proxy)
    # Default False for self-hosted homelab HTTP deployments
    secure_cookies = os.environ.get("SECURE_COOKIES", "false").lower() == "true"

    app.config.from_mapping(
        SECRET_KEY=load_or_generate_secret_key(app.instance_path),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'listarr.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16 MB max request size
        SESSION_COOKIE_SECURE=secure_cookies,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
        REMEMBER_COOKIE_SECURE=secure_cookies,
        REMEMBER_COOKIE_DURATION=timedelta(days=30),
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    # Configure logging from LOG_LEVEL environment variable
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logging.basicConfig(level=log_level, format="%(asctime)s %(name)s %(levelname)s: %(message)s")

    # Suppress noisy library logs unless DEBUG mode
    if log_level > logging.DEBUG:
        for logger_name in ["httpx", "httpcore", "urllib3", "werkzeug"]:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Load encryption key
    try:
        load_encryption_key(instance_path=app.instance_path)  # Pass instance path explicitly
        app.logger.info("Encryption key loaded successfully")
    except RuntimeError as e:
        app.logger.error(f"Encryption key error: {e}")
        raise

    db.init_app(app)
    csrf.init_app(app)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "main.login_page"
    login_manager.login_message = None  # Disable flash messages, app uses toast

    from .routes import bp as main_bp

    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_app_version():
        repo_root = "https://github.com/fisherd80/Listarr"
        release_base = f"{repo_root}/releases/tag/"
        normalized_version = ""

        if __version__:
            normalized_version = __version__ if __version__.startswith("v") else f"v{__version__}"

        return {
            "app_version": normalized_version,
            "app_version_url": f"{release_base}{normalized_version}" if normalized_version else repo_root,
        }

    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Content Security Policy
        # style-src 'unsafe-inline' required for Tailwind CSS utility classes
        # script-src 'unsafe-inline' required for inline event handlers
        # Tailwind is now compiled locally - no CDN allowlist needed
        # img-src includes TMDB for poster images and data: for inline SVGs
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https://image.tmdb.org; "
            "font-src 'self'; "
            "frame-ancestors 'self'"
        )

        # HSTS only when actually served over HTTPS
        # Per user decision: don't enable by default (too risky for self-hosted HTTP)
        if not app.debug and request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "Not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "Internal server error"}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "CSRF token missing or invalid"}), 400
        return render_template("errors/404.html"), 400

    @app.errorhandler(Exception)
    def unhandled_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.error(f"Unhandled exception: {error}", exc_info=True)
        db.session.rollback()
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "Internal server error"}), 500
        return render_template("errors/500.html"), 500

    # Initialize database and recover interrupted jobs at startup
    with app.app_context():
        # Import models so they are registered with SQLAlchemy
        from listarr import models  # noqa: F401

        # Create tables if they don't exist
        db.create_all()

        # Ensure cross-process duplicate-job guard index exists on existing databases.
        # db.create_all() only creates tables/indexes for new databases; it does not
        # add new indexes to tables that already exist. This migration call is
        # idempotent (IF NOT EXISTS) and safe to run on every startup.
        _ensure_unique_running_job_index(app)

        # Recover interrupted jobs
        recover_interrupted_jobs(app)

        # Initialize scheduler (only in designated worker or development)
        scheduler_worker = os.environ.get("SCHEDULER_WORKER", "true")  # Default true for dev
        if scheduler_worker == "true":
            from listarr.services.scheduler import init_scheduler

            init_scheduler(app)
            app.logger.info("Scheduler initialized")
        else:
            app.logger.debug("Scheduler not initialized in this worker")

    return app


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    from listarr.models.user_model import User

    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access attempts."""
    # For AJAX/JSON requests, return JSON error
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    # For page requests, store next URL and redirect to login
    session["next"] = request.url
    return redirect(url_for("main.login_page"))


def _ensure_unique_running_job_index(app):
    """
    Create the cross-process duplicate-job guard index on existing databases.

    db.create_all() only creates indexes declared in __table_args__ for brand-new
    tables. On an already-existing 'jobs' table the index must be applied via DDL.
    This function is idempotent: IF NOT EXISTS means it is safe to call on every
    startup whether the index already exists or not.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    ddl = text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_jobs_one_running_per_list ON jobs (list_id) WHERE status = 'running'"
    )
    try:
        with app.app_context():
            db.session.execute(ddl)
            db.session.commit()
    except OperationalError as e:
        app.logger.warning(f"Could not create unique running-job index: {e}")


def recover_interrupted_jobs(app):
    """Mark any 'running' jobs as failed on startup."""
    from datetime import datetime, timezone

    from sqlalchemy.exc import OperationalError

    from listarr.models.jobs_model import Job

    try:
        running_jobs = Job.query.filter_by(status="running").all()
        for job in running_jobs:
            job.status = "failed"
            job.error_message = "Job interrupted by application restart"
            job.error_details = "Application was restarted while job was running"
            job.completed_at = datetime.now(timezone.utc)

        if running_jobs:
            db.session.commit()
            app.logger.warning(f"Recovered {len(running_jobs)} interrupted jobs")
    except OperationalError:
        # Table doesn't exist yet (e.g., in-memory database before create_all)
        app.logger.debug("Jobs table not yet created, skipping recovery")
