# UAT Issues: Phase 2 Plan 5

**Tested:** 2026-01-17
**Source:** .planning/phases/02-list-creation-wizard/02-05-PLAN.md
**Tester:** User via /gsd:verify-work

## Open Issues

[None - all issues resolved]

## Resolved Issues

### UAT-001: Preset flow should skip Step 1

**Discovered:** 2026-01-17
**Phase/Plan:** 02-05
**Severity:** Minor
**Feature:** Preset wizard flow
**Description:** When clicking a preset card, the wizard shows Step 1 but there's no reason to enter Step 1 since the type is already determined by the preset.
**Expected:** Wizard should start at Step 2 for preset flows
**Actual:** Wizard starts at Step 1 with preset info displayed
**Resolution:** Fixed in commit `dc74a0d` - Updated `initWizard()` to skip to Step 2 for preset flows
**Fixed:** 2026-01-17

### UAT-002: Missing season folder checkbox for Sonarr

**Discovered:** 2026-01-17
**Phase/Plan:** 02-05
**Severity:** Major
**Feature:** Import Settings (Step 3)
**Description:** For Sonarr/TV lists, there is no checkbox option for "Season Folder" setting.
**Expected:** Season folder checkbox should be available for Sonarr import settings
**Actual:** Season folder option is missing from the form
**Resolution:** Fixed in commit `15b6404` - Added season_folder field to model, template, JS handlers, and routes
**Fixed:** 2026-01-17

### UAT-003: Name validation treats pre-populated name as missing

**Discovered:** 2026-01-17
**Phase/Plan:** 02-05
**Severity:** Minor
**Feature:** Schedule step (Step 4)
**Description:** When a preset pre-populates the name field (e.g., "Trending Movies"), the validation still shows it as missing/required. Pre-populated name should be accepted.
**Expected:** Pre-populated name should be treated as valid input, only mark as missing if truly empty
**Actual:** Shows validation warning even with pre-populated name
**Resolution:** Fixed in commit `22271db` - Added state sync in populateStep4() and updateNextButtonState() call
**Fixed:** 2026-01-17

### UAT-004: Missing asterisk before "Name" required indicator

**Discovered:** 2026-01-17
**Phase/Plan:** 02-05
**Severity:** Cosmetic
**Feature:** Schedule step (Step 4)
**Description:** The "Missing Name" text doesn't have the asterisk (*) prefix that typically indicates required fields.
**Expected:** Required field indicator should show as "* Name" or "Name *"
**Actual:** Missing the asterisk marker
**Resolution:** Fixed in commit `22271db` - Added asterisk prefix to error message
**Fixed:** 2026-01-17

### UAT-005: Edit mode forces user through full wizard unnecessarily

**Discovered:** 2026-01-17
**Phase/Plan:** 02-05
**Severity:** Major
**Feature:** Edit mode
**Description:** Editing a list requires going through the entire wizard again. For movie lists, only Radarr settings apply; for TV lists, only Sonarr applies. Previous edit form was simpler and preferred.
**Expected:** Consider direct edit form or at least skip irrelevant steps (e.g., service selection)
**Actual:** Must navigate through all wizard steps to make edits
**Resolution:** Fixed in commit `dc74a0d` - Edit mode now starts at Step 2, skipping type selection
**Fixed:** 2026-01-17

### UAT-006: TV genre mapping incorrect with TMDB

**Discovered:** 2026-01-17
**Phase/Plan:** 02-05
**Severity:** Major
**Feature:** Filters step (Step 2) - Custom TV flow
**Description:** Only a couple of TV genres correctly map to TMDB. Most genres don't pull correct results.
**Expected:** All TV genres should map correctly to TMDB TV genre IDs
**Actual:** Most TV genres don't work, only a few correctly map
**Resolution:** Fixed in commit `608cb48` - Implemented separate TMDB_MOVIE_GENRES and TMDB_TV_GENRES with dynamic checkbox population
**Fixed:** 2026-01-17

---

*Phase: 02-list-creation-wizard*
*Plan: 05*
*Tested: 2026-01-17*
*All issues resolved: 2026-01-17*
