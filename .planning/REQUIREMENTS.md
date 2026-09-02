# Requirements: Listarr v2.2 — Settings, Import Control & Maintenance

**Defined:** 2026-09-02
**Core Value:** Lists are the primary domain object — every route, UI decision, and interaction centers on creating, managing, and monitoring list automations.

## v2.2 Requirements

Each maps to a roadmap phase. REQ-IDs continue from prior milestones (GEN-01 was reserved for timezone in v2.1 and is delivered here).

### General Settings

- [ ] **GEN-01**: User can set the application timezone from a searchable, region-grouped IANA list on a "General" settings tab, with a "System default (TZ)" entry that persists as no override
- [ ] **GEN-03**: The persisted timezone is the scheduler's source of truth — resolution order is DB value → live scheduler → `TZ` env var → UTC — applied in the single `_get_scheduler_timezone()` helper
- [ ] **GEN-04**: Changing the timezone live-reschedules every scheduled list; existing cron triggers are rebuilt (not mutated) so wall-clock run times move to the new zone without firing a retroactive catch-up run
- [ ] **GEN-05**: A timezone change made on a non-scheduler gunicorn worker converges on the scheduler worker within ~60s via a housekeeping poll job
- [ ] **GEN-06**: The General tab shows a live "current time in <zone>" preview beside the selector, and saving shows a success toast naming how many scheduled lists were rescheduled
- [ ] **GEN-07**: An invalid or unresolvable stored timezone never blocks app or scheduler startup — it falls back to `TZ` env / UTC and surfaces a warning
- [ ] **GEN-08**: Activity and list views render UTC timestamps in the configured application timezone (same resolver as the scheduler), not the container `TZ` env var

### Sonarr Monitor Mode

- [ ] **MON-01**: User can choose a Sonarr monitor mode per TV list — All episodes / First season / Latest season / Pilot only / None — shown only for Sonarr (TV) lists
- [ ] **MON-02**: Monitor mode is a Sonarr Import Default (default: All episodes) with a per-list tri-state override, mirroring the existing `override_season_folder` pattern; existing lists are unaffected on upgrade
- [ ] **MON-03**: The selected mode is sent to Sonarr as `addOptions.monitor` using an exact camelCase enum token from a constant map (verified against the target Sonarr v3 schema at build time), on both the single-add and bulk-import payload paths
- [ ] **MON-04**: Monitor mode applies only when Listarr adds a series — already-imported Sonarr series are never re-modified
- [ ] **MON-05**: The new `lists` column is added via an idempotent startup DDL helper (no Alembic in this project); all create paths (custom, preset, edit) carry the field
- [ ] **MON-06**: `None` monitor mode does not trigger a search on add; each mode's search behaviour is explicit and tested via read-back of `seasons[].monitored`
- [ ] **MON-07**: Resolves GitHub issue #34

### Dependency & Docker Maintenance

- [ ] **MNT-01**: `pip-audit` passes on the updated lockfile, with any unfixable transitive CVE covered by a justified `--ignore-vuln` allowlist entry and a tracking issue
- [ ] **MNT-02**: All runtime dependencies bumped to latest patch/minor; majors taken only where a CVE forces it — `cryptography` 46→50 lands as its own reviewed change validated by `pytest -m encryption`
- [ ] **MNT-03**: Currently-unpinned dependencies are given explicit pins (`Werkzeug`, `bcrypt`, `cachetools`, and any others surfaced by `pip freeze` vs `requirements.txt`); `tzdata` is added as a runtime dependency
- [ ] **MNT-04**: The Docker base image is pinned to `python:3.11-alpine` at a specific `@sha256:` digest; the built image is smoke-tested (gunicorn boots, scheduler worker inits, entrypoint privilege drop, `ZoneInfo("America/New_York")` resolves, an encryption round-trip, an end-to-end import)
- [ ] **MNT-05**: `.pre-commit-config.yaml` hook revisions (`ruff`, `bandit`) are pinned in lockstep with `requirements-dev.txt`; `pre-commit run --all-files` passes
- [ ] **MNT-06**: Full CI is green — lint, test (coverage ≥ 60% gate, non-negative delta), security, and the Docker build validation job — with the validation image built using `--pull`

## Future Requirements

Deferred beyond v2.2. Tracked, not in this roadmap.

### General Settings

- **GEN-02**: User-configurable application name
- Per-list timezone override; browser timezone auto-detect; offset-prefixed timezone labels `(UTC−05:00) …`

### Sonarr Monitor Mode

- Retroactive monitor re-apply to already-imported Sonarr series (season `PUT` on existing series)
- Additional Sonarr monitor enums (`future`, `missing`, `recent`, monitor/unmonitor specials)
- Per-run monitor-mode override in the "Run now" flow

### Infrastructure

- Migrate the Docker base image from Alpine (musl) to Debian slim (glibc) — own phase with a full container smoke test
- Tag management UI (Radarr/Sonarr)
- Trakt/IMDB/third-party list source integration (research required)
- TMDB URL import (research required)

## Out of Scope

| Feature | Reason |
|---------|--------|
| APScheduler 4.x upgrade | Incompatible rewrite; 3.x is maintained and sufficient |
| New datetime library (pendulum/arrow) / Sonarr SDK | stdlib `zoneinfo` and a single HTTP field cover the need; added CVE surface |
| Retroactive monitor changes to existing Sonarr series | Explicitly deferred — new-adds only per issue #34 discussion |
| Alpine → slim migration in v2.2 | libc/distro switch with real regression risk; deferred to its own phase |
| Per-run import-setting overrides | Inconsistent with Listarr's default-then-override pattern for every other import setting |
| Real-time WebSocket scheduler status | Complexity not justified for current user base (carried from prior milestones) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MNT-03 (partial — `tzdata` runtime dep + APScheduler/SQLAlchemy scheduler/ORM pins) | Phase 12 | Complete (12-02) |
| MON-01 | Phase 13 | Pending |
| MON-02 | Phase 13 | Pending |
| MON-03 | Phase 13 | Pending |
| MON-04 | Phase 13 | Pending |
| MON-05 | Phase 13 | Pending |
| MON-06 | Phase 13 | Pending |
| MON-07 | Phase 13 | Pending |
| GEN-01 | Phase 14 | Pending |
| GEN-03 | Phase 14 | Pending |
| GEN-04 | Phase 14 | Pending |
| GEN-05 | Phase 14 | Pending |
| GEN-06 | Phase 14 | Pending |
| GEN-07 | Phase 14 | Pending |
| GEN-08 | Phase 14 | Pending |
| MNT-01 | Phase 15 | Pending |
| MNT-02 | Phase 15 | Pending |
| MNT-03 (remainder — `Werkzeug` / `bcrypt` / `cachetools` + any other unpinned deps) | Phase 15 | Pending |
| MNT-04 | Phase 15 | Pending |
| MNT-05 | Phase 15 | Pending |
| MNT-06 | Phase 15 | Pending |

**Coverage:**
- v2.2 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

MNT-03 is split across two phases: Phase 12 delivers the `tzdata` runtime dependency plus the scheduler/ORM-relevant pins (APScheduler, SQLAlchemy) that must be settled before the timezone work; Phase 15 delivers the remaining explicit pins for currently-unpinned dependencies once feature code has settled. All other requirements map to exactly one phase.

---
*Requirements defined: 2026-09-02*
*Last updated: 2026-09-02 — roadmap created (Phases 12–15), MNT-03 split finalised*
