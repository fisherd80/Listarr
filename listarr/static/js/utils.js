/**
 * Shared JavaScript utility functions for Listarr.
 * Loaded globally via base.html — available on all pages.
 */

// --- Global 401 Handler ---

/**
 * Override window.fetch to globally intercept 401 responses and redirect to login.
 * This ensures all AJAX calls automatically handle session expiry.
 */
(function () {
  const originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const response = await originalFetch.apply(this, args);

    // Redirect to login on 401, unless already on login page
    if (response.status === 401 && window.location.pathname !== '/login') {
      // Store current URL for post-login redirect
      sessionStorage.setItem('loginRedirect', window.location.href);
      window.location.href = '/login';
    }

    return response;
  };
})();

// --- Fetch Utilities ---

/**
 * Fetch with configurable timeout using AbortSignal.
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options (signal, headers, etc.)
 * @param {number} timeoutMs - Timeout in milliseconds (default 10000)
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
  const { signal, ...fetchOptions } = options;
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const combinedSignal = signal
    ? AbortSignal.any([signal, timeoutSignal])
    : timeoutSignal;

  try {
    return await fetch(url, { ...fetchOptions, signal: combinedSignal });
  } catch (err) {
    if (err.name === "TimeoutError") {
      throw new Error(`Request timed out after ${timeoutMs}ms`);
    }
    if (err.name === "AbortError") {
      throw new Error("Request was cancelled");
    }
    throw err;
  }
}

// --- DOM Utilities ---

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Escape a value for interpolation into a double-quoted HTML attribute.
 * escapeHtml() alone leaves quotes intact, which is not safe in attribute position.
 */
function escapeAttr(str) {
  return escapeHtml(str).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function getCsrfToken() {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.content : "";
}

// --- Formatting ---

/**
 * Format timestamp with multiple display modes.
 *
 * Absolute output is rendered in the application timezone (window.APP_TZ).
 *
 * @param {string} isoString - ISO 8601 timestamp
 * @param {string} mode - 'relative' | 'absolute' (default: 'relative')
 * @returns {string} Formatted date string
 */
function formatTimestamp(isoString, mode = "relative") {
  if (!isoString) return mode === "relative" ? "-" : "--";

  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const tz = window.APP_TZ || undefined;

    switch (mode) {
      case "absolute":
        // "Jan 15, 2024, 12:30 PM EST" - app timezone
        return new Intl.DateTimeFormat(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: tz,
          timeZoneName: "short",
        }).format(date);

      case "relative":
      default:
        return formatRelativeTimeInternal(diffMs, date);
    }
  } catch (e) {
    return mode === "relative" ? "-" : "--";
  }
}

function formatRelativeTimeInternal(diffMs, date) {
  const diffSeconds = Math.floor(Math.abs(diffMs) / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const isPast = diffMs >= 0;

  if (isPast) {
    if (diffSeconds < 60) return "Just now";
    if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes > 1 ? "s" : ""} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: window.APP_TZ || undefined });
  } else {
    if (diffSeconds < 60) return "In less than a minute";
    if (diffMinutes < 60) return `In ${diffMinutes} minute${diffMinutes > 1 ? "s" : ""}`;
    if (diffHours < 24) return `In ${diffHours} hour${diffHours > 1 ? "s" : ""}`;
    if (diffDays === 1) {
      return `Tomorrow at ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", timeZone: window.APP_TZ || undefined })}`;
    }
    return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZone: window.APP_TZ || undefined });
  }
}

function appTzTooltip(isoString) {
  if (!isoString) return "";

  try {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return "";

    return new Intl.DateTimeFormat(undefined, {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: window.APP_TZ || undefined,
      timeZoneName: "longOffset",
    }).format(date);
  } catch (e) {
    return "";
  }
}

/**
 * Attach app-timezone tooltips to every [data-timestamp] element under `root`.
 *
 * `root` scopes the sweep to markup injected after DOMContentLoaded — jobs.js calls it
 * with the jobs tbody after replacing its rows (IN-03). Nodes built via createElement
 * rather than innerHTML should set `title = appTzTooltip(iso)` directly instead.
 *
 * @param {ParentNode} [root=document] - Subtree to sweep.
 */
