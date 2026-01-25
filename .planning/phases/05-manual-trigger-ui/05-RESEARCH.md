# Phase 5: Manual Trigger UI - Research

**Researched:** 2026-01-25
**Domain:** Flask AJAX patterns, vanilla JavaScript polling, button state management
**Confidence:** HIGH

## Summary

This phase adds manual trigger functionality to the existing List Management page, allowing users to run imports on-demand. The codebase already has all necessary infrastructure: the `/lists/<id>/run` endpoint exists and returns structured `ImportResult` data, a shared toast notification system (`toast.js`) is implemented and loaded globally, and established patterns exist for AJAX button actions (see `toggleList()` and `deleteList()` in `lists.js`).

The primary technical challenge is tracking asynchronous job state across page navigation. Since Flask is a stateless request/response framework without built-in background job tracking, the solution involves client-side state persistence using `localStorage` combined with polling to detect completion. This is the standard lightweight approach for Flask applications that don't use Celery or Redis Queue.

**Primary recommendation:** Follow existing codebase patterns for button actions and toast notifications. Use `localStorage` to persist running state across navigation, implement simple polling with 2-second intervals, and use `AbortController` for cleanup on page unload.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JavaScript | ES6+ | Client-side logic | Already used throughout codebase, no framework dependencies |
| Fetch API | Native | AJAX requests | Modern replacement for XMLHttpRequest, native browser support |
| localStorage | Native | State persistence | HTML5 Web Storage API for cross-navigation state |
| AbortController | Native | Request cancellation | Standard way to prevent memory leaks in polling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Tailwind CSS | CDN | Button styling | Already configured in base.html |
| Flask CSRF | Built-in | Request protection | Required for POST endpoints |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| localStorage | sessionStorage | sessionStorage is tab-specific, would lose state on tab close |
| Polling | WebSockets/Server-Sent Events | Too heavy for simple status checks, requires additional server infrastructure |
| Client-side tracking | Celery + Redis | Massive infrastructure overhead for simple feature, not justified |

**Installation:**
No additional dependencies required. All capabilities are native browser APIs or already in the codebase.

## Architecture Patterns

### Recommended Project Structure
```
listarr/
├── static/js/
│   ├── toast.js          # Already exists - shared notification system
│   └── lists.js          # Extend with run button handlers
└── templates/
    └── lists.html        # Add Run button to actions column
```

### Pattern 1: Button State Management with AJAX
**What:** Disable button immediately on click, update text, make async request, update state based on response
**When to use:** Any button that triggers async server action
**Example:**
```javascript
// Source: Existing codebase pattern from lists.js lines 97-155
function runList(listId, button) {
  // 1. Disable button immediately
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = "Running...";

  // 2. Make async request
  fetch(`/lists/${listId}/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        // Start polling for completion
        trackRunningJob(listId);
        showToast("Import started", "info");
      } else {
        // Failed to start - restore button
        button.disabled = false;
        button.textContent = originalText;
        showToast(data.error || "Failed to start import", "error");
      }
    })
    .catch((error) => {
      // Network error - restore button
      button.disabled = false;
      button.textContent = originalText;
      showToast("Error starting import. Please try again.", "error");
    });
}
```

### Pattern 2: State Persistence with localStorage
**What:** Store running job state in localStorage to survive page navigation
**When to use:** Any client-side state that must persist across navigation without server session
**Example:**
```javascript
// Source: MDN Web Storage API, javascript.info/localstorage
function trackRunningJob(listId) {
  // Store in localStorage (survives navigation)
  const runningJobs = JSON.parse(localStorage.getItem('runningJobs') || '{}');
  runningJobs[listId] = {
    startedAt: Date.now(),
    status: 'running'
  };
  localStorage.setItem('runningJobs', JSON.stringify(runningJobs));

  // Start polling
  pollJobStatus(listId);
}

function getRunningJobs() {
  return JSON.parse(localStorage.getItem('runningJobs') || '{}');
}

