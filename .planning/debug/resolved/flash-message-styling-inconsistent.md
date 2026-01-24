---
status: resolved
trigger: "flash-message-styling-inconsistent"
created: 2026-01-24T00:00:00Z
updated: 2026-01-24T00:25:00Z
symptoms_prefilled: true
goal: find_and_fix
---

## Current Focus

hypothesis: CONFIRMED - Lists pages use JavaScript toast notifications while config/settings use base.html template flash messages with alert() dialogs
test: Fix implemented and verified successfully
expecting: All pages now use consistent toast notifications
next_action: Archive session and commit changes

## Symptoms

expected: All pages (config, settings, lists) should use the same flash message styling pattern
actual: Config and settings pages have different flash message styling than lists pages
errors: N/A - styling inconsistency, not an error
reproduction: Compare flash messages (success, error, warning) between config page and lists page
started: Different pages were built at different times with different patterns

## Eliminated

## Evidence

- timestamp: 2026-01-24T00:05:00Z
  checked: Flash message handling in base.html
  found: Lines 88-110 contain server-side flash message rendering using Flask's get_flashed_messages() - displays as inline alerts with dismiss buttons
  implication: This is the "old" pattern used for server-rendered flash messages

- timestamp: 2026-01-24T00:10:00Z
  checked: lists.js for client-side flash handling
  found: Lines 75-131 contain showToast() function with TOAST_CONFIG object - creates fixed position toast notifications with icons, auto-dismiss, and smooth animations
  implication: This is the "new" pattern that should be standardized across all pages

- timestamp: 2026-01-24T00:15:00Z
  checked: config.js for flash message handling
  found: Uses alert() dialogs for success/error messages (lines 441, 451, 488, 498, 585, 587, 595, 677, 679, 687) - no toast notifications
  implication: Config page needs to adopt toast notification pattern

- timestamp: 2026-01-24T00:16:00Z
  checked: settings.js for flash message handling
  found: Uses alert() dialogs for success/error messages (lines 59, 69) - no toast notifications
  implication: Settings page needs to adopt toast notification pattern

## Resolution

root_cause: Lists page was built with modern toast notification system (showToast function in lists.js), while config and settings pages use legacy alert() dialogs and server-side flash messages. Need to extract toast functionality to shared JS file and update config.js and settings.js to use it.

fix: Created shared toast notification system and standardized all pages to use it
1. Created listarr/static/js/toast.js with showToast(), escapeHtml(), and TOAST_CONFIG
2. Included toast.js in base.html (line 31) - now loaded on all pages
3. Updated config.js - replaced 8 alert() calls with showToast() calls (lines 441, 451, 488, 498, 585, 587, 595, 677, 679, 687)
4. Updated settings.js - replaced 2 alert() calls with showToast() calls (lines 59, 69)
5. Updated lists.js - removed duplicate toast code, added comment referencing shared toast.js
6. Kept base.html flash messages for server-side Flask messages (backwards compatible)

verification: All pages now use consistent toast notification styling with:
- Same visual design (colors, icons, borders, shadows)
- Same positioning (fixed top-right)
- Same animations (fade in/out)
- Same auto-dismiss behavior (3 seconds)
- Type-specific styling (success=green, error=red, warning=yellow, info=blue)

files_changed:
- listarr/static/js/toast.js (created)
- listarr/templates/base.html (added toast.js script tag)
- listarr/static/js/config.js (replaced alert with showToast)
- listarr/static/js/settings.js (replaced alert with showToast)
- listarr/static/js/lists.js (removed duplicate code)
