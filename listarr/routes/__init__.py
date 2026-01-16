from flask import Blueprint

bp = Blueprint("main", __name__)

# Import all model classes
from listarr.routes.dashboard_routes import *
from listarr.routes.lists_routes import *
from listarr.routes.jobs_routes import *
from listarr.routes.config_routes import *
from listarr.routes.settings_routes import *
