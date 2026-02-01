from datetime import datetime, timezone

from listarr import db
from listarr.models.custom_types import TZDateTime


class List(db.Model):
    __tablename__ = "lists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    target_service = db.Column(db.String(20), nullable=False)
    tmdb_list_type = db.Column(db.String(50), nullable=False)

    override_root_folder = db.Column(db.String(255))
    override_quality_profile = db.Column(db.Integer)
    override_monitored = db.Column(db.Integer)
    override_search_on_add = db.Column(db.Integer)
    override_tag_id = db.Column(db.Integer)
    override_season_folder = db.Column(db.Integer)  # 1=yes, 0=no, None=use default (Sonarr only)

    filters_json = db.Column(db.JSON, nullable=False)
    limit = db.Column(db.Integer)

    cache_enabled = db.Column(db.Boolean, default=False)
    cache_ttl_hours = db.Column(db.Integer)

    schedule_cron = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True, index=True)

    last_run_at = db.Column(TZDateTime)
    last_tmdb_fetch_at = db.Column(TZDateTime)
    cache_valid_until = db.Column(TZDateTime)

    created_at = db.Column(TZDateTime, default=lambda: datetime.now(timezone.utc))
