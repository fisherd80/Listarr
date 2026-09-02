---
phase: 12-maintenance-pre-flight
plan: 02
subsystem: infra
tags: [dependencies, requirements-txt, tzdata, zoneinfo, apscheduler, sqlalchemy, cron-descriptor, pip]

# Dependency graph
requires:
  - phase: 12-01
    provides: 12-NOTES.md evidence artifact with the pre-change baseline (coverage 73.29% at 9e89849, five-gate snapshot)
provides:
  - "tzdata==2026.3 as an explicit runtime pin in requirements.txt (# Scheduler block)"
  - "Settled scheduler/ORM pin set: SQLAlchemy==2.0.52, APScheduler==3.11.3, cron-descriptor==2.1.0"
  - "Written dependency review table (12-NOTES.md section 2) with per-bump changelog summaries and two reviewed no-ops"
affects: [12-03, 12-04, 12-05, 12-06, phase-14-application-timezone]

# Tech tracking
tech-stack:
  added:
    - "tzdata==2026.3 (IANA tz database for zoneinfo on Windows / Alpine musl)"
    - "typing_extensions (new runtime transitive pulled by cron-descriptor 2.1.0; not yet explicitly pinned — Phase 15)"
  patterns:
    - "Exact == pins for all runtime deps; <2.1 / <4 major boundaries are prose rationale in 12-NOTES.md, never range operators (D-09)"
    - "Every crossed changelog range summarised in writing whether or not a bump happened (D-10)"

key-files:
  created: []
  modified:
    - "requirements.txt"
    - ".planning/phases/12-maintenance-pre-flight/12-NOTES.md"

key-decisions:
  - "tzdata pinned exact ==2026.3 despite being a rolling YYYY.n data release; accepted future manual bumps over a >= range (D-09/D-10b)"
  - "Flask-SQLAlchemy==3.1.1 and cronsim==2.7 left untouched — already latest, recorded as reviewed no-ops (D-10)"
  - "cryptography left at 46.0.7 — deliberately deferred to plan 12-03 (D-16)"

patterns-established:
  - "Pattern: dependency review table columns Package | Pre-Phase-12 pin | Latest | Checked | Action | Changelog summary, one row per reviewed package"

requirements-completed: [MNT-03]

# Metrics
duration: ~40min
completed: 2026-09-02
---

# Phase 12 Plan 02: Scheduler/ORM Pin Set + tzdata Summary

**Added `tzdata==2026.3` as an explicit runtime pin, bumped SQLAlchemy 2.0.46→2.0.52 / APScheduler 3.11.2→3.11.3 / cron-descriptor 2.0.6→2.1.0, and recorded a six-row dependency review table with per-bump changelog analysis in 12-NOTES.md — full suite stayed 599 passed at 73.29% coverage.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-02T15:25:00Z
- **Completed:** 2026-09-02T16:03:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `tzdata==2026.3` declared in the `# Scheduler` block of `requirements.txt` under an explanatory `zoneinfo` comment — makes `zoneinfo.ZoneInfo(...)` resolvable on Windows / Alpine musl for the Phase 14 timezone feature.
- Scheduler/ORM pin set frozen inside the `<2.1` / `<4` boundaries: `SQLAlchemy==2.0.52`, `APScheduler==3.11.3`, `cron-descriptor==2.1.0`; `Flask-SQLAlchemy==3.1.1` and `cronsim==2.7` confirmed already-latest and recorded as reviewed no-ops.
- `12-NOTES.md` section 2 filled with a Markdown review table (six rows) plus per-bump changelog prose naming the actual consumed surface (`TypeDecorator` / `cache_ok`, `CronTrigger.from_crontab` / `next_run_time`, `get_description`), the new `typing_extensions` transitive, the tzdata rolling-release caveat, and a D-02 verification-posture paragraph.
- All PyPI latest versions re-verified at execution time (2026-09-02) — all matched the 12-RESEARCH.md verdicts exactly.
- Post-bump gates green: `599 passed`, coverage `TOTAL 73.29%` (identical to baseline), `ruff check .`, `ruff format --check .`, `bandit -r listarr -ll` all exit 0.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the tzdata runtime pin** - `7f95081` (chore)
2. **Task 2: Bump the scheduler and ORM pins** - `922528a` (chore)
3. **Task 3: Write the dependency review table into 12-NOTES.md** - `3a8e164` (docs)

## Files Created/Modified
- `requirements.txt` - Added `tzdata==2026.3` + comment (2 lines); bumped `SQLAlchemy`, `APScheduler`, `cron-descriptor`; `Flask-SQLAlchemy` / `cronsim` / `cryptography` untouched.
- `.planning/phases/12-maintenance-pre-flight/12-NOTES.md` - Section 2 dependency review table + D-02 posture paragraph; section 5 marked "no non-mechanical changes required" for plan 12-02.

## Decisions Made
- **Exact `==` pin for `tzdata`** despite it being a rolling `YYYY.n` data release — a `>=` range is forbidden by D-09/D-10b. Future IANA updates require a manual bump (noted in the table).
- **`Flask-SQLAlchemy` / `cronsim` no bump** — both already newest on PyPI as of 2026-09-02; recorded "already current — no bump" per D-10 rather than churning versions.
- **`cryptography` deliberately not touched** — the `pip-audit` RED on `cryptography==46.0.7` is plan 12-03's dedicated reviewed change (D-16). This plan's `pip-audit` state is unchanged and still RED, as expected.

## Deviations from Plan

None - plan executed exactly as written. All three re-verified latest versions matched the plan's declared targets; no bump broke a test, so no call-site changes and no `## 5. Non-mechanical Change Log` entries beyond the explicit "none required" marker.

## Issues Encountered
- `pytest --timeout=30` (from the plan's fast-inner-loop command, mirroring the pre-push hook) failed because `pytest-timeout` is not in `requirements-dev.txt` and the host is a slow global Python 3.14 install with no project venv. Resolved by running the unit suite without `--timeout` (matching the 12-01 baseline methodology, which also ran without it) — `252 passed`. Full suite subsequently ran clean: `599 passed`.
- Bare `pip-audit` remains RED on `cryptography` — expected and out of scope for this plan (12-03 / D-16).

## Next Phase Readiness
- `requirements.txt` scheduler/ORM/tz surface is frozen and ready for the Phase 14 timezone work.
- Plan 12-03 owns the `cryptography==50.0.1` bump to clear `pip-audit` (D-16) and will add its own row to the 12-NOTES.md section 2 table.
- Plan 12-05 owns the deprecation canary against this now-bumped stack (section 3).
- Plan 12-06 owns the authoritative Docker musl fresh-install proof of the `tzdata` add (section 6) and the coverage-delta check (section 7).
- New transitive `typing_extensions` (from `cron-descriptor 2.1.0`) is recorded for the Phase 15 pin sweep so it is not treated as a mystery dependency.

## Self-Check: PASSED

- `requirements.txt` contains `tzdata==2026.3` (line 34), `SQLAlchemy==2.0.52` (line 6), `APScheduler==3.11.3` (line 30), `cron-descriptor==2.1.0` (line 32); `Flask-SQLAlchemy==3.1.1` and `cronsim==2.7` byte-identical to pre-phase; `cryptography==46.0.7` unchanged.
- `12-NOTES.md` section `## 2. Dependency Review Table` present with six rows + `typing_extensions` + "already current" + D-02 posture paragraph.
- Commits `7f95081`, `922528a`, `3a8e164` all present in `git log`.

---
*Phase: 12-maintenance-pre-flight*
*Completed: 2026-09-02*
