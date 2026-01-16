import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from listarr.services.crypto_utils import load_encryption_key

db = SQLAlchemy()
csrf = CSRFProtect()

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

    # Initialize dashboard cache at startup
    with app.app_context():
        from .services.dashboard_cache import initialize_dashboard_cache
        initialize_dashboard_cache(app)

    return app
