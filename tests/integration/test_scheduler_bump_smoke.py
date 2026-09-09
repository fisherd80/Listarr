"""Real-scheduler + real-SQLite smoke test — the permanent regression guard for dependency bumps.

Why this file exists (Phase 12, MNT-03 / decisions D-06, D-07, D-08, D-08a):

``tests/unit/services/test_scheduler.py`` patches ``listarr.services.scheduler._scheduler``
to a ``MagicMock``. That is fast, but it means the unit suite can never notice when an
APScheduler upgrade changes the real ``BackgroundScheduler`` API, how a bare timezone
string is resolved and stored, or how ``CronTrigger.from_crontab`` computes
``next_run_time``. Likewise, no existing test exercises
``listarr.models.custom_types.TZDateTime`` directly against a real database, so a SQLAlchemy
upgrade that broke its bind/result processing (or its ``cache_ok = True`` contract) would
fail silently.

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

import logging
import zoneinfo
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import OperationalError

from listarr import db
from listarr.models.app_config_model import get_app_config
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.services import scheduler as sched
from listarr.utils import time_utils
from listarr.utils.time_utils import tz_key

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

# 02:00 every Monday. Shared by the List row and the schedule_list() call so the
# "Monday" / "hour 2" intent stays synced with the assertions below.
SMOKE_CRON = "0 2 * * 1"

# Accepted by cronsim (validate_cron_expression) but rejected by APScheduler's
# CronTrigger.from_crontab. This grammar gap is the live trigger-build failure
# path guarded by CR-01/CR-02.
APS_UNSUPPORTED_CRON = "0 2 L * *"


@pytest.fixture(autouse=True)
def _reset_reschedule_convergence_state():
    """CR-01 added module-level convergence state; keep it from leaking across tests."""
    sched._reschedule_incomplete = False
    sched.reset_reschedule_state()
    yield
    sched._reschedule_incomplete = False
    sched.reset_reschedule_state()


def _make_real_scheduler(timezone_name=SCHEDULER_TZ):
    """Build a real BackgroundScheduler configured exactly like the production one."""
    return BackgroundScheduler(timezone=timezone_name, job_defaults=dict(PROD_JOB_DEFAULTS))


def _make_list_row(cron=SMOKE_CRON):
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


def _set_app_timezone(value):
    cfg = get_app_config()
    cfg.timezone = value
    db.session.commit()
    time_utils.invalidate_app_timezone_memo()


def test_real_scheduler_registers_job_and_runs_import_synchronously(app, monkeypatch):
    """schedule_list registers a tz-aware future job on a real scheduler; _run_scheduled_import
    reaches submit_job when called synchronously with only the Arr HTTP boundary mocked."""
    scheduler = _make_real_scheduler()
    try:
        # real jobstore + next_run_time computation, but nothing fires. Inside the try so a
        # failure during start() still hits the finally and never leaks a scheduler thread.
        scheduler.start(paused=True)

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
            list_id = _make_list_row(SMOKE_CRON)
            db.session.add(
                ServiceConfig(
                    service="RADARR",
                    base_url="http://radarr.local",
                    api_key_encrypted="unused-ciphertext",
                )
            )
            db.session.commit()

            # --- schedule_list against the REAL scheduler ---------------------------------
            sched.schedule_list(list_id, SMOKE_CRON)

            job = scheduler.get_job(f"list_{list_id}")
            assert job is not None, "schedule_list did not register a job under list_{id}"

            tz = sched._get_scheduler_timezone()
            assert tz is not None
            # the resolved tz must be usable as a datetime tzinfo
            assert datetime.now(tz).tzinfo is not None

            next_run = job.next_run_time
            assert next_run is not None
            assert isinstance(next_run, datetime)
            assert next_run.tzinfo is not None
            assert next_run > datetime.now(timezone.utc), "next_run_time is not in the future"
            # POSIX day-of-week 1 == Monday. APScheduler's numeric DOW 1 would be Tuesday, so a
            # Monday next_run_time proves _posix_cron_to_apscheduler translated "1" -> "mon" and
            # CronTrigger.from_crontab consumed that translated expression.
            assert next_run.weekday() == 0, f"expected Monday, got weekday {next_run.weekday()}"
            # The trigger must have fired in America/New_York, NOT UTC — if the bare tz string
            # silently resolved to UTC these would fail (WR-01): NY keeps the 02:00 cron hour
            # local, and its offset is EST (-5h) or EDT (-4h), never zero.
            assert next_run.hour == 2, f"cron hour not preserved in local tz: got {next_run.hour}"
            assert next_run.utcoffset() in (
                timedelta(hours=-5),
                timedelta(hours=-4),
            ), f"next_run_time not in America/New_York (offset {next_run.utcoffset()})"

            # --- _run_scheduled_import synchronously (no interval trigger, no sleep) -------
            sched._run_scheduled_import(list_id)

            validate_api_key.assert_called_once()
            submit_job.assert_called_once()
            call = submit_job.call_args
            assert call.args[0] == list_id
            assert call.kwargs.get("triggered_by") == "scheduled"
    finally:
        # guard: shutdown() raises if start() never succeeded
        if scheduler.running:
            scheduler.shutdown(wait=False)  # never leak a live scheduler thread into the session


def test_tzdatetime_round_trips_non_utc_aware_datetime_through_real_sqlite(app):
    """D-08a: a non-UTC tz-aware datetime written through TZDateTime comes back tz-aware at the
    same instant, with a zero UTC offset on the loaded value — exercises process_bind_param and
    process_result_value end-to-end against real SQLite, the paths a TypeDecorator/result-
    processing regression in a SQLAlchemy bump would break (the ``cache_ok = True`` contract
    included, though this test does not isolate it)."""
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


def test_reschedule_all_moves_every_job_forward_into_new_zone(app, monkeypatch):
    scheduler = _make_real_scheduler()
    submit_job = Mock()
    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)
        monkeypatch.setattr(sched, "submit_job", submit_job)

        with app.app_context():
            _set_app_timezone("Europe/London")
            list_ids = [_make_list_row(SMOKE_CRON) for _ in range(3)]
            for list_id in list_ids:
                sched.schedule_list(list_id, SMOKE_CRON)

            before = {list_id: scheduler.get_job(f"list_{list_id}").next_run_time for list_id in list_ids}

            assert sched.reschedule_all_lists("Europe/London") == (3, 0)

            assert tz_key(scheduler.timezone) == "Europe/London"
            for list_id in list_ids:
                job = scheduler.get_job(f"list_{list_id}")
                assert job is not None
                next_run = job.next_run_time
                assert next_run is not None
                assert next_run != before[list_id]
                assert next_run.tzinfo is not None
                assert next_run > datetime.now(timezone.utc)
                assert next_run.weekday() == 0
                assert next_run.hour == 2
                assert next_run.utcoffset() in (timedelta(0), timedelta(hours=1))
            submit_job.assert_not_called()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_reschedule_all_partial_failure_returns_counts(app, monkeypatch):
    scheduler = _make_real_scheduler()
    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            valid_ids = [_make_list_row(SMOKE_CRON) for _ in range(2)]
            _make_list_row("not a cron")
            for list_id in valid_ids:
                sched.schedule_list(list_id, SMOKE_CRON)

            assert sched.reschedule_all_lists("Asia/Tokyo") == (2, 1)

            for list_id in valid_ids:
                job = scheduler.get_job(f"list_{list_id}")
                assert job is not None
                assert job.next_run_time is not None
                assert job.next_run_time > datetime.now(timezone.utc)
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_tz_poll_converges_then_no_ops_and_ignores_bad_value(app, monkeypatch, caplog):
    scheduler = _make_real_scheduler()
    calls = []
    real_reschedule = sched.reschedule_all_lists

    def spy_reschedule(tz_str, blocking=True):
        calls.append((tz_str, blocking))
        return real_reschedule(tz_str, blocking=blocking)

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)
        monkeypatch.setattr(sched, "reschedule_all_lists", spy_reschedule)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            sched._tz_poll_tick()

            assert calls == [("Asia/Tokyo", False)]
            assert tz_key(scheduler.timezone) == "Asia/Tokyo"

            sched._tz_poll_tick()
            assert calls == [("Asia/Tokyo", False)]

            monkeypatch.setenv("TZ", "Europe/London")
            _set_app_timezone("Bogus/Zone")
            calls.clear()

            with caplog.at_level("WARNING", logger="listarr.services.scheduler"):
                sched._tz_poll_tick()
                sched._tz_poll_tick()
                sched._tz_poll_tick()

            assert calls == [("Europe/London", False)]
            assert tz_key(scheduler.timezone) == "Europe/London"
            warnings = [record for record in caplog.records if "Bogus/Zone" in record.getMessage()]
            assert len(warnings) == 1
    finally:
        time_utils.invalidate_app_timezone_memo()
        sched._tz_poll_last_bad_value = None
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_tz_poll_registered_and_scheduler_built_from_db_tz(app, monkeypatch):
    monkeypatch.setenv("SCHEDULER_WORKER", "true")
    monkeypatch.setattr(sched, "_scheduler", None)
    monkeypatch.setattr(sched, "_app", None)

    try:
        with app.app_context():
            _set_app_timezone("Australia/Sydney")
            sched.init_scheduler(app)

        job = sched._scheduler.get_job("_tz_poll")
        assert tz_key(sched._scheduler.timezone) == "Australia/Sydney"
        assert job is not None
        assert job.max_instances == 1
        assert job.coalesce is True
        assert job.trigger.interval == timedelta(seconds=60)
    finally:
        sched.shutdown_scheduler()
        time_utils.invalidate_app_timezone_memo()


def test_tz_poll_system_default_converges_to_fallback_zone(app, monkeypatch):
    scheduler = _make_real_scheduler("Asia/Tokyo")
    calls = []
    real_reschedule = sched.reschedule_all_lists

    def spy_reschedule(tz_str, blocking=True):
        calls.append((tz_str, blocking))
        return real_reschedule(tz_str, blocking=blocking)

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)
        monkeypatch.setattr(sched, "reschedule_all_lists", spy_reschedule)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            list_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(list_id, SMOKE_CRON)

            monkeypatch.setenv("TZ", "Europe/London")
            _set_app_timezone(None)
            sched._tz_poll_tick()

            assert calls == [("Europe/London", False)]
            assert tz_key(scheduler.timezone) == "Europe/London"
            job = scheduler.get_job(f"list_{list_id}")
            assert job is not None
            assert job.next_run_time is not None
            assert job.next_run_time.tzinfo is not None
            assert job.next_run_time > datetime.now(timezone.utc)
            assert job.next_run_time.utcoffset() in (timedelta(0), timedelta(hours=1))

            sched._tz_poll_tick()
            assert calls == [("Europe/London", False)]

            monkeypatch.delenv("TZ", raising=False)
            _set_app_timezone(None)
            sched._tz_poll_tick()

            assert calls[-1] == ("UTC", False)
            assert tz_key(scheduler.timezone) == "UTC"
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_reschedule_lock_skips_colliding_non_blocking_entrant(app, monkeypatch):
    scheduler = _make_real_scheduler()
    lock_acquired = False
    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            for _ in range(2):
                list_id = _make_list_row(SMOKE_CRON)
                sched.schedule_list(list_id, SMOKE_CRON)

            lock_acquired = sched._reschedule_lock.acquire(blocking=False)
            assert lock_acquired is True

            assert sched.reschedule_all_lists("Asia/Tokyo", blocking=False) == (0, 0)
            assert tz_key(scheduler.timezone) == "America/New_York"

            sched._tz_poll_tick()
            assert tz_key(scheduler.timezone) == "America/New_York"

            sched._reschedule_lock.release()
            lock_acquired = False

            sched._tz_poll_tick()
            assert tz_key(scheduler.timezone) == "Asia/Tokyo"

            assert sched._reschedule_lock.acquire(blocking=False) is True
            sched._reschedule_lock.release()
    finally:
        if lock_acquired:
            sched._reschedule_lock.release()
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_schedule_list_keeps_existing_job_when_trigger_build_fails(app, monkeypatch):
    """CR-02: a cron that cronsim accepts but APScheduler cannot build must leave the
    previously registered job intact instead of silently unscheduling the list."""
    scheduler = _make_real_scheduler()
    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            list_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(list_id, SMOKE_CRON)
            before = scheduler.get_job(f"list_{list_id}").next_run_time

            with pytest.raises(ValueError):
                sched.schedule_list(list_id, APS_UNSUPPORTED_CRON)

            job = scheduler.get_job(f"list_{list_id}")
            assert job is not None, "a failed trigger build must not remove the existing job"
            assert job.next_run_time == before
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_schedule_list_keeps_existing_job_when_add_job_fails(app, monkeypatch):
    """WR-07: CR-02 moved trigger construction ahead of the swap, but the old job was
    still removed before add_job ran. A failing add_job then left the list with no job at
    all, silently discarding the schedule the CR-02 comment promises to keep."""
    scheduler = _make_real_scheduler()
    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            list_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(list_id, SMOKE_CRON)
            before = scheduler.get_job(f"list_{list_id}").next_run_time

            def boom(*args, **kwargs):
                raise ValueError("jobstore rejected the job")

            monkeypatch.setattr(scheduler, "add_job", boom)
            with pytest.raises(ValueError):
                sched.schedule_list(list_id, SMOKE_CRON)

            job = scheduler.get_job(f"list_{list_id}")
            assert job is not None, "a failed add_job must not leave the list unscheduled"
            assert job.next_run_time == before
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_unbuildable_cron_is_quarantined_not_retried(app, monkeypatch):
    """CR-01: a cron that can never build a trigger is a deterministic failure. It must be
    quarantined and reported rather than retried, and must not consume anything that a
    *recoverable* failure would later need."""
    scheduler = _make_real_scheduler()
    calls = []
    real_reschedule = sched.reschedule_all_lists

    def spy_reschedule(tz_str, blocking=True):
        calls.append((tz_str, blocking))
        return real_reschedule(tz_str, blocking=blocking)

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            good_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(good_id, SMOKE_CRON)
            bad_id = _make_list_row(APS_UNSUPPORTED_CRON)

            assert real_reschedule("Asia/Tokyo") == (1, 1)
            assert tz_key(scheduler.timezone) == "Asia/Tokyo"

            # The bad list is named, not merely counted, and it does not masquerade as a
            # pending retry — retrying it is exactly what would never help.
            assert sched.get_unschedulable_lists() == {bad_id: APS_UNSUPPORTED_CRON}
            assert sched.reschedule_is_incomplete() is False

            monkeypatch.setattr(sched, "reschedule_all_lists", spy_reschedule)

            # The zone is applied and the only outstanding failure is quarantined, so the
            # poll does no work at all. No spinning, and nothing was "used up".
            for _ in range(5):
                sched._tz_poll_tick()
            assert calls == []

            # A genuine timezone change still rebuilds everything and re-diagnoses the
            # bad list against the new zone.
            _set_app_timezone("Europe/London")
            sched._tz_poll_tick()
            assert calls == [("Europe/London", False)]
            assert tz_key(scheduler.timezone) == "Europe/London"
            assert sched.get_unschedulable_lists() == {bad_id: APS_UNSUPPORTED_CRON}

            # Fixing the cron clears the quarantine on the next convergence pass.
            calls.clear()
            List.query.filter(List.id == bad_id).one().schedule_cron = SMOKE_CRON
            db.session.commit()
            _set_app_timezone("Asia/Tokyo")
            sched._tz_poll_tick()
            assert calls == [("Asia/Tokyo", False)]
            assert sched.get_unschedulable_lists() == {}
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_unclassified_exception_after_the_commit_still_arms_the_retry(app, monkeypatch):
    """WR-02: scheduler.timezone is the commit point, and only (ValueError, KeyError) were
    classified per list. Any other exception escaping after the commit used to unwind with
    _reschedule_incomplete still False, so the poll saw "converged" forever while the
    un-rebuilt remainder kept firing on the old zone. Unknown must mean recoverable."""
    scheduler = _make_real_scheduler()

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            _make_list_row(SMOKE_CRON)

            def boom(list_id, cron_expression):
                # Not ValueError and not KeyError: the whole point of the finding.
                raise RuntimeError("jobstore exploded")

            monkeypatch.setattr(sched, "schedule_list", boom)

            with pytest.raises(RuntimeError):
                sched.reschedule_all_lists("Asia/Tokyo")

            # The commit landed, so the zone moved...
            assert tz_key(scheduler.timezone) == "Asia/Tokyo"
            # ...but the rebuild did not finish, so this must not read as converged.
            assert sched.reschedule_is_incomplete() is True
            # And it is not a quarantine either - retrying is exactly what may help.
            assert sched.get_unschedulable_lists() == {}

            # The lock was released by the finally, so the poll can actually retry.
            assert sched._reschedule_lock.acquire(blocking=False) is True
            sched._reschedule_lock.release()
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_quarantine_is_rediagnosed_when_the_target_zone_changes(app, monkeypatch, caplog):
    """IN-02: the "log once" guard compared the cron alone, so the same bad cron failing
    against a second zone was silent even though the ERROR names the zone. Re-key on
    (cron, zone) so each distinct diagnosis is stated once, and name the zone in the
    periodic reminder so it can be matched to the ERROR that produced it."""
    scheduler = _make_real_scheduler()

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            bad_id = _make_list_row(APS_UNSUPPORTED_CRON)

            def verdicts():
                # schedule_list() logs its own unconditional "Failed to build trigger"
                # line; the deduplicated one is the quarantine verdict.
                return [r.message for r in caplog.records if "cannot be rescheduled into" in r.message]

            with caplog.at_level(logging.ERROR, logger="listarr.services.scheduler"):
                assert sched.reschedule_all_lists("Asia/Tokyo") == (0, 1)
                assert len(verdicts()) == 1
                assert "Asia/Tokyo" in verdicts()[0]

                # Same cron, same list, unchanged zone: still only said once.
                caplog.clear()
                assert sched.reschedule_all_lists("Asia/Tokyo") == (0, 1)
                assert verdicts() == []

                # New zone: a genuinely new verdict, so it is stated again.
                caplog.clear()
                assert sched.reschedule_all_lists("Europe/London") == (0, 1)
                assert len(verdicts()) == 1
                assert "Europe/London" in verdicts()[0]

            # The public projection is unchanged by the richer internal key.
            assert sched.get_unschedulable_lists() == {bad_id: APS_UNSUPPORTED_CRON}

            with caplog.at_level(logging.WARNING, logger="listarr.services.scheduler"):
                caplog.clear()
                sched._quarantine_reminder_countdown = 0
                sched._warn_about_quarantined_lists()
                reminder = " | ".join(r.message for r in caplog.records)
            assert "Europe/London" in reminder, "the periodic reminder never names a zone"
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_quarantine_is_cleared_by_the_remedy_its_warning_recommends(app, monkeypatch):
    """WR-01: the hourly WARN tells the operator to correct the cron, and the edit routes
    apply that correction through schedule_list() alone. Neither the zone nor the
    convergence flag changes, so reschedule_all_lists() never runs - yet the verdict must
    still clear, or the warning goes on making a claim that is no longer true. Deleting or
    deactivating the list must clear it too, rather than stranding a dead list id."""
    scheduler = _make_real_scheduler()

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            bad_id = _make_list_row(APS_UNSUPPORTED_CRON)
            assert sched.reschedule_all_lists("Asia/Tokyo") == (0, 1)
            assert sched.get_unschedulable_lists() == {bad_id: APS_UNSUPPORTED_CRON}

            # Exactly what lists_routes does after committing a corrected cron: no
            # timezone save, no poll tick, no rebuild.
            List.query.filter(List.id == bad_id).one().schedule_cron = SMOKE_CRON
            db.session.commit()
            sched.schedule_list(bad_id, SMOKE_CRON)

            assert sched.get_unschedulable_lists() == {}
            assert scheduler.get_job(f"list_{bad_id}") is not None

            # And the removal path: a quarantined list that is deactivated or deleted must
            # not leave a verdict behind referencing an id that no longer schedules.
            other_id = _make_list_row(APS_UNSUPPORTED_CRON)
            assert sched.reschedule_all_lists("Asia/Tokyo") == (1, 1)
            assert sched.get_unschedulable_lists() == {other_id: APS_UNSUPPORTED_CRON}

            sched.unschedule_list(other_id)
            assert sched.get_unschedulable_lists() == {}
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_rebuild_drops_list_jobs_the_query_no_longer_covers(app, monkeypatch):
    """WR-02: assigning scheduler.timezone does not rebuild existing triggers, so a job
    outside the active-and-scheduled query silently keeps firing on the old zone. A list
    deactivated by a non-scheduler worker is exactly that case."""
    scheduler = _make_real_scheduler()
    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            keep_id = _make_list_row(SMOKE_CRON)
            orphan_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(keep_id, SMOKE_CRON)
            sched.schedule_list(orphan_id, SMOKE_CRON)

            # Another gunicorn worker deactivates the list: the DB row changes, but
            # unschedule_list() was a no-op over there, so the job survives here.
            List.query.filter(List.id == orphan_id).one().is_active = False
            db.session.commit()

            _set_app_timezone("Asia/Tokyo")
            assert sched.reschedule_all_lists("Asia/Tokyo") == (1, 0)

            assert scheduler.get_job(f"list_{keep_id}") is not None
            assert scheduler.get_job(f"list_{orphan_id}") is None, "orphan kept its old-zone trigger"
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_orphan_sweep_keeps_a_job_added_after_the_rebuild_query(app, monkeypatch):
    """WR-03: the sweep used to compare against the id set from the query that opened the
    rebuild. On the scheduler worker, request threads share this process, so a schedule
    saved between that query and the sweep was deleted as an "orphan" and - because the
    rebuild then reported convergence - never restored. Simulate the interleaving by
    committing the row and registering its job from inside the rebuild loop."""
    scheduler = _make_real_scheduler()
    real_schedule_list = sched.schedule_list
    latecomer = {}

    def schedule_list_then_race(list_id, cron_expression):
        real_schedule_list(list_id, cron_expression)
        if latecomer:
            return
        # A request thread lands here: row committed first, then the job registered -
        # the ordering every mutator in lists_routes uses.
        latecomer["id"] = _make_list_row(SMOKE_CRON)
        real_schedule_list(latecomer["id"], SMOKE_CRON)

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            existing_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(existing_id, SMOKE_CRON)

            monkeypatch.setattr(sched, "schedule_list", schedule_list_then_race)
            assert sched.reschedule_all_lists("Asia/Tokyo") == (1, 0)

            assert scheduler.get_job(f"list_{existing_id}") is not None
            assert scheduler.get_job(f"list_{latecomer['id']}") is not None, (
                "the sweep deleted a valid job registered after the rebuild query"
            )
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_transient_db_failure_retries_indefinitely(app, monkeypatch):
    """CR-01: a locked database is recoverable, so the poll must keep retrying it. The
    old bounded budget gave up after three ticks and stranded every list on the previous
    timezone for the rest of the process lifetime."""
    scheduler = _make_real_scheduler()
    calls = []
    real_reschedule = sched.reschedule_all_lists

    class _BoomQuery:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            raise OperationalError("SELECT", {}, Exception("database is locked"))

    class _BoomList:
        query = _BoomQuery()
        id = List.id
        schedule_cron = List.schedule_cron
        is_active = List.is_active

    def spy_reschedule(tz_str, blocking=True):
        calls.append((tz_str, blocking))
        return real_reschedule(tz_str, blocking=blocking)

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            list_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(list_id, SMOKE_CRON)

            monkeypatch.setattr(sched, "List", _BoomList)
            monkeypatch.setattr(sched, "reschedule_all_lists", spy_reschedule)

            # Well past the three attempts the previous design allowed.
            for _ in range(10):
                sched._tz_poll_tick()
            assert calls == [("Asia/Tokyo", False)] * 10
            assert sched.reschedule_is_incomplete() is True
            assert tz_key(scheduler.timezone) == SCHEDULER_TZ

            # Contention clears; the very next tick converges.
            monkeypatch.setattr(sched, "List", List)
            sched._tz_poll_tick()
            assert tz_key(scheduler.timezone) == "Asia/Tokyo"
            assert sched.reschedule_is_incomplete() is False
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_lock_contention_does_not_forfeit_a_later_retry(app, monkeypatch):
    """CR-01: an attempt that returns immediately because a concurrent save holds the
    reschedule lock touched no job at all, so it must not reduce what a later attempt
    is allowed to do."""
    scheduler = _make_real_scheduler()
    lock_acquired = False
    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            list_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(list_id, SMOKE_CRON)

            lock_acquired = sched._reschedule_lock.acquire(blocking=False)
            assert lock_acquired is True

            # Many no-op ticks while the "concurrent save" holds the lock.
            for _ in range(10):
                sched._tz_poll_tick()
            assert tz_key(scheduler.timezone) == SCHEDULER_TZ

            sched._reschedule_lock.release()
            lock_acquired = False

            sched._tz_poll_tick()
            assert tz_key(scheduler.timezone) == "Asia/Tokyo"
    finally:
        if lock_acquired:
            sched._reschedule_lock.release()
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_reschedule_db_failure_leaves_timezone_unapplied_for_next_poll(app, monkeypatch):
    """CR-01: when the schedule query fails, scheduler.timezone must stay untouched so the
    poll still sees a divergence and retries instead of believing it converged."""
    scheduler = _make_real_scheduler()

    class _BoomQuery:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            raise OperationalError("SELECT", {}, Exception("database is locked"))

    class _BoomList:
        query = _BoomQuery()
        id = List.id
        schedule_cron = List.schedule_cron
        is_active = List.is_active

    try:
        scheduler.start(paused=True)
        monkeypatch.setattr(sched, "_scheduler", scheduler)
        monkeypatch.setattr(sched, "_app", app)

        with app.app_context():
            _set_app_timezone("Asia/Tokyo")
            list_id = _make_list_row(SMOKE_CRON)
            sched.schedule_list(list_id, SMOKE_CRON)

            monkeypatch.setattr(sched, "List", _BoomList)
            assert sched.reschedule_all_lists("Asia/Tokyo") == (0, 0)
            assert tz_key(scheduler.timezone) == SCHEDULER_TZ, "timezone must not be committed"
            assert sched.reschedule_is_incomplete() is True

            monkeypatch.setattr(sched, "List", List)
            sched._tz_poll_tick()

            assert tz_key(scheduler.timezone) == "Asia/Tokyo"
            assert sched.reschedule_is_incomplete() is False
            job = scheduler.get_job(f"list_{list_id}")
            assert job is not None
            assert job.next_run_time > datetime.now(timezone.utc)
    finally:
        time_utils.invalidate_app_timezone_memo()
        if scheduler.running:
            scheduler.shutdown(wait=False)
