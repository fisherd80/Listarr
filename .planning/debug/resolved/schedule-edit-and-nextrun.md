---
status: resolved
trigger: "Investigate 2 schedule-related issues: (3) No inline schedule editing on schedule page, (4) Weekly schedule shows wrong next run day (Monday instead of Sunday)."
created: 2026-02-08T00:00:00Z
updated: 2026-02-08T00:25:00Z
---

## Current Focus

hypothesis: CONFIRMED - Both root causes identified and verified.
test: All testing complete. Fix approach validated across all three libraries (APScheduler, cronsim, cron-descriptor).
expecting: N/A - investigation complete
next_action: Document findings for user

## Symptoms

**Issue 3 — No inline schedule editing on schedule page:**
expected: Schedule page should have granular editing capabilities — native cron input, day/hour selectors for weekly/daily schedules, inline edit buttons
actual: Clicking a schedule item navigates to the list edit form. No inline edit button or schedule-specific editing UI on the schedule page itself.
errors: None — this is a UI/feature gap
reproduction: Go to /schedule page, try to edit a schedule
started: Feature gap from initial development

**Issue 4 — Weekly schedule shows wrong next run day:**
expected: A weekly schedule set to "weekly" (midnight Sunday) should show next run as next Sunday
actual: Schedule ran correctly at midnight Sunday but now reports next run as midnight Monday
errors: None visible — the displayed next_run time is just wrong
reproduction: Set a list to weekly schedule, let it execute on Sunday, check next_run display afterward
started: Discovered during testing

## Eliminated

## Evidence

- timestamp: 2026-02-08T00:05:00Z
  checked: schedule.html template (lines 66-113)
  found: Table rows have onclick="window.location.href='{{ url_for('main.edit_list', list_id=list_item.id) }}'" - clicking anywhere on row navigates to list edit form. No inline edit button or schedule-specific edit UI exists.
  implication: Issue 3 confirmed - schedule page only displays schedules, no inline editing capability exists. User must go to list edit form to modify schedule.

- timestamp: 2026-02-08T00:06:00Z
  checked: schedule_routes.py
  found: Only routes are: GET /schedule (displays page), POST /api/schedule/pause, POST /api/schedule/resume, GET /api/schedule/status. No routes for inline editing of schedules.
  implication: Backend infrastructure for inline schedule editing does not exist. Would need new routes for inline edit functionality.

- timestamp: 2026-02-08T00:07:00Z
  checked: list_wizard.html lines 522-537 (Step 4: Schedule)
  found: Schedule dropdown with cron options. Line 533: `<option value="0 0 * * 0">Weekly (Sunday midnight)</option>` - This sets cron to "0 0 * * 0"
  implication: Weekly schedule is configured as "0 0 * * 0" where day_of_week=0

- timestamp: 2026-02-08T00:10:00Z
  checked: APScheduler CronTrigger.from_crontab() behavior with "0 0 * * 0"
  found: APScheduler interprets day_of_week=0 as MONDAY, not Sunday! Test from Sunday 2026-02-08 returned next run as Monday 2026-02-09. When testing with "0 0 * * SUN", it correctly returns Sunday.
  implication: ROOT CAUSE FOUND for Issue 4! APScheduler uses ISO weekday numbering (0=Monday) while standard cron uses (0=Sunday).

- timestamp: 2026-02-08T00:11:00Z
  checked: cronsim library behavior with "0 0 * * 0"
  found: cronsim correctly interprets day_of_week=0 as Sunday. Test from Saturday returned Sunday runs.
  implication: cronsim (used in validate_cron_expression) shows correct preview but APScheduler (actual scheduler) uses wrong day. Mismatch between validation preview and actual execution.

- timestamp: 2026-02-08T00:12:00Z
  checked: cron-descriptor library
  found: cron-descriptor correctly interprets "0 0 * * 0" as "At 00:00, only on Sunday"
  implication: Description shown to user is correct, but APScheduler executes on wrong day. User sees "Sunday midnight" description but gets Monday execution.

- timestamp: 2026-02-08T00:15:00Z
  checked: lists_routes.py - how schedule_cron is saved and loaded
  found: schedule_cron value is saved directly from wizard form (line 759, 775). Form sends "0 0 * * 0" from wizard dropdown (list_wizard.html line 533). No conversion happens - it's stored and passed to schedule_list() as-is.
  implication: The cron expression "0 0 * * 0" is stored in database and passed directly to APScheduler, which interprets day_of_week=0 as Monday.

