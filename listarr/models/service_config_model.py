from listarr import db
from datetime import datetime, timezone
from sqlalchemy.sql import func
from listarr.models.custom_types import TZDateTime

class ServiceConfig(db.Model):
    __tablename__="service_config"

    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(20), unique=True, nullable=False)

    base_url = db.Column(db.String(255), nullable=True)
    api_key_encrypted = db.Column(db.Text, nullable=False)

    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    last_tested_at = db.Column(TZDateTime)
    last_test_status = db.Column(db.String(20))

    created_at = db.Column(TZDateTime, default=lambda: datetime.now(timezone.utc))


class MediaImportSettings(db.Model):
    __tablename__ = "media_import_settings"

    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(20), nullable=False)  

    root_folder = db.Column(db.String(255), nullable=False)
    quality_profile_id = db.Column(db.Integer, nullable=False)

    monitored = db.Column(db.Boolean, default=True)
    search_on_add = db.Column(db.Boolean, default=True)
    season_folder = db.Column(db.Boolean, default=True)  

    default_tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"))
