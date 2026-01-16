from listarr import db
from datetime import datetime, timezone
from listarr.models.custom_types import TZDateTime

class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey("lists.id"))

    status = db.Column(db.String(20))  # pending/running/failed/completed
    started_at = db.Column(TZDateTime)
    finished_at = db.Column(TZDateTime)

    items_found = db.Column(db.Integer, default=0)
    items_added = db.Column(db.Integer, default=0)
    items_skipped = db.Column(db.Integer, default=0)

    error_message = db.Column(db.Text)

class JobItem(db.Model):
    __tablename__ = "job_items"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)

    tmdb_id = db.Column(db.Integer)
    title = db.Column(db.String(255))

    status = db.Column(db.String(20))  # added/skipped/failed
    message = db.Column(db.Text)