function clearRunningJob(listId) {
  const runningJobs = getRunningJobs();
  delete runningJobs[listId];
  localStorage.setItem('runningJobs', JSON.stringify(runningJobs));
}
```

### Pattern 3: Simple Polling with Cleanup
**What:** Poll endpoint at regular intervals, clean up on completion or page unload
**When to use:** Status checking for async operations without WebSocket infrastructure
**Example:**
```javascript
// Source: davidwalsh.name/javascript-polling, dev.to/abhishek97/poll-backend-endpoint
let pollingTimers = {};
let abortControllers = {};

function pollJobStatus(listId) {
  // Create abort controller for cleanup
  const controller = new AbortController();
  abortControllers[listId] = controller;

  const poll = () => {
    fetch(`/lists/${listId}/status`, {
      signal: controller.signal
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'completed') {
          // Job finished - show results and cleanup
          handleJobComplete(listId, data.result);
          clearRunningJob(listId);
          delete pollingTimers[listId];
          delete abortControllers[listId];
        } else if (data.status === 'running') {
          // Still running - continue polling
          pollingTimers[listId] = setTimeout(poll, 2000);
        } else {
          // Unknown state - stop polling
          clearRunningJob(listId);
          delete pollingTimers[listId];
          delete abortControllers[listId];
        }
      })
      .catch(error => {
        if (error.name === 'AbortError') {
          // Polling cancelled - normal cleanup
          return;
        }
        console.error('Polling error:', error);
        // Don't stop polling on network errors
        pollingTimers[listId] = setTimeout(poll, 2000);
      });
  };

  // Start first poll
  poll();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  Object.values(abortControllers).forEach(c => c.abort());
});
```

### Pattern 4: Page Load State Restoration
**What:** Check localStorage on page load to restore running state for jobs still in progress
**When to use:** Any feature with persistent async state across navigation
**Example:**
```javascript
// Source: Existing codebase pattern from lists.js initListsPage()
function restoreRunningStates() {
  const runningJobs = getRunningJobs();

  Object.keys(runningJobs).forEach(listId => {
    const button = document.querySelector(`[data-run-list="${listId}"]`);
    if (button) {
      // Restore "Running..." state
      button.disabled = true;
      button.textContent = "Running...";

      // Resume polling
      pollJobStatus(listId);
    } else {
      // Button not on page - clear stale state
      clearRunningJob(listId);
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initListsPage();
  restoreRunningStates();
});
```

### Pattern 5: Toast Notification with ImportResult
**What:** Parse ImportResult data and show color-coded toast with summary
**When to use:** Displaying results from `/lists/<id>/run` endpoint
**Example:**
```javascript
// Source: Existing toast.js, ImportResult.to_dict() structure
function handleJobComplete(listId, result) {
  const button = document.querySelector(`[data-run-list="${listId}"]`);
  if (button) {
    button.disabled = false;
    button.textContent = "Run";
  }

  // Parse ImportResult structure
  const { summary } = result;
  const message = `${summary.added_count} added, ${summary.skipped_count} skipped, ${summary.failed_count} failed`;

  // Determine toast type based on results
  let toastType = 'success';
  if (summary.failed_count > 0) {
    toastType = 'error';
  } else if (summary.skipped_count > 0) {
    toastType = 'warning';
  }

  // Use existing toast system (toast.js)
  showToast(message, toastType, 5000);
}
```

### Anti-Patterns to Avoid
- **Polling without AbortController:** Causes memory leaks when user navigates away during polling
- **Using sessionStorage instead of localStorage:** State is lost on tab close, breaking persistence requirement
- **Synchronous waiting for job completion:** User experience would be terrible, button would block for entire import duration
- **Building custom toast system:** Codebase already has a complete toast.js implementation with dark mode support
- **Aggressive polling (< 1 second intervals):** Unnecessary server load for a non-critical feature, 2 seconds is industry standard

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast notifications | Custom toast HTML/CSS/JS from scratch | Existing `toast.js` with `showToast()` | Already implemented with dark mode, animations, auto-dismiss, and consistent styling |
| CSRF token extraction | Manual meta tag parsing | Existing `getCsrfToken()` function in lists.js | Already handles edge cases, used by all other actions |
| Request abortion | Custom timeout logic with `Promise.race()` | Native `AbortController` API | Promise.race doesn't actually cancel requests, causes memory leaks |
| Button styling | Custom CSS classes | Tailwind utility classes matching existing buttons | Maintains consistency with Enable/Disable/Edit/Delete buttons |
| Error message display | Alert boxes or custom modal | Toast system with type='error' | Consistent with app's error handling pattern |

**Key insight:** This codebase has mature patterns for every piece of this feature. The job is integration, not invention.

## Common Pitfalls

### Pitfall 1: Memory Leaks from Uncancelled Polling
**What goes wrong:** Polling continues after user navigates away, accumulating fetch requests and setTimeout timers
**Why it happens:** JavaScript timers and fetch promises don't automatically stop when the page changes in SPAs, or when user navigates in traditional server-rendered apps the timers persist until completion
**How to avoid:** Use AbortController for all fetch requests and clear all timers on beforeunload event
**Warning signs:** Browser DevTools Network tab shows requests to old pages, memory usage grows over time, console errors about updating unmounted components

### Pitfall 2: Lost State on Page Refresh
**What goes wrong:** User clicks "Run", navigates to another page, returns to Lists page, and button shows "Run" again even though job is still executing
**Why it happens:** Using JavaScript variables or sessionStorage instead of localStorage for tracking running jobs
**How to avoid:** Always store running state in localStorage, check and restore state on DOMContentLoaded
**Warning signs:** Users report "Run" button not showing "Running..." state after navigation, duplicate job submissions possible

### Pitfall 3: Disabled Buttons Without Visual Feedback
**What goes wrong:** Button is disabled but doesn't communicate why or that something is happening
**Why it happens:** Setting `disabled=true` without updating button text or adding loading indicator
**How to avoid:** Always change button text to "Running..." when disabled, ensure Tailwind disabled styles provide visual distinction
**Warning signs:** User confusion ("why can't I click this?"), accessibility issues, support tickets about "broken" buttons

### Pitfall 4: Race Condition on Rapid Clicks
**What goes wrong:** User double-clicks "Run" before first request completes, triggering duplicate job submissions
**Why it happens:** Disable happens asynchronously after network round-trip begins
**How to avoid:** Set `button.disabled = true` as the FIRST line in click handler, before any async operations
**Warning signs:** Database logs show duplicate imports with same list_id and timestamp, users report "it ran twice"

### Pitfall 5: Stale localStorage Data
**What goes wrong:** Old job tracking data accumulates in localStorage, causing buttons to appear stuck in "Running..." state for completed jobs
**Why it happens:** Not cleaning up localStorage when job completes, or when button element doesn't exist on page
**How to avoid:** Clear localStorage entry immediately when status='completed', clean up orphaned entries in restoreRunningStates() if button not found
**Warning signs:** localStorage size growing unbounded, buttons permanently disabled, users need to clear browser cache

### Pitfall 6: Polling After Job Completion
**What goes wrong:** Polling continues even after job finishes, wasting server resources
**Why it happens:** Not properly tracking and clearing polling timers when completion detected
**How to avoid:** Store timer IDs in object keyed by listId, delete entry when job completes, abort controller and clear timer together
**Warning signs:** Network tab shows continued requests to status endpoint after completion toast appears

### Pitfall 7: Wrong Toast Type Selection
**What goes wrong:** Showing green "success" toast when import had failures, or red "error" toast when some items succeeded
**Why it happens:** Not properly parsing ImportResult.summary to determine overall outcome
**How to avoid:** Use clear logic: error if failed_count > 0, warning if skipped_count > 0, success otherwise
**Warning signs:** User confusion about import results ("it said success but some failed"), misleading feedback

### Pitfall 8: Missing Error Recovery
**What goes wrong:** Network error during status polling leaves button permanently disabled
**Why it happens:** Catching fetch errors but not retrying or restoring button state
**How to avoid:** Continue polling on network errors (transient), only stop on abort or completion, consider max retry count
**Warning signs:** Buttons stuck in "Running..." after WiFi reconnect, users need to refresh page

## Code Examples

Verified patterns from official sources and codebase:

### Initializing Run Buttons with Event Delegation
```javascript
// Source: Existing lists.js pattern (lines 176-184)
function initRunButtons() {
  const runButtons = document.querySelectorAll("[data-run-list]");
  runButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const listId = this.getAttribute("data-run-list");
      runList(listId, this);
    });
  });
}
```

### CSRF Token Extraction
```javascript
// Source: Existing lists.js (lines 9-12)
function getCsrfToken() {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.content : "";
}
```

### Toast Notification with Existing System
```javascript
// Source: Existing toast.js (lines 57-79)
// Available types: "success", "error", "warning", "info"
// Default duration: 3000ms
showToast("5 added, 3 skipped, 1 failed", "warning", 5000);
```

### Fetch with AbortController
```javascript
// Source: MDN Web APIs, lowmess.com/blog/fetch-with-timeout
const controller = new AbortController();
const signal = controller.signal;

