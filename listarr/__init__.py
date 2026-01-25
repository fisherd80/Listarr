import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
from listarr.services.crypto_utils import load_encryption_key

db = SQLAlchemy()
csrf = CSRFProtect()


# Enable SQLite WAL mode for better concurrent access
# This listener is registered at module level to catch all engine connections
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Only apply to SQLite connections
    if 'sqlite' in str(type(dbapi_connection)).lower():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")  # 5 second wait on locks
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("LISTARR_SECRET_KEY", "dev_key_change_me"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'listarr.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s %(levelname)s: %(message)s'
    )

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

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Initialize dashboard cache and recover interrupted jobs at startup
    with app.app_context():
        from .services.dashboard_cache import initialize_dashboard_cache
        initialize_dashboard_cache(app)

        # Recover interrupted jobs
        recover_interrupted_jobs(app)

    return app


def recover_interrupted_jobs(app):
    """Mark any 'running' jobs as failed on startup."""
    from listarr.models.jobs_model import Job
    from datetime import datetime, timezone
    from sqlalchemy.exc import OperationalError

    try:
        running_jobs = Job.query.filter_by(status='running').all()
        for job in running_jobs:
            job.status = 'failed'
            job.error_message = 'Job interrupted by application restart'
            job.error_details = 'Application was restarted while job was running'
            job.completed_at = datetime.now(timezone.utc)

        if running_jobs:
            db.session.commit()
            app.logger.warning(f"Recovered {len(running_jobs)} interrupted jobs")
    except OperationalError:
        # Table doesn't exist yet (e.g., in-memory database before create_all)
        app.logger.debug("Jobs table not yet created, skipping recovery")