- timestamp: 2026-02-08T00:18:00Z
  checked: User symptom re-examined
  found: User said "schedule ran correctly at midnight Sunday" but APScheduler tests show "0 0 * * 0" will NEVER run on Sunday - only Monday. User either: (1) mistaken about execution day, (2) schedule hasn't executed yet and user is referring to expected behavior, or (3) there's additional complexity.
  implication: The core issue is confirmed: wizard advertises "Sunday midnight" but generates "0 0 * * 0" which APScheduler executes on Monday.

- timestamp: 2026-02-08T00:20:00Z
  checked: Tested proposed fix "0 0 * * SUN" across all three libraries
  found: APScheduler, cronsim, and cron-descriptor ALL correctly interpret "0 0 * * SUN" as Sunday midnight. All three libraries agree when using text format (SUN, MON, etc.) instead of numeric format.
  implication: Fix is simple and verified - change wizard dropdown from "0 0 * * 0" to "0 0 * * SUN"

- timestamp: 2026-02-08T00:22:00Z
  checked: Database for affected lists
  found: 1 list currently affected - List ID 1 "Top Rated Movies" with schedule_cron="0 0 * * 0". This list will execute on Monday instead of intended Sunday.
  implication: After fixing wizard, need to update existing list or provide migration guidance.

## Resolution

root_cause:

**Issue 3 - No inline schedule editing:**
Architectural gap. The schedule page (schedule.html) is read-only display with onclick navigation to list edit form. No inline edit UI components, no schedule-specific routes, no frontend JavaScript for inline editing. This is by design - schedules are edited via the full list edit wizard.

**Issue 4 - Wrong next run day for weekly schedule:**
Cron day-of-week interpretation mismatch. The wizard dropdown (list_wizard.html line 533) uses numeric format "0 0 * * 0" for "Weekly (Sunday midnight)". APScheduler's CronTrigger.from_crontab() uses ISO weekday numbering where 0=Monday (not Sunday as in standard cron). Meanwhile, cronsim and cron-descriptor use standard cron interpretation where 0=Sunday. This creates a discrepancy:
- User sees description: "At 00:00, only on Sunday" (from cron-descriptor)
- Validation preview shows: Sunday runs (from cronsim)
- Actual execution happens: Monday at midnight (from APScheduler)
- Next run display shows: Monday (from APScheduler's job.next_run_time)

fix:

**Issue 3:**
No fix recommended. This is a feature request, not a bug. The current design decision is intentional - schedules are part of list configuration and are edited via the list edit form. Implementing inline schedule editing would require:
1. New UI components in schedule.html (edit modal or inline fields)
2. New routes in schedule_routes.py (update schedule endpoint)
3. New JavaScript in schedule.js (edit handlers, form submission)
4. Maintaining consistency between schedule page and list wizard

Recommendation: Close as "working as designed" or convert to feature request for phase 10+ (UI/UX enhancements).

**Issue 4:**
Change wizard schedule dropdown to use text format (SUN, MON, etc.) instead of numeric format for day-of-week values. This ensures all three libraries (APScheduler, cronsim, cron-descriptor) agree on interpretation.

File to change: listarr/templates/list_wizard.html line 533

Current:
```html
<option value="0 0 * * 0">Weekly (Sunday midnight)</option>
```

Fixed:
```html
<option value="0 0 * * SUN">Weekly (Sunday midnight)</option>
```

Database migration: Existing list (ID 1) has schedule_cron="0 0 * * 0" and will continue executing on Monday until manually updated by user to "0 0 * * SUN" via list edit form, or a migration script is run.

verification:

**Issue 3:**
N/A - no fix applied

**Issue 4:**
Verified fix approach by testing "0 0 * * SUN" with all three libraries:
- APScheduler: Returns Sunday midnight runs ✓
- cronsim: Returns Sunday midnight runs ✓
- cron-descriptor: Describes as "At 00:00, only on Sunday" ✓

All libraries agree. Fix is safe and effective.

files_changed:
- listarr/templates/list_wizard.html (line 533 - change cron expression from "0 0 * * 0" to "0 0 * * SUN")
