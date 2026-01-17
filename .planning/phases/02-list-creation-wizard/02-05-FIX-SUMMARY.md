# Summary: 02-05-FIX

**Phase:** 02-list-creation-wizard
**Plan:** 02-05-FIX
**Completed:** 2026-01-17

## What Was Built

Fixed 6 UAT issues discovered during user acceptance testing of the List Creation Wizard (Phase 2, Plan 5).

### Issues Fixed

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| UAT-001 | Minor | Preset flow unnecessarily showed Step 1 | Skip to Step 2 for presets |
| UAT-002 | Major | Missing season folder checkbox for Sonarr | Added full season_folder support |
| UAT-003 | Minor | Pre-populated names failed validation | Sync state after populating input |
| UAT-004 | Cosmetic | Missing asterisk on required field error | Added asterisk prefix |
| UAT-005 | Major | Edit mode forced full wizard navigation | Skip to Step 2 for edit mode |
| UAT-006 | Major | TV genres used wrong TMDB IDs | Implemented separate movie/TV genre maps |

## Key Changes

### Task 1 & 4: Skip Step 1 for Preset and Edit Mode
- **File:** `listarr/static/js/wizard.js`
- Modified `initWizard()` to check `wizardState.editMode` and `wizardState.isPreset`
- Both modes now start directly at Step 2 (Filters)
- Modified `prevStep()` to redirect to `/lists` when going back from Step 2 in these modes
- **Commit:** `dc74a0d`

### Task 2: Season Folder for Sonarr
- **Files:** `lists_model.py`, `list_wizard.html`, `wizard.js`, `lists_routes.py`
- Added `override_season_folder` column to List model (Integer: 1=yes, 0=no, null=default)
- Added checkbox in template (hidden container, shown for Sonarr only)
- Added `handleSeasonFolderChange()` handler with same pattern as other boolean settings
- Updated routes: `wizard_defaults()`, `wizard_submit()`, edit mode data
- **Commit:** `15b6404`

### Task 3: Name Validation and Asterisk
- **Files:** `wizard.js`, `list_wizard.html`
- Added state sync in `populateStep4()`: if input has value but state doesn't, sync from input
- Added `updateNextButtonState()` call after populating Step 4
- Added asterisk prefix to error message: "* Name is required"
- **Commit:** `22271db`

### Task 5: TV Genre Mapping
- **Files:** `wizard.js`, `list_wizard.html`
- Replaced single `TMDB_GENRES` constant with:
  - `TMDB_MOVIE_GENRES` (19 genres: Action, Adventure, Animation, Comedy, etc.)
  - `TMDB_TV_GENRES` (16 genres: Action & Adventure, Sci-Fi & Fantasy, Kids, etc.)
- Added `updateGenreCheckboxes()` function for dynamic checkbox generation
- Called on service selection and when entering Step 2
- Updated `updateSummaryFilters()` to use correct genre map
- Replaced static genre HTML with dynamic container `#genre-checkboxes`
- **Commit:** `608cb48`

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `dc74a0d` | fix | Preset and edit mode skip Step 1 |
| `15b6404` | fix | Add season folder checkbox for Sonarr |
| `22271db` | fix | Sync pre-populated name state and asterisk |
| `608cb48` | fix | Implement dynamic TV/Movie genre mapping |

## Verification

All fixes are ready for re-verification:

1. **Preset flow:** Click preset card → should open at Step 2
2. **Season folder:** TV preset → Step 3 → season folder checkbox visible
3. **Name validation:** Preset → Step 4 → name pre-filled, Create button enabled
4. **Asterisk:** Clear name → error shows "* Name is required"
5. **Edit mode:** Click Edit → opens at Step 2
6. **TV genres:** Custom list → TV → Step 2 → TV-specific genres shown

## Next Steps

- Human verification checkpoint (Task 6 in FIX.md)
- If approved, update STATE.md and ROADMAP.md
- Close fix plan with metadata commit
