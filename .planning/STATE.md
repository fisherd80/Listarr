---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: — Bug Fixes & UX Polish
status: executing
last_updated: "2026-05-15T10:29:27.536Z"
last_activity: 2026-05-15
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 5
  completed_plans: 4
---

# Session State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-12)

**Core value:** Lists are the primary domain object — every route, UI decision, and interaction centers on creating, managing, and monitoring list automations.
**Current focus:** Phase 10 — activity-page-polish

## Position

**Milestone:** v2.1 — Bug Fixes & UX Polish
**Phase:** 10
**Status:** Executing Phase 10
**Plans:** 2 plans in 1 wave (Wave 1: backend API contract, frontend badge + clear-all polish)
**Last activity:** 2026-05-15

## Progress Bar

```
Phase 8  [x] Scheduler Timezone Fix
Phase 9  [~] Cron Expression UX
Phase 10 [~] Activity Page Polish
Phase 11 [ ] Preset Preview, Settings Layout & Remaining Bugs
```

## Accumulated Context

### Key Design Decisions (carried forward)

- Semantic CSS token naming: `bg-{layer}-{role}`, `text-{role}`, `border-{role}` — all new UI uses tokens, never raw Tailwind palette classes
- RGB format for CSS custom properties (`--color-primary: 45 212 191`) enables Tailwind opacity modifiers (bg-primary/10)
- teal-800 (`#115e59`) used for WCAG AA contrast on light backgrounds; bare bg-primary fails AA against white
- Toast-only feedback for AJAX actions — no persistent status spans in templates
- applyToggleStyle() owns toggle border state via inline JS style — CSS specificity conflicts make declarative border unreliable on toggles
- escapeHtml() required at all innerHTML boundaries for data-driven labels (generateServiceBadge pattern)
- Session-scoped test fixtures with per-test table truncation (children before parents) for DB isolation
- Activity rows now receive `list_deleted` from `GET /api/activity`; true means `job.list_id` is non-null and the `List` lookup is missing
- For orphaned-list tests that must preserve stale `Job.list_id`, use bulk `List.query.filter_by(id=list_id).delete(synchronize_session=False)` instead of ORM instance deletion

### v2.1 Phase Notes

- Phase 8 (BUG-01) is a prerequisite for all other phases — must land first
- Phases 9, 10, 11 are independent of each other and can be planned/executed in any order after Phase 8
- All features use existing backend endpoints; no new dependencies required
- Run `./scripts/build-css.sh` after every template change (Phases 9, 10, 11 all touch HTML templates)
- Every AJAX POST must include `X-CSRFToken` header — follow the pattern in `jobs.js`
- Settings tab active state is hardcoded in `settings.html` — Phase 11 INT-01 requires careful atomic CSS class changes

## Session Log

- 2026-05-15: Phase 10 Plan 01 executed; `GET /api/activity` now emits `list_deleted`; 36 activity route tests and ruff checks passed

- 2026-05-01: v2.0 milestone archived — ROADMAP.md collapsed, PROJECT.md evolved, RETROSPECTIVE.md created
- 2026-05-12: v2.1 milestone started — Bug Fixes & UX Polish
- 2026-05-12: Roadmap created — 4 phases (8-11), 9 requirements mapped, ready for phase planning
- 2026-05-12: Phase 8 planned — 2 plans (Wave 0: test stubs, Wave 1: scheduler.py fix), BUG-01 covered, verification passed
- 2026-05-13: Phase 8 UAT complete — 3/3 passed (17 scheduler tests green, cron validation UTC offset confirmed, next-run display correct in America/New_York)
- 2026-05-13: Phase 9 planned — 1 plan (Wave 1: 3 templates + create.js + CSS rebuild), BUG-04 + CRON-01 + CRON-02 covered, verification passed
- 2026-05-13: Phase 9 executed inline — advanced cron toggles removed, crontab.guru links added, hide/reset branch fixed, AbortController validation added; ruff clean and 592 tests passed
