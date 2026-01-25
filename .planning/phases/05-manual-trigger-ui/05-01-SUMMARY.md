# Phase 5 Plan 01: Run Button and Handler Summary

**One-liner:** Run button in list table with runList() handler showing import results via toast notifications

## What Was Built

### Run Button (lists.html)
- Added Run button as first action in the Actions column
- Button uses `data-run-list` attribute for JavaScript selection
- Conditionally visible based on `list.is_active` status (hidden when inactive)
- Includes `data-list-active` attribute for dynamic state management
- Matches existing button styling: `text-primary hover:text-indigo-900 dark:hover:text-indigo-300 mr-3`

### runList() Handler (lists.js)
- Immediate button disable + "Running..." text prevents double-click
- POST request to `/lists/${listId}/run` with CSRF token
- On success: displays import results in toast (added/skipped/failed counts)
- On error: shows error toast with message, restores button state
- Includes placeholder stubs for polling functions (trackRunningJob, pollJobStatus) to be implemented in 05-02

### Toggle Integration
- Updated `toggleList()` to show/hide Run button when list status changes
- Active lists show Run button, inactive lists hide it
- Updates `data-list-active` attribute on state change

### Initialization
- Added `initRunButtons()` function to attach click handlers
- Called from `initListsPage()` on DOM ready

## Deviation from Plan

**Endpoint Response Handling:** The plan specified the endpoint returns 202 (async), but the actual `/lists/<id>/run` endpoint returns 200 with synchronous results. Adapted implementation to:
- Show actual import results in toast (added/skipped/failed counts) instead of "Import started"
- Re-enable button after completion (since import completes synchronously)
- Placeholder stubs still included for future async implementation (05-02)

This is a [Rule 3 - Blocking] deviation: the plan assumed async behavior that doesn't exist yet. Implementation handles current synchronous behavior while maintaining compatibility with future polling (05-02).

## Files Modified

| File | Changes |
|------|---------|
| `listarr/templates/lists.html` | Added Run button (9 lines) in Actions column |
| `listarr/static/js/lists.js` | Added runList(), initRunButtons(), polling stubs, toggle integration (87 lines) |

## Commits

| Hash | Message |
|------|---------|
| 536d685 | feat(05-01): add Run button to lists table |
| f675a71 | feat(05-01): implement runList() handler with toast feedback |

## Verification Status

| Criteria | Status |
|----------|--------|
| Run button appears for active lists | Pass |
| Run button hidden for inactive lists | Pass |
| Clicking Run shows "Running..." state | Pass |
| Success shows result toast | Pass |
| Error shows error toast and restores button | Pass |
| Toggle updates Run button visibility | Pass |
| Double-click prevention | Pass |
| All 363 tests pass | Pass |

## Technical Details

### Button HTML Structure
```html
<button
  type="button"
  data-run-list="{{ list.id }}"
  data-list-active="{{ 'true' if list.is_active else 'false' }}"
  class="text-primary hover:text-indigo-900 dark:hover:text-indigo-300 mr-3"
  {% if not list.is_active %}style="display: none;"{% endif %}
>
  Run
</button>
```

### JavaScript Functions Added
- `runList(listId, button)` - Main handler for Run button clicks
- `initRunButtons()` - Attaches click handlers to all Run buttons
- `trackRunningJob(listId, startTime)` - Stub for 05-02
- `pollJobStatus(listId)` - Stub for 05-02

### Integration Points
- Uses existing `getCsrfToken()` for CSRF protection
- Uses existing `showToast()` from toast.js for notifications
- Follows existing fetch/error handling patterns from toggleList() and deleteList()

## Next Phase Readiness

Ready for 05-02 (Progress Polling):
- Placeholder stubs in place for `trackRunningJob()` and `pollJobStatus()`
- Button state management ready for polling to restore
- Data attributes available for job tracking
