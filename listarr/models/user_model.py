from listarr import db
from datetime import datetime, timezone
from listarr.models.custom_types import TZDateTime

class User(db.Model):
    __tablename__="users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(TZDateTime, default=lambda: datetime.now(timezone.utc))
