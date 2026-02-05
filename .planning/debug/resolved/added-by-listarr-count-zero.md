---
status: resolved
trigger: "Dashboard Radarr/Sonarr cards 'Added by Listarr' count always shows '0' when it should show actual count"
created: 2026-02-05T00:00:00Z
updated: 2026-02-05T00:05:00Z
---

## Current Focus

hypothesis: CONFIRMED - Early return statements in _calculate_radarr_stats() and _calculate_sonarr_stats() prevent added_by_listarr calculation
test: Code analysis confirmed the bug - early returns bypass the count calculation
expecting: Moving added_by_listarr calculation before early returns will fix the issue
next_action: COMPLETE - Fix applied and verified

## Symptoms

expected: Radarr/Sonarr cards in the dashboard should show the count of items that were added by Listarr. Both automatic updates and manual refresh should work.
actual: The "Added by Listarr" count always shows "0" on the cards
errors: No visible errors in browser console or logs
reproduction: Always happens - the count is 0 on every page load
started: Was working before, broke recently

## Eliminated

## Evidence

- timestamp: 2026-02-05T00:00:30Z
  checked: dashboard_cache.py _calculate_radarr_stats() function
  found: Lines 82-83 return early if Radarr not configured, BEFORE lines 140-163 which calculate added_by_listarr
  implication: If service not configured, the count calculation never runs

- timestamp: 2026-02-05T00:00:45Z
  checked: dashboard_cache.py _calculate_sonarr_stats() function
  found: Same pattern - lines 195-196 return early before lines 254-276 which calculate added_by_listarr
  implication: Both Radarr and Sonarr have the same bug

- timestamp: 2026-02-05T00:01:00Z
  checked: Code flow analysis
  found: The added_by_listarr count is database-only (summing Job.items_added from completed jobs). It should NOT depend on whether the external service (Radarr/Sonarr) is currently online or configured.
  implication: The count calculation should happen BEFORE the early returns for "not configured" status

- timestamp: 2026-02-05T00:03:00Z
  checked: Applied fix and ran tests
  found: All 38 dashboard route tests pass, all 18 integration tests pass
  implication: Fix is correct and no regressions

## Resolution

root_cause: In dashboard_cache.py, the _calculate_radarr_stats() and _calculate_sonarr_stats() functions have early return statements that return when the service is not configured. However, the added_by_listarr calculation comes AFTER these early returns, so it never executes when the service is not configured. The added_by_listarr count should be calculated regardless of service configuration since it's purely database data (summing Job.items_added from completed jobs).

fix: Moved the added_by_listarr calculation to the BEGINNING of both _calculate_radarr_stats() and _calculate_sonarr_stats() functions, before any early return statements. This ensures the count is always calculated regardless of whether the external service is configured or online.

verification: All 38 tests in tests/routes/test_dashboard_routes.py pass (including 4 added_by_listarr specific tests). All 18 tests in tests/integration/test_dashboard_integration.py pass.

files_changed:
  - listarr/services/dashboard_cache.py
