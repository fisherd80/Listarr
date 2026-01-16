# Import the db instance (SQLAlchemy) from your main app package
from listarr import db

# Import all model classes
from listarr.models.user_model import User
from listarr.models.service_config_model import ServiceConfig, MediaImportSettings
from listarr.models.tag_model import Tag
from listarr.models.lists_model import List
from listarr.models.jobs_model import Job, JobItem

