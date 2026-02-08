/**
 * Shared JavaScript utility functions for Listarr.
 * Loaded globally via base.html — available on all pages.
 */

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

function getCsrfToken() {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.content : "";
}

// --- Formatting ---

/**
 * Format timestamp with multiple display modes.
 * @param {string} isoString - ISO 8601 timestamp
 * @param {string} mode - 'relative' | 'absolute' | 'utc' (default: 'relative')
 * @returns {string} Formatted date string
 */
function formatTimestamp(isoString, mode = "relative") {
  if (!isoString) return mode === "relative" ? "-" : "--";

  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;

    switch (mode) {
      case "utc":
        // "2024-01-15 12:30 UTC" - used by generateStatusHTML
        return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";

      case "absolute":
        // "Jan 15, 2024, 12:30 PM" - used by jobs table
        return date.toLocaleString(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });

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
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } else {
    if (diffSeconds < 60) return "In less than a minute";
    if (diffMinutes < 60) return `In ${diffMinutes} minute${diffMinutes > 1 ? "s" : ""}`;
    if (diffHours < 24) return `In ${diffHours} hour${diffHours > 1 ? "s" : ""}`;
    if (diffDays === 1) {
      return `Tomorrow at ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
    }
    return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
}

function generateStatusHTML(success, timestamp) {
  const statusIcon = success ? "\u2713" : "\u2717";
  const statusClass = success
    ? "text-green-600 dark:text-green-400"
    : "text-red-600 dark:text-red-400";
  const formattedTime = formatTimestamp(timestamp, "utc");

  return `
    <span class="inline-flex items-center gap-1">
      <span class="${statusClass}">${statusIcon}</span>
      Last tested: <span data-timestamp="${timestamp}">${formattedTime}</span>
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
    ? "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200"
    : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
  return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}">${capitalize(service)}</span>`;
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
