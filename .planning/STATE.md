---
gsd_state_version: 1.0
milestone: v2.2
milestone_name: Settings, Import Control & Maintenance
status: executing
last_updated: "2026-09-02T15:03:32.308Z"
last_activity: 2026-09-02
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 6
  completed_plans: 2
  percent: 33
---

# Session State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-02)

**Core value:** Lists are the primary domain object — every route, UI decision, and interaction centers on creating, managing, and monitoring list automations.
**Current focus:** Phase 12 — maintenance-pre-flight

## Position

**Milestone:** v2.2 — Settings, Import Control & Maintenance
**Status:** Ready to execute
**Last activity:** 2026-09-02

## Progress Bar

```
Phase 12 [ ] Maintenance Pre-flight
Phase 13 [ ] Sonarr Monitor-Mode Selector
Phase 14 [ ] Application Timezone
Phase 15 [ ] Maintenance Finish
```

## Accumulated Context

### Key Design Decisions (carried into v2.2 execution)

- Docker: pin `python:3.11-alpine` + `@sha256:` digest — NOT a slim migration (Alpine→slim is explicitly deferred to its own phase)
- Scheduler cross-worker convergence: a ~30–60s poll job on the scheduler worker with acceptable lag — not a config_version watch, not signals, not a shared jobstore
- GEN-01 scope includes the current-time preview, the reschedule toast, and repointing Activity/list UTC→local rendering at the new `_get_scheduler_timezone()` resolver
- "Latest Season" Sonarr enum token: send `lastSeason` (not `latestSeason`, which is `[Obsolete]`); verify against the target instance's v3 schema at build time, keep `latestSeason` recognised only as a legacy alias
- No Alembic — new columns (`lists.sonarr_monitor_mode`) via idempotent `PRAGMA table_info` + `ALTER TABLE` startup DDL helpers next to `_ensure_unique_running_job_index`; new `app_config` table is created by `db.create_all()` and only needs a one-row seed helper
- MNT-03 is split: `tzdata` + APScheduler/SQLAlchemy pins land in Phase 12 (before the timezone work); the rest of the unpinned-dependency pins land in Phase 15
- `cryptography` 46→50 is the one forced major — its own reviewed change validated by `pytest -m encryption`
- Monitor mode gated to `target_service == "sonarr"`; `validate_choice=False` on the form field (mirrors `override_season_folder`); applied on series add only, both single-add and bulk payload builders
- `_get_scheduler_timezone()` new resolution order: DB `AppConfig.timezone` → live `_scheduler.timezone` → `TZ` env → UTC, wrapped in try/except OperationalError, with a short TTL memo (runs on every cron-validation keystroke)
- Carried from v2.1: `misfire_grace_time=3600` (1h) — suppress the catch-up run on tz-driven reschedule (explicit forward `next_run_time` or `misfire_grace_time=1` for that re-add)

### Pending Todos

- Plan Phase 12 (`/gsd:plan-phase 12`)
- Phase 14 (GEN-01) flagged for `--research-phase` during planning: verify APScheduler 3.11 `configure(timezone=)` does not rewrite existing triggers; confirm the poll-job design against `scheduler.py` internals and `_load_schedules_from_db()`; confirm Activity/list UTC→local render path
- Phase 13: verify `/api/v3/series/import` (bulk) honours `addOptions.monitor` against a real Sonarr; fall back to per-series POST for non-`all` modes if it drops the field
- Record the Docker base-image decision (Alpine-pin, confirmed) before Phase 15 planning

## Session Log

- 2026-05-20: v2.1 milestone archived — ROADMAP.md collapsed, PROJECT.md evolved, git tag v2.1.0 created
- 2026-09-02: v2.2 milestone started; requirements defined (20 reqs: GEN, MON, MNT)
- 2026-09-02: v2.2 roadmap created — Phases 12–15, 100% requirement coverage, MNT-03 split (Phase 12 / Phase 15) finalised
- 2026-09-02: 12-01 executed — 12-NOTES.md evidence artifact created; pre-change baseline recorded (coverage TOTAL 73.29% at commit 9e89849, five-gate snapshot); pip-audit RED on cryptography==46.0.7 as expected, deferred to 12-03
- 2026-09-02: 12-02 executed — tzdata==2026.3 pinned; SQLAlchemy 2.0.46→2.0.52, APScheduler 3.11.2→3.11.3, cron-descriptor 2.0.6→2.1.0 bumped; Flask-SQLAlchemy/cronsim confirmed already-current; 12-NOTES.md section 2 review table filled. Full suite 599 passed, coverage 73.29% (== baseline), ruff/format/bandit green. No non-mechanical changes.

## Current Position

Phase: 12 (maintenance-pre-flight) — EXECUTING
Plan: 3 of 6
Status: Ready to execute
Last activity: 2026-09-02

## Decisions (Phase 12 execution)

- Phase 12 baseline measured on host Python 3.14.3 (no 3.11 venv on this machine); `pip-audit -r requirements.txt` (5 cryptography findings) is the finding of record, not the bare global-env scan (35 findings, mostly unrelated packages)
- Baseline coverage TOTAL 73.29% at commit 9e89849 is the D-04 comparison target for plan 12-06; interpreter change (3.14 → 3.11-alpine in the Docker proof) may introduce a small delta
- 12-02: scheduler/ORM pins settled at exact `==` (SQLAlchemy 2.0.52, APScheduler 3.11.3, cron-descriptor 2.1.0); tzdata==2026.3 added. Bumps were purely mechanical — no test broke, coverage unchanged at 73.29%. cron-descriptor 2.1.0 pulls a new `typing_extensions` runtime transitive (unpinned — Phase 15 sweep to catch it). tzdata's exact pin means future IANA data releases need manual bumps.
