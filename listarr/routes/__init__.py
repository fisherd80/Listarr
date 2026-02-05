from flask import Blueprint

bp = Blueprint("main", __name__)

# Import route modules to register routes with blueprint  # noqa: E402
from listarr.routes.config_routes import *  # noqa: E402, F403
from listarr.routes.dashboard_routes import *  # noqa: E402, F403
from listarr.routes.jobs_routes import *  # noqa: E402, F403
from listarr.routes.lists_routes import *  # noqa: E402, F403
from listarr.routes.schedule_routes import *  # noqa: E402, F403
from listarr.routes.settings_routes import *  # noqa: E402, F403
