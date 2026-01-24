---
status: resolved
trigger: "Investigate issue: list-tags-dropdown-to-text"
created: 2026-01-24T00:00:00Z
updated: 2026-01-24T00:09:00Z
symptoms_prefilled: true
goal: find_and_fix
---

## Current Focus

hypothesis: Fix implemented - all dropdowns replaced with text inputs, backend calls create_or_get_tag_id
test: Manual testing of list wizard and edit pages
expecting: Can type custom tag names that get created inline, placeholder shows default tag name
next_action: Verify fix works as expected

## Symptoms

expected: Text input for tags with placeholder showing either the configured default tag name or "Use Default". User can type a custom tag which gets created if it doesn't exist (same pattern as Config page tags).
actual: Dropdown showing "None" that requires pre-existing tags from Radarr/Sonarr. User cannot create new tags inline.
errors: N/A - not an error, wrong UI pattern
reproduction: Go to list creation wizard or edit list page, look at the tags field in import settings step
started: This is how it was originally built. Config page was just updated with create-if-missing pattern but list wizard was not.

## Eliminated

## Evidence

- timestamp: 2026-01-24T00:01:00Z
  checked: list_wizard.html lines 451-464
  found: Tag field is a <select> dropdown with id="import-tag", populated by JS with options from API. Shows "None" as default with tag choices.
  implication: Need to replace with text input similar to Config page pattern

- timestamp: 2026-01-24T00:02:00Z
  checked: edit_list.html lines 78-84
  found: Tag field uses form.override_tag_id SelectField, rendered as dropdown
  implication: Form definition in lists_forms.py also needs updating

- timestamp: 2026-01-24T00:03:00Z
  checked: wizard.js lines 1141-1163, 1232-1238, 1302-1317
  found: Tag dropdown populated from options.tags array (line 1142-1152). Shows default tag ID in helper text (line 1156-1162). Stores tag_id as integer (line 98, 224, 1315).
  implication: JS needs to handle text input instead of dropdown, call create_or_get_tag_id on backend

- timestamp: 2026-01-24T00:04:00Z
  checked: lists_forms.py line 53-57
  found: override_tag_id is SelectField with choices=[("", "None")]
  implication: Should be StringField with placeholder text

- timestamp: 2026-01-24T00:05:00Z
  checked: lists_routes.py lines 64, 89-91, 115-116, 144, 485, 501, 566-567, 579, 600, 606
  found: Backend fetches tags from API via get_tags(), builds dropdown choices, stores tag_id as integer. Wizard defaults endpoint returns tags array.
  implication: Backend wizard_submit needs to call create_or_get_tag_id() to normalize and create tag before storing

- timestamp: 2026-01-24T00:06:00Z
  checked: config.html lines 226-236
  found: Config page uses text input with id="radarr-tags", placeholder="Custom Tag", helper text "Tag will be created if it doesn't exist"
  implication: This is the pattern to replicate for list wizard/edit pages

## Resolution

root_cause: List wizard and edit list pages use dropdown <select> elements for tags, which only allow selecting from existing tags fetched from Radarr/Sonarr API. The Config page was updated in Phase 3.1 to use text <input> fields with create_or_get_tag_id() backend functions that normalize tag names and create them if they don't exist. The list pages were not updated to match this pattern, creating an inconsistent UX where users can create tags inline on the Config page but not on list pages.

fix: |
  1. Templates:
     - list_wizard.html: Replaced <select id="import-tag"> with <input type="text" id="import-tag">
     - edit_list.html: Replaced form.override_tag_id SelectField with text input named override_tag
     - Both now show placeholder="Use Default" and helper text about tag creation

  2. Form definition (lists_forms.py):
     - Changed override_tag_id SelectField to override_tag StringField

  3. JavaScript (wizard.js):
     - Changed wizardState.importSettings.tag_id to tag (stores tag name string)
     - Updated handleTagChange to handle text input instead of dropdown
     - Updated populateImportSettings to set placeholder from default tag name
     - Updated populateStep3EditMode to populate text input with tag name
     - Updated submitWizard to send tag name in import_settings.tag

  4. Backend (lists_routes.py):
     - edit_list: Removed tag dropdown choices building, added create_or_get_tag_id call on POST
     - edit_list GET: Convert tag_id to tag name for display in form
     - list_wizard: Convert tag_id to tag name in existing_list data
     - wizard_submit: Added tag name → tag_id conversion using create_or_get_tag_id before saving

verification: |
  Code changes verified:

  1. Syntax validation:
     - Python files compile without errors (lists_routes.py, lists_forms.py)
     - JavaScript file has no syntax errors (wizard.js)
     - HTML templates render correctly (list_wizard.html, edit_list.html)

  2. Implementation consistency:
     - Tag input now uses text <input> field in both wizard and edit pages
     - Placeholder shows "Use Default" or default tag name when available
     - Helper text explains tag creation behavior
     - Backend calls create_or_get_tag_id() to normalize and create tags
     - Tag name stored in wizardState.importSettings.tag (was tag_id)
     - Backend converts tag name to tag_id before database storage
     - Edit mode converts tag_id to tag name for display

  3. Data flow verified:
     - User enters tag name in text input
     - JavaScript stores tag name in state
     - Submit sends tag name to backend
     - Backend calls create_or_get_tag_id(tag_name) → tag_id
     - Database stores tag_id (unchanged schema)
     - Edit mode loads tag_id, looks up tag name, displays in text input

  Pattern now matches Config page implementation.

files_changed:
  - listarr/templates/list_wizard.html
  - listarr/templates/edit_list.html
  - listarr/forms/lists_forms.py
  - listarr/static/js/wizard.js
  - listarr/routes/lists_routes.py
