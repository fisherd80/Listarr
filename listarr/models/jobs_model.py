from listarr import db
from listarr.models.custom_types import TZDateTime


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey("lists.id"))
    list_name = db.Column(db.String(255))  # Denormalized, survives list deletion

    status = db.Column(db.String(20))  # pending/running/failed/completed
    started_at = db.Column(TZDateTime)
    completed_at = db.Column(TZDateTime)  # Renamed from finished_at
    duration = db.Column(db.Integer)  # Seconds, calculated at job completion

    triggered_by = db.Column(db.String(20), default="manual")  # manual/scheduled
    retry_count = db.Column(db.Integer, default=0)

    items_found = db.Column(db.Integer, default=0)
    items_added = db.Column(db.Integer, default=0)
    items_skipped = db.Column(db.Integer, default=0)
    items_failed = db.Column(db.Integer, default=0)  # Count of failed items

    error_message = db.Column(db.Text)  # User-friendly error message
    error_details = db.Column(db.Text)  # Technical stack trace

    def to_dict(self):
        """Convert Job to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "list_id": self.list_id,
            "list_name": self.list_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "triggered_by": self.triggered_by,
            "retry_count": self.retry_count,
            "items_found": self.items_found,
            "items_added": self.items_added,
            "items_skipped": self.items_skipped,
            "items_failed": self.items_failed,
            "error_message": self.error_message,
            "error_details": self.error_details,
        }


class JobItem(db.Model):
    __tablename__ = "job_items"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    tmdb_id = db.Column(db.Integer)
    title = db.Column(db.String(255))

    status = db.Column(db.String(20))  # added/skipped/failed
    message = db.Column(db.Text)

    def to_dict(self):
        """Convert JobItem to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "status": self.status,
            "message": self.message,
        }
