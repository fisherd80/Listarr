# Roadmap: Listarr

## Milestones

- ✅ **v2.0 UI/UX Redesign & Code Optimization** — Phases 1–7 + 04.1, 04.2, 05.1, 06.1, 07.1, 07.2 (shipped 2026-05-01) → [Archive](milestones/v2.0-ROADMAP.md)
- ✅ **v2.1 Bug Fixes & UX Polish** — Phases 8–11 (shipped 2026-05-15) → [Archive](milestones/v2.1-ROADMAP.md)
- 🚧 **v2.2 Settings, Import Control & Maintenance** — Phases 12–15 (planning)

## Phases

<details>
<summary>✅ v2.0 UI/UX Redesign & Code Optimization — SHIPPED 2026-05-01</summary>

- [x] Phase 1: Route Skeleton and Redirects (2/2 plans) — completed 2026-02-26
- [x] Phase 2: Blueprint Consolidation and Test Migration (2/2 plans) — completed 2026-02-26
- [x] Phase 3: Settings Consolidation (4/4 plans) — completed 2026-02-27
- [x] Phase 4: Lists Page and Creation Flows (5/5 plans) — completed 2026-02-27
- [x] Phase 04.1: List table last run and results columns (2/2 plans) — completed 2026-02-28
- [x] Phase 04.2: Edit form UX fixes (3/3 plans) — completed 2026-02-28
- [x] Phase 5: Activity Monitoring and Run Detail (2/2 plans) — completed 2026-03-01
- [x] Phase 05.1: Back button on run detail (1/1 plan) — completed 2026-03-02
- [x] Phase 6: Operational Dark Theme (13/13 plans) — completed 2026-03-13
- [x] Phase 06.1: Dark and light mode audit and fixes (4/4 plans) — completed 2026-03-13
- [x] Phase 7: Test Coverage Completion (5/5 plans) — completed 2026-04-21
- [x] Phase 07.1: Frontend consistency fixes from design review (3/3 plans) — completed 2026-04-29
- [x] Phase 07.2: Security hardening (1/1 plan) — completed 2026-04-29

</details>

<details>
<summary>✅ v2.1 Bug Fixes & UX Polish — SHIPPED 2026-05-15</summary>

- [x] Phase 8: Scheduler Timezone Fix (2/2 plans) — completed 2026-05-12
- [x] Phase 9: Cron Expression UX (1/1 plan) — completed 2026-05-13
- [x] Phase 10: Activity Page Polish (2/2 plans) — completed 2026-05-15
- [x] Phase 11: Preset Preview, Settings Layout & Remaining Bugs (3/3 plans) — completed 2026-05-15

</details>

### 🚧 v2.2 Settings, Import Control & Maintenance (Planning)

**Milestone Goal:** Give users control over application timezone and per-list Sonarr monitoring, and refresh the dependency/runtime baseline — all CI green.

- [ ] **Phase 12: Maintenance Pre-flight** - Green baseline, scheduler/ORM pins stabilized, `tzdata` added
- [ ] **Phase 13: Sonarr Monitor-Mode Selector** - Per-list All/First/Latest/Pilot/None monitoring on series add
- [ ] **Phase 14: Application Timezone** - DB-persisted app timezone as scheduler source of truth with live reschedule
- [ ] **Phase 15: Maintenance Finish** - Bulk dependency bumps, digest-pinned base image, full CI + pre-commit green

## Phase Details

### Phase 12: Maintenance Pre-flight

**Goal**: A green, reproducible dependency baseline with the scheduler/ORM stack stabilized and IANA timezone data available in the container, so the timezone feature is built without mid-feature dependency churn.
**Depends on**: Nothing (first phase of v2.2; continues numbering from Phase 11)
**Requirements**: MNT-03 (partial — `tzdata` runtime dep + scheduler/ORM-relevant pins)
**Success Criteria** (what must be TRUE):

  1. `pip-audit`, `ruff check .`, `ruff format --check .`, `pytest`, and `bandit -r listarr -ll` all pass on the lockfile and the known-clean state is recorded in the phase notes.
  2. `APScheduler` is pinned at the latest 3.11.x patch and `SQLAlchemy` at the latest 2.0.x patch (still `<4` / `<2.1`), changelogs for the crossed range reviewed; full `pytest` stays green and a manual scheduler smoke (create list, schedule, run now) succeeds.
  3. `tzdata` is present in `requirements.txt` as an explicit runtime dependency, and `python -c "from zoneinfo import ZoneInfo; ZoneInfo('America/New_York')"` succeeds against a fresh install of the lockfile.
  4. `Flask-SQLAlchemy` and `cronsim` are confirmed current or bumped to their latest compatible pins.
  5. Test coverage is at or above the 60% CI gate with a non-negative delta.

**Plans**: 6 plans

Plans:
**Wave 1**

