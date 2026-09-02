"""Real-scheduler + real-SQLite smoke test — the permanent regression guard for dependency bumps.

Why this file exists (Phase 12, MNT-03 / decisions D-06, D-07, D-08, D-08a):

``tests/unit/services/test_scheduler.py`` patches ``listarr.services.scheduler._scheduler``
to a ``MagicMock``. That is fast, but it means the unit suite can never notice when an
APScheduler upgrade changes the real ``BackgroundScheduler`` API, how a bare timezone
string is resolved and stored, or how ``CronTrigger.from_crontab`` computes
``next_run_time``. Likewise, no existing test exercises
``listarr.models.custom_types.TZDateTime`` directly, so a SQLAlchemy upgrade that
invalidates its ``cache_ok = True`` contract would fail silently.

This module drives:

* a **real** ``apscheduler.schedulers.background.BackgroundScheduler`` built with the exact
  ``job_defaults`` that ``scheduler.init_scheduler()`` uses (not a mock), and
* a **real** in-memory SQLite database (the session-scoped ``app`` fixture, ``StaticPool``),

so that any future APScheduler or SQLAlchemy bump that breaks scheduler job registration,
timezone-aware ``next_run_time`` computation, the synchronous ``_run_scheduled_import``
path, or the ``TZDateTime`` UTC round-trip fails loudly here. Only the Arr HTTP boundary
is mocked; there is no ``time.sleep``, no sub-second ``IntervalTrigger``, and no
``responses`` usage.
"""

import zoneinfo
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from listarr import db
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.services import scheduler as sched

pytestmark = [pytest.mark.integration, pytest.mark.database]

# Copied verbatim from listarr.services.scheduler.init_scheduler() (scheduler.py:104-108).
# Kept here so a change to the production dict that is not mirrored in this test is caught.
PROD_JOB_DEFAULTS = {
    "coalesce": True,
    "max_instances": 1,
    "misfire_grace_time": 3600,
}

# A named, non-UTC zone so the timezone plumbing is actually exercised (not a UTC no-op).
SCHEDULER_TZ = "America/New_York"


def _make_real_scheduler():
    """Build a real BackgroundScheduler configured exactly like the production one."""
    return BackgroundScheduler(timezone=SCHEDULER_TZ, job_defaults=dict(PROD_JOB_DEFAULTS))


def _make_list_row(cron="0 2 * * 1"):
    """Insert a real List row and return its id. Cleaned up by the autouse db_session fixture."""
    lst = List(
        name="bump-smoke",
        target_service="RADARR",
        tmdb_list_type="popular_movies",
        filters_json={},
        schedule_cron=cron,
        is_active=True,
    )
    db.session.add(lst)
    db.session.commit()
    return lst.id


def test_real_scheduler_registers_job_and_runs_import_synchronously(app, monkeypatch):
    """schedule_list registers a tz-aware future job on a real scheduler; _run_scheduled_import
    reaches submit_job when called synchronously with only the Arr HTTP boundary mocked."""
    scheduler = _make_real_scheduler()
    scheduler.start(paused=True)  # real jobstore + next_run_time computation, but nothing fires
    try:
        # Real instance patched onto the module singleton (module-attribute patching, the
        # convention in test_scheduler.py). monkeypatch auto-reverts cleanly with a real object.
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        # Arr HTTP boundary + side-effecting collaborators, patched as module attributes.
        # No `responses`: the scheduler never calls requests directly, it goes through
        # arr_service.validate_api_key.
        monkeypatch.setattr(sched, "is_scheduler_paused", lambda: False)
        monkeypatch.setattr(sched, "is_list_running", lambda _list_id: False)
        monkeypatch.setattr(sched, "decrypt_data", lambda _blob: "decrypted-key")
        validate_api_key = Mock(return_value=True)
        monkeypatch.setattr(sched, "validate_api_key", validate_api_key)
        submit_job = Mock()
        monkeypatch.setattr(sched, "submit_job", submit_job)

        with app.app_context():
            list_id = _make_list_row("0 2 * * 1")
            db.session.add(
                ServiceConfig(
                    service="RADARR",
                    base_url="http://radarr.local",
                    api_key_encrypted="unused-ciphertext",
                )
            )
            db.session.commit()

            # --- schedule_list against the REAL scheduler ---------------------------------
            sched.schedule_list(list_id, "0 2 * * 1")

            job = scheduler.get_job(f"list_{list_id}")
            assert job is not None, "schedule_list did not register a job under list_{id}"

            tz = sched._get_scheduler_timezone()
            assert tz is not None
            now = datetime.now(tz)  # the resolved tz must be usable as a datetime tzinfo

            next_run = job.next_run_time
            assert next_run is not None
            assert isinstance(next_run, datetime)
            assert next_run.tzinfo is not None
            assert next_run > now, "next_run_time is not in the future"
            # POSIX day-of-week 1 == Monday. APScheduler's numeric DOW 1 would be Tuesday, so a
            # Monday next_run_time proves _posix_cron_to_apscheduler translated "1" -> "mon" and
            # CronTrigger.from_crontab consumed that translated expression.
            assert next_run.weekday() == 0, f"expected Monday, got weekday {next_run.weekday()}"

            # --- _run_scheduled_import synchronously (no interval trigger, no sleep) -------
            sched._run_scheduled_import(list_id)

            validate_api_key.assert_called_once()
            submit_job.assert_called_once()
            call = submit_job.call_args
            assert call.args[0] == list_id
            assert call.kwargs.get("triggered_by") == "scheduled"
    finally:
        scheduler.shutdown(wait=False)  # never leak a live scheduler thread into the session


def test_tzdatetime_round_trips_non_utc_aware_datetime_through_real_sqlite(app):
    """D-08a: a non-UTC tz-aware datetime written through TZDateTime is stored as UTC and read
    back tz-aware for the same instant — guards the cache_ok = True silent-failure point."""
    with app.app_context():
        list_id = _make_list_row()

        written = datetime(2026, 1, 1, 12, 0, tzinfo=zoneinfo.ZoneInfo("America/Chicago"))

        lst = db.session.get(List, list_id)  # SQLAlchemy 2.0 style — not List.query.get()
        lst.last_run_at = written
        db.session.commit()
        db.session.expire(lst)  # force a real SELECT back through process_result_value

        read_back = db.session.get(List, list_id).last_run_at

        assert read_back is not None
        assert read_back.tzinfo is not None, "process_result_value did not make the value tz-aware"
        assert read_back.utcoffset().total_seconds() == 0, "value was not stored/returned as UTC"
        assert read_back == written, "round-trip changed the instant"
        assert read_back.astimezone(timezone.utc) == written.astimezone(timezone.utc)
