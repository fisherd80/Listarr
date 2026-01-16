from listarr import db
from datetime import datetime, timezone
from listarr.models.custom_types import TZDateTime

class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(20), nullable=False)
    tag_id = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(100), nullable=False)

    created_at = db.Column(TZDateTime, default=lambda: datetime.now(timezone.utc))
