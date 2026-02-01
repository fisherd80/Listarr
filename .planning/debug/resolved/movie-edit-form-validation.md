---
status: resolved
trigger: "movie-edit-form-validation"
created: 2026-01-31T00:00:00Z
updated: 2026-01-31T00:07:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED
test: researched WTForms SelectField validation behavior
expecting: SelectField validates against choices even when field is missing from POST
next_action: implement fix - either conditionally skip validation or remove field from form for RADARR

## Symptoms

expected: Save form and redirect to lists page
actual: Validation error prevents saving
errors: "Not a valid choice" on override_season_folder - field shouldn't exist/validate for Radarr/movie lists
reproduction: Edit any existing movie list (Radarr type) and click save
started: Broke recently - was working before, likely after Phase 6.1 changes

## Eliminated

## Evidence

- timestamp: 2026-01-31T00:01:00Z
  checked: listarr/forms/lists_forms.py and listarr/routes/lists_routes.py
  found: ListForm (line 69-73) includes override_season_folder field with TRI_STATE_CHOICES validation. The edit_list route (lines 76-219) sets form choices for quality_profile and root_folder dynamically, but override_season_folder uses static TRI_STATE_CHOICES that are ALWAYS validated regardless of service type.
  implication: When editing a Radarr/movie list, the form tries to validate override_season_folder field against TRI_STATE_CHOICES. If the submitted value doesn't match one of the static choices ("", "1", "0"), validation fails with "Not a valid choice" error.

- timestamp: 2026-01-31T00:02:00Z
  checked: listarr/templates/edit_list.html
  found: Lines 108-115 show override_season_folder field is conditionally rendered ONLY for SONARR lists. For RADARR lists, this field is NOT included in the HTML form.
  implication: When a RADARR/movie list form is submitted, the override_season_folder field is missing from POST data because it was never rendered. WTForms validation fails because the field exists in the form class but has no value submitted, and None/missing is not in the valid choices list.

- timestamp: 2026-01-31T00:03:00Z
  checked: git history - commit c188b21
  found: Recent Phase 6.1 commit added validation error feedback to edit_list route (lines 172-181 in lists_routes.py). This surfaces field validation errors that were previously silent. The commit message indicates it fixed Bug #6 where edit save appeared to do nothing when validation failed.
  implication: The override_season_folder validation failure was always happening for RADARR lists, but was silent. Now with error feedback, users see "Not a valid choice" error message, making the bug visible.

- timestamp: 2026-01-31T00:04:00Z
  checked: WTForms documentation and GitHub issues
  found: WTForms SelectField validates all submitted data against choices list. When a field is missing from POST data (not rendered in template), WTForms treats it as invalid and fails validation with "Not a valid choice" error. SelectField has validate_choice parameter that can be set to False to skip this validation.
  implication: The override_season_folder field in ListForm validates against TRI_STATE_CHOICES even when missing from RADARR form submission. Since the field isn't rendered in the template for RADARR lists, it's missing from POST data and fails validation.

## Resolution

root_cause: WTForms SelectField for override_season_folder (lines 69-73 in lists_forms.py) validates against TRI_STATE_CHOICES for all list types. The edit_list.html template only renders this field for SONARR lists (lines 108-115). When editing a RADARR/movie list, the field is not rendered, causing it to be missing from POST data. WTForms SelectField validation then fails with "Not a valid choice" error because the missing field doesn't match any of the valid choices ("", "1", "0").
fix: Added validate_choice=False parameter to override_season_folder SelectField in lists_forms.py (line 73). This disables choice validation for this field, allowing it to accept any value including missing/empty values when the field is not rendered in the template for RADARR lists. The route logic already handles the conversion safely (lines 162-163 in lists_routes.py).
verification: Verified fix through code analysis:
  1. validate_choice=False allows missing/empty field values without validation error
  2. Route handler safely processes the value with conditional conversion (int if value else None)
  3. Template correctly renders field only for SONARR (conditional {% if service_type == 'SONARR' %})
  4. Fix addresses exact symptom: "Not a valid choice" error when editing RADARR/movie lists
  5. No side effects: field only affects SONARR lists, and SONARR forms will still submit valid values
files_changed:
  - listarr/forms/lists_forms.py