function applyAppTzTooltips(root) {
  if (!root) root = document;

  root.querySelectorAll("[data-timestamp]").forEach(function (el) {
    if (!el.dataset.timestamp) return;

    const tooltip = appTzTooltip(el.dataset.timestamp);
    if (tooltip) {
      el.title = tooltip;
    }
  });
}

function generateStatusHTML(success, timestamp) {
  const statusIcon = success ? "\u2713" : "\u2717";
  const statusClass = success
    ? "text-success"
    : "text-error";
  const formattedTime = formatTimestamp(timestamp, "absolute");

  // WR-04: applyAppTzTooltips() only runs on DOMContentLoaded, so markup injected
  // later must carry its own app-timezone tooltip rather than wait to be swept.
  const tooltip = appTzTooltip(timestamp);
  const titleAttr = tooltip ? ` title="${escapeAttr(tooltip)}"` : "";
  const tsAttr = escapeAttr(timestamp || "");

  return `
    <span class="inline-flex items-center gap-1">
      <span class="${statusClass}">${statusIcon}</span>
      Last tested: <span data-timestamp="${tsAttr}"${titleAttr}>${formattedTime}</span>
    </span>
  `;
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "\u2014";
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  if (minutes < 60) {
    return remainingSeconds > 0
      ? `${minutes}m ${remainingSeconds}s`
      : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function generateServiceBadge(service) {
  const isRadarr = service.toLowerCase() === "radarr";
  const colorClass = isRadarr
    ? "bg-badge-movie/15 text-badge-movie border border-badge-movie/30"
    : "bg-badge-tv/15 text-badge-tv border border-badge-tv/30";
  // colorClass is constructed from a hardcoded boolean branch — not user data, no escaping needed
  return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}">${escapeHtml(capitalize(service))}</span>`;
}

// --- Function Utilities ---

function debounce(func, wait) {
  if (wait === undefined) wait = 300;
  let timeout;
  return function () {
    const context = this;
    const args = arguments;
    clearTimeout(timeout);
    timeout = setTimeout(function () {
      func.apply(context, args);
    }, wait);
  };
}

// --- Sonarr Monitor-Mode Gating (D-06 / D-08) ---
//
// Client mirror of the reconciliation in import_service.resolve_import_settings:
//   Rule 1: an unmonitored series can never emit a monitoring or searching payload.
//   Rule 2: an explicit "none" mode forces search-on-add off.
// The server remains authoritative; this only reflects the rule in the UI.
//
// Shared by all four monitor-mode surfaces (settings.js, create.js, wizard.js and the
// edit-list inline script) so the rule and its wording live in one place.

// `unmonitored` is the copy locked verbatim by 13-UI-SPEC.md for the Monitor Mode select.
// The spec does not state what Search on Add shows in that same state, so `unmonitoredSearch`
// explains it from that field's own point of view - reusing the Monitor Mode sentence there
// misattributes the reason (it isn't about monitor mode when read under Search on Add).
var MONITOR_GATING_HELP = {
  unmonitored: "Series are added unmonitored, so monitor mode doesn't apply.",
  unmonitoredSearch: "Series are added unmonitored, so there's nothing to search for.",
  noneSearch: "None adds the series without monitoring anything, so there's nothing to search for.",
};

/**
 * Return the [value, label] monitor-mode rows published by the server, or [] when absent.
 *
 * Reads the #monitor-mode-choices JSON block rendered by base.html from MONITOR_MODE_CHOICES,
 * so the locked option labels have exactly one source across Jinja and JS surfaces.
 */
function monitorModeChoices() {
  var el = document.getElementById('monitor-mode-choices');
  if (!el) { return []; }
  try {
    var parsed = JSON.parse(el.textContent);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    return [];
  }
}

/**
 * Build the monitor-mode <option> rows as an HTML string, mirroring the Jinja
 * monitor_mode_options macro. `useDefault` prepends the blank "Use Default" inherit row.
 */
function monitorModeOptionsHtml(useDefault, selectedValue) {
  var selected = selectedValue || '';
  var html = '';
  if (useDefault) {
    html += '<option value=""' + (selected ? '' : ' selected') + '>Use Default</option>';
  }
  monitorModeChoices().forEach(function (choice) {
    var value = choice[0];
    var label = choice[1];
    html += '<option value="' + escapeHtml(value) + '"' +
      (value === selected ? ' selected' : '') + '>' + escapeHtml(label) + '</option>';
  });
  return html;
}

/**
 * Toggle a control's disabled state and its matching "inactive" styling.
 */
function setDisabledState(el, disabled) {
  if (!el) { return; }
  el.disabled = disabled;
  el.classList.toggle('opacity-50', disabled);
  el.classList.toggle('cursor-not-allowed', disabled);
}

/**
 * Return a help element's server-rendered text, captured on first use.
 *
 * Gating overwrites these paragraphs, so the original wording is stashed on the node the
 * first time it is read. This keeps the copy in the Jinja template the single source of
 * truth instead of duplicating each sentence as a JS constant.
 */
function defaultHelpText(el) {
  if (!el) { return ''; }
  if (el.dataset.defaultHelp === undefined) {
    el.dataset.defaultHelp = (el.textContent || '').trim();
  }
  return el.dataset.defaultHelp;
}

function setHelpText(el, text) {
  if (el) { el.textContent = text; }
}

/**
 * Apply the monitor/search gating rule to one surface.
 *
 * @param {Object} cfg
 * @param {HTMLElement} cfg.modeEl        - the monitor-mode <select>
 * @param {HTMLElement} cfg.searchEl      - the search-on-add control
 * @param {HTMLElement} [cfg.modeHelpEl]  - help text under the mode select
 * @param {HTMLElement} [cfg.searchHelpEl]- help text under the search control
 * @param {boolean} cfg.unmonitored       - true when "monitored" is off
 * @param {boolean} cfg.modeIsNone        - true when the mode is "none"
 * @param {Function} [cfg.beforeDisableSearch] - stash the search value before it is cleared
 * @param {Function} [cfg.clearSearch]    - force the search control off (omit to leave values untouched)
 * @param {Function} [cfg.restoreSearch]  - put the stashed search value back when re-enabled
 */
function applyMonitorGating(cfg) {
  // Capture the server-rendered wording before any branch overwrites it, so the first
  // call landing on a gated branch cannot stash gating text as the "default".
  var modeHelp = defaultHelpText(cfg.modeHelpEl);
  var searchHelp = defaultHelpText(cfg.searchHelpEl);

  if (cfg.unmonitored) {
    if (cfg.beforeDisableSearch) { cfg.beforeDisableSearch(); }
    setDisabledState(cfg.modeEl, true);
    setHelpText(cfg.modeHelpEl, MONITOR_GATING_HELP.unmonitored);
    if (cfg.clearSearch) { cfg.clearSearch(); }
    setDisabledState(cfg.searchEl, true);
    setHelpText(cfg.searchHelpEl, MONITOR_GATING_HELP.unmonitoredSearch);
    return;
  }

  setDisabledState(cfg.modeEl, false);
  setHelpText(cfg.modeHelpEl, modeHelp);

  if (cfg.modeIsNone) {
    if (cfg.beforeDisableSearch) { cfg.beforeDisableSearch(); }
    if (cfg.clearSearch) { cfg.clearSearch(); }
    setDisabledState(cfg.searchEl, true);
    setHelpText(cfg.searchHelpEl, MONITOR_GATING_HELP.noneSearch);
  } else {
    setDisabledState(cfg.searchEl, false);
    if (cfg.restoreSearch) { cfg.restoreSearch(); }
    setHelpText(cfg.searchHelpEl, searchHelp);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  applyAppTzTooltips();
});