fetch('/api/endpoint', { signal })
  .then(response => response.json())
  .catch(error => {
    if (error.name === 'AbortError') {
      console.log('Fetch aborted');
    } else {
      console.error('Fetch error:', error);
    }
  });

// Later, to cancel:
controller.abort();
```

### Button HTML Template
```html
<!-- Source: Existing lists.html actions pattern (lines 140-159) -->
<button
  type="button"
  data-run-list="{{ list.id }}"
  class="text-primary hover:text-indigo-900 dark:hover:text-indigo-300 mr-3"
  {% if not list.is_active %}style="display: none;"{% endif %}
>
  Run
</button>
```

### Conditional Rendering Based on is_active
```jinja2
<!-- Source: Existing lists.html (lines 126-134) -->
{% if list.is_active %}
  <button data-run-list="{{ list.id }}">Run</button>
{% endif %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| XMLHttpRequest | Fetch API | ~2015 | Native promises, cleaner syntax, better error handling |
| jQuery AJAX | Vanilla JS Fetch | ~2015 | No dependencies, better performance, native browser support |
| Promise.race for timeouts | AbortController | ~2017 | Properly cancels requests, prevents memory leaks |
| Cookies for client state | localStorage/sessionStorage | ~2011 (HTML5) | More storage (5-10MB vs 4KB), no automatic server transmission |
| setInterval polling | setTimeout recursive polling | Always preferred | Prevents poll overlap, easier to cancel specific polls |
| Server session tracking | Client-side localStorage | Modern SPAs | Stateless server, scales better, works across page loads |

**Deprecated/outdated:**
- `XMLHttpRequest`: Replaced by Fetch API, more verbose and callback-based
- jQuery for AJAX: Unnecessary dependency for modern browsers
- `Promise.race()` for cancellation: Doesn't actually abort requests, use AbortController
- Global variables for state: Lost on navigation, use localStorage
- Aggressive sub-second polling: Industry standard is 2-5 seconds for non-critical updates

## Open Questions

Things that couldn't be fully resolved:

1. **Status endpoint implementation details**
   - What we know: Need a GET `/lists/<id>/status` endpoint that returns `{status: 'running'|'completed', result?: ImportResult}`
   - What's unclear: Whether endpoint should be added to lists_routes.py or if we need server-side job tracking
   - Recommendation: For Phase 5 MVP, polling could check if `list.last_run_at` timestamp changed, indicating completion. Proper job queue (Celery/RQ) would be Phase 6 territory. Simple approach: store job start time client-side, if last_run_at > start_time, job completed.

2. **Polling interval optimization**
   - What we know: Industry standard is 2-5 seconds for non-critical background tasks, adaptive polling can adjust based on activity
   - What's unclear: Whether 2 seconds is too aggressive for this use case, import jobs could take 30 seconds to several minutes
   - Recommendation: Start with fixed 2-second interval. Research shows polling should be "unobtrusive" and users expect updates without manual reload. 2 seconds provides good balance. Can optimize later with exponential backoff if needed.

3. **Maximum polling duration**
   - What we know: Polling shouldn't run forever if job hangs or server loses state
   - What's unclear: What timeout is reasonable (5 minutes? 10 minutes? 30 minutes?)
   - Recommendation: Implement 5-minute max polling duration (150 polls at 2-second interval). After timeout, show warning toast "Import taking longer than expected, check Jobs page" and stop polling but keep button disabled. User can navigate to Jobs page (Phase 6) to check actual status or refresh page to reset.

## Sources

### Primary (HIGH confidence)
- Existing codebase files:
  - `listarr/static/js/toast.js` - Toast notification system implementation
  - `listarr/static/js/lists.js` - AJAX button action patterns
  - `listarr/templates/lists.html` - List table structure and button placement
  - `listarr/routes/lists_routes.py` - `/lists/<id>/run` endpoint (lines 700-754)
  - `listarr/services/import_service.py` - ImportResult structure (lines 28-69)
  - `listarr/templates/base.html` - Global toast container and flash message handling

- [MDN Web APIs - Window.localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) - localStorage API reference
- [MDN Web APIs - Window.sessionStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage) - sessionStorage comparison
- [MDN Web APIs - AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController) - Request cancellation API
- [Flask Documentation - JavaScript, fetch, and JSON](https://flask.palletsprojects.com/en/stable/patterns/javascript/) - Official Flask AJAX patterns

### Secondary (MEDIUM confidence)
- [David Walsh - JavaScript Polling](https://davidwalsh.name/javascript-polling) - Classic polling pattern
- [DEV Community - Poll backend endpoint in Vanilla js](https://dev.to/abhishek97/poll-backend-endpoint-in-vanilla-js-147g) - Modern polling example
- [Lowmess - Request Timeouts With the Fetch API](https://lowmess.com/blog/fetch-with-timeout/) - AbortController timeout pattern
- [javascript.info - LocalStorage, sessionStorage](https://javascript.info/localstorage) - Web Storage tutorial
- [Miguel Grinberg - The Flask Mega-Tutorial, Part XXII: Background Jobs](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xxii-background-jobs) - Flask async patterns
- [LogRocket - What is a toast notification? Best practices for UX](https://blog.logrocket.com/ux-design/toast-notifications/) - Toast UX guidelines
- [Smashing Magazine - Usability Pitfalls of Disabled Buttons](https://www.smashingmagazine.com/2021/08/frustrating-design-patterns-disabled-buttons/) - Button state UX

### Tertiary (LOW confidence - general guidance)
- [Medium - Modern JavaScript Polling: Adaptive Strategies](https://medium.com/tech-pulse-by-collatzinc/modern-javascript-polling-adaptive-strategies-that-actually-work-part-1-9909f5946730) - Advanced polling strategies
- [DEV Community - AbortController manage memory efficiently](https://dev.to/tgmarinhodev/abortcontroller-manage-memory-efficiently-to-ensure-optimal-performance-2j82) - Memory leak prevention
- [Medium - Avoid Memory Leaks in React using AbortController](https://medium.com/@piyush.satija/avoid-memory-leaks-in-react-using-abortcontroller-for-network-calls-166e45c7fde) - Cleanup patterns (React-focused but principles apply)
- WebSearch results on polling intervals and toast duration (multiple sources, cross-referenced)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All native browser APIs and existing codebase patterns verified
- Architecture: HIGH - Patterns directly extracted from working codebase (lists.js, toast.js)
- Pitfalls: HIGH - Common issues well-documented in multiple authoritative sources
- Code examples: HIGH - Taken directly from codebase and official documentation

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - stable technology stack, patterns unlikely to change)
