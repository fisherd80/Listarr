# Roadmap: Listarr

## Milestones

- ✅ **v2.0 UI/UX Redesign & Code Optimization** — Phases 1–7 + 04.1, 04.2, 05.1, 06.1, 07.1, 07.2 (shipped 2026-05-01) → [Archive](milestones/v2.0-ROADMAP.md)
- 🔄 **v2.1 Bug Fixes & UX Polish** — Phases 8–11 (in progress)

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

---

## Milestone: v2.1 — Bug Fixes & UX Polish

- [x] **Phase 8: Scheduler Timezone Fix** — Resolve the cron day-offset bug in the APScheduler backend
- [ ] **Phase 9: Cron Expression UX** — Remove redundant cron toggle and add live preview and crontab.guru link
- [ ] **Phase 10: Activity Page Polish** — Add Clear All action and Deleted badge for orphaned activity rows
- [ ] **Phase 11: Preset Preview, Settings Layout & Remaining Bugs** — Fix preset list preview, relocate Import Defaults, and fix the GitHub version link

---

## Phase Details

### Phase 8: Scheduler Timezone Fix
**Goal**: Cron jobs fire at the correct time by passing the scheduler's configured timezone to CronTrigger
**Depends on**: Nothing (first phase of v2.1)
**Requirements**: BUG-01
**Success Criteria** (what must be TRUE):
  1. A cron job configured for Monday at 9:00 AM in the scheduler's timezone fires on Monday at 9:00 AM, not offset to Tuesday or another day
  2. The "next run" time displayed in the UI matches the configured cron expression when evaluated against the scheduler's timezone
  3. The CronSim fallback used to calculate next-run previews uses the same timezone as the live scheduler, so preview and actual fire time agree
**Plans**: 2 plans
Plans:
- [x] 08-01-PLAN.md — Add TestSchedulerTimezone class (5 RED tests) to test_scheduler.py
- [x] 08-02-PLAN.md — Add _get_scheduler_timezone() helper and fix 3 call sites in scheduler.py

### Phase 9: Cron Expression UX
**Goal**: Users entering a custom cron expression see a live human-readable description and a direct link to crontab.guru, with no redundant toggle cluttering the interface
**Depends on**: Phase 8
**Requirements**: BUG-04, CRON-01, CRON-02
**Success Criteria** (what must be TRUE):
  1. Selecting "Custom (cron expression)" frequency reveals the cron input directly — no secondary "Advanced Cron Expression" toggle button exists
  2. As the user types a valid cron expression, a human-readable description (e.g. "Every Monday at 9:00 AM") appears below the input within one second, without requiring form submission
  3. An invalid or incomplete cron expression shows a clear error description in place of the human-readable preview, not a silent blank
  4. A "crontab.guru" link is visible adjacent to the custom cron input whenever the Custom frequency option is selected
**Plans**: 1 plan
Plans:
- [x] 09-01-PLAN.md — Remove toggle buttons + add crontab.guru help links (3 templates) + fix dead branch + add AbortController (create.js) + CSS rebuild

### Phase 10: Activity Page Polish
**Goal**: Users can clear all historical run records in one confirmed action, and activity rows for deleted lists display a "Deleted" badge rather than a broken or missing service badge
**Depends on**: Phase 8
**Requirements**: ACT-01, BUG-03
**Success Criteria** (what must be TRUE):
  1. A "Clear All" button is present on the activity page; clicking it shows a confirmation dialog before acting
  2. After confirming, all historical activity records are removed and the activity table shows an empty state without requiring a page reload
  3. Activity rows whose associated list has been deleted display a "Deleted" badge in the list/service column, rather than blank space or a broken reference
**Plans**: 2 plans
Plans:
- [x] 10-01-PLAN.md — Add TestGetActivityListDeleted tests (TDD RED then GREEN) + add list_deleted field to GET /api/activity
- [ ] 10-02-PLAN.md — Add Clear All button to jobs.html + clearAllActivity() to jobs.js + Deleted badge branch in renderJobRow() + CSS rebuild

### Phase 11: Preset Preview, Settings Layout & Remaining Bugs
**Goal**: The preset creation wizard shows a preview panel before confirmation, Import Defaults settings sit beside their respective service connection blocks, and the GitHub version link resolves to the correct release tag
**Depends on**: Phase 8
**Requirements**: BUG-02, INT-01, BUG-05
**Success Criteria** (what must be TRUE):
  1. Selecting a preset in the Create List wizard displays a preview panel showing the preset's name, description, and expected results before the user confirms creation
  2. On the Settings page, the Radarr Import Defaults section appears directly adjacent to the Radarr connection block, and Sonarr Import Defaults appears directly adjacent to the Sonarr connection block
  3. The version link in the UI navigates to the correct GitHub release or tag page for the running version, not a 404 or generic repository page
**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 8. Scheduler Timezone Fix | 2/2 | Complete | 2026-05-12 |
| 9. Cron Expression UX | 1/1 | Pending verification | - |
| 10. Activity Page Polish | 1/2 | In Progress | - |
| 11. Preset Preview, Settings Layout & Remaining Bugs | 0/TBD | Not started | - |