- [x] 12-01-PLAN.md — Create 12-NOTES.md evidence artifact and record the pre-change gate snapshot + coverage baseline (D-04/D-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 12-02-PLAN.md — Add the tzdata pin, bump SQLAlchemy/APScheduler/cron-descriptor, write the dependency review table (D-09/D-10/D-10a/D-10b)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 12-03-PLAN.md — Bump cryptography to clear all five pip-audit findings, prove pip-audit green, human-verify the final lockfile diff (D-12/D-16)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 12-04-PLAN.md — Correct the Dockerfile base tag to python:3.11-alpine and settle the image-proof substrate (D-17/D-01)

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 12-05-PLAN.md — Author the real-scheduler + real-ORM integration smoke and run the deprecation canary (D-06/D-07/D-08/D-08a/D-11)

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 12-06-PLAN.md — Docker image proof (ZoneInfo + pip-audit + full pytest in-container) and coverage-delta close-out (D-01/D-04)

### Phase 13: Sonarr Monitor-Mode Selector

**Goal**: Users can choose, per Sonarr TV list, how much of a series Listarr monitors when it adds it — All / First Season / Latest Season / Pilot / None — applied on new adds only, with existing lists unaffected.
**Depends on**: Phase 12
**Requirements**: MON-01, MON-02, MON-03, MON-04, MON-05, MON-06, MON-07
**Success Criteria** (what must be TRUE):

  1. On a Sonarr (TV) list's import settings — in the custom builder, the preset wizard, and the edit form — the user sees a monitor-mode selector (All / First Season / Latest Season / Pilot / None); the control is absent for Radarr (movie) lists.
  2. Monitor mode is a Sonarr Import Default (default: All episodes) with a per-list tri-state override mirroring `override_season_folder`; lists created before the upgrade keep behaving as "All" with no manual action.
  3. When Listarr adds a new series — on both the single-add and scheduled bulk-import payload paths — the exact camelCase `addOptions.monitor` token from a constant map is sent (verified against the target Sonarr v3 schema at build time; "Latest Season" → `lastSeason`), and a read-back of `seasons[].monitored` matches the selected mode for all five options.
  4. Re-running a list never modifies monitoring on series already present in Sonarr; the `lists.sonarr_monitor_mode` column is added to a pre-v2.2 database via an idempotent startup DDL helper (no Alembic).
  5. `None` monitor mode adds the series without triggering a search; each mode's search behaviour is explicit and test-covered. GitHub issue #34 is resolved.

**Plans**: TBD
**UI hint**: yes

### Phase 14: Application Timezone

**Goal**: Users can set the application timezone on a new General settings tab; the stored value is the single source of truth for the cron scheduler and for timestamp rendering, and changing it live-reschedules every list without a restart.
**Depends on**: Phase 12 (Phase 13 recommended first as a warm-up for the startup-DDL pattern — not a hard dependency; the two features share no files beyond the settings/lists route modules)
**Requirements**: GEN-01, GEN-03, GEN-04, GEN-05, GEN-06, GEN-07, GEN-08
**Success Criteria** (what must be TRUE):

  1. A new "General" settings tab presents a searchable, region-grouped IANA timezone list with a "System default (TZ)" entry that persists as no override (NULL) in a new `AppConfig` singleton table, alongside a live "current time in <zone>" preview beside the selector.
  2. `_get_scheduler_timezone()` resolves in the order DB value → live scheduler → `TZ` env → UTC as the one helper every call site uses; an invalid or unresolvable stored timezone falls back safely and surfaces a warning without ever blocking app or scheduler startup.
  3. Saving a new timezone rebuilds every scheduled list's cron trigger (rebuilt, not mutated) so wall-clock run times move to the new zone with no retroactive catch-up run, and the user sees a success toast naming how many scheduled lists were rescheduled.
  4. A timezone change saved on a non-scheduler gunicorn worker converges on the scheduler worker within ~60s via a housekeeping poll job.
  5. Activity and list views render UTC timestamps through the same resolver as the scheduler (the configured application timezone), not the container `TZ` env var.

**Plans**: TBD
**UI hint**: yes

### Phase 15: Maintenance Finish

**Goal**: The full dependency tree, Docker base image, and CI/pre-commit tooling reflect the shipped v2.2 state — audited, pinned by digest, and fully green.
**Depends on**: Phase 14 (and Phase 13) — runs after feature code has settled so the image and lockfile reflect shipped state.
**Requirements**: MNT-01, MNT-02, MNT-03 (remainder — `Werkzeug` / `bcrypt` / `cachetools` and any other unpinned deps), MNT-04, MNT-05, MNT-06
**Success Criteria** (what must be TRUE):

  1. All runtime dependencies are at latest patch/minor with majors taken only where a CVE forces it; `cryptography` 46→50 lands as its own reviewed change validated by `pytest -m encryption`.
  2. Every previously-unpinned dependency (`Werkzeug`, `bcrypt`, `cachetools`, and any others surfaced by `pip freeze` vs `requirements.txt`) has an explicit `==` pin.
  3. `pip-audit` passes on the updated lockfile, with any unfixable transitive CVE covered by a justified `--ignore-vuln` allowlist entry plus a tracking issue.
  4. The Docker base image is pinned to `python:3.11-alpine` at a specific `@sha256:` digest (deliberately not a slim migration — that is deferred), and the built image passes a smoke test: gunicorn boots, scheduler worker inits, entrypoint privilege drop works, `ZoneInfo("America/New_York")` resolves, an encryption round-trip succeeds, and an end-to-end import runs.
  5. `.pre-commit-config.yaml` hook revisions for `ruff` and `bandit` are pinned in lockstep with `requirements-dev.txt`, `pre-commit run --all-files` passes, and full CI (lint, test with coverage ≥ 60% and non-negative delta, security, Docker build validation built with `--pull`) is green.

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 12 → 13 → 14 → 15

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 12. Maintenance Pre-flight | v2.2 | 2/6 | In Progress|  |
| 13. Sonarr Monitor-Mode Selector | v2.2 | 0/TBD | Not started | - |
| 14. Application Timezone | v2.2 | 0/TBD | Not started | - |
| 15. Maintenance Finish | v2.2 | 0/TBD | Not started | - |
