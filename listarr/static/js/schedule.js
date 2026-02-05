// ----------------------
// Schedule Page JavaScript
// ----------------------

/**
 * State management for schedule page
 */
const state = {
  pollingInterval: null,
  hasRunningJobs: false,
};

/**
 * Gets the CSRF token from the meta tag.
 * @returns {string} CSRF token value
 */
function getCsrfToken() {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.content : "";
}

/**
 * Format ISO date string to relative time.
 * @param {string} isoString - ISO date string
 * @returns {string} Relative time string
 */
function formatRelativeTime(isoString) {
  if (!isoString) return "-";
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    // Past dates
    if (diffMs >= 0) {
      if (diffSeconds < 60) return "Just now";
      if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes > 1 ? "s" : ""} ago`;
      if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
      if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
      return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    }

    // Future dates (for next run)
    const absDiffSeconds = Math.abs(diffSeconds);
    const absDiffMinutes = Math.abs(diffMinutes);
    const absDiffHours = Math.abs(diffHours);
    const absDiffDays = Math.abs(diffDays);

    if (absDiffSeconds < 60) return "In less than a minute";
    if (absDiffMinutes < 60) return `In ${absDiffMinutes} minute${absDiffMinutes > 1 ? "s" : ""}`;
    if (absDiffHours < 24) return `In ${absDiffHours} hour${absDiffHours > 1 ? "s" : ""}`;
    if (absDiffDays === 1) {
      return `Tomorrow at ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
    }
    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (e) {
    return "-";
  }
}

/**
 * Update status badge styling.
 * @param {Element} badge - Badge element
 * @param {string} status - Status value
 */
function updateStatusBadge(badge, status) {
  // Remove all status classes
  badge.className = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium status-badge";

  // Add status-specific classes
  switch (status) {
    case "Running":
      badge.classList.add("bg-blue-100", "text-blue-800", "dark:bg-blue-900", "dark:text-blue-200");
      badge.innerHTML = `
        <svg class="animate-spin -ml-1 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Running
      `;
      break;
    case "Paused":
      badge.classList.add("bg-yellow-100", "text-yellow-800", "dark:bg-yellow-900", "dark:text-yellow-200");
      badge.textContent = "Paused";
      break;
    case "Scheduled":
      badge.classList.add("bg-green-100", "text-green-800", "dark:bg-green-900", "dark:text-green-200");
      badge.textContent = "Scheduled";
      break;
    case "Manual only":
      badge.classList.add("bg-gray-100", "text-gray-800", "dark:bg-gray-900", "dark:text-gray-200");
      badge.textContent = "Manual only";
      break;
  }
  badge.setAttribute("data-status", status);
}

/**
 * Update all relative time displays.
 */
function updateRelativeTimes() {
  document.querySelectorAll(".relative-time").forEach((element) => {
    const isoString = element.closest("td").getAttribute("data-last-run") || element.closest("td").getAttribute("data-next-run");
    if (isoString) {
      element.textContent = formatRelativeTime(isoString);
    }
  });
}

/**
 * Toggle global pause/resume state.
 */
async function toggleGlobalScheduler() {
  const btn = document.getElementById("global-toggle-btn");
  const isPaused = btn.getAttribute("data-paused") === "true";

  // Disable button during request
  btn.disabled = true;

  try {
    const endpoint = isPaused ? "/api/schedule/resume" : "/api/schedule/pause";
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    if (!data.success) throw new Error("Toggle failed");

    // Update button state
    const newPaused = !isPaused;
    btn.setAttribute("data-paused", newPaused.toString());

    // Update button appearance
    if (newPaused) {
      btn.className = "inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-yellow-600 hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500";
      btn.innerHTML = `
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span id="toggle-btn-text">Resume All</span>
      `;
    } else {
      btn.className = "inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500";
      btn.innerHTML = `
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span id="toggle-btn-text">Pause All</span>
      `;
    }

    // Refresh schedule status
    await refreshScheduleStatus();

    // Show success toast
    if (window.showToast) {
      window.showToast(newPaused ? "All schedules paused" : "All schedules resumed", "success");
    }
  } catch (error) {
    console.error("Failed to toggle scheduler:", error);
    if (window.showToast) {
      window.showToast("Failed to toggle scheduler", "error");
    }
  } finally {
    btn.disabled = false;
  }
}

/**
 * Refresh schedule status from API.
 */
async function refreshScheduleStatus() {
  try {
    const response = await fetch("/api/schedule/status");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();

    // Update status badges
    let hasRunning = false;
    data.lists.forEach((list) => {
      const badge = document.querySelector(`tr[onclick*="${list.id}"] .status-badge`);
      if (badge) {
        updateStatusBadge(badge, list.status);
      }
      if (list.status === "Running") {
        hasRunning = true;
      }

      // Update next run times
      const nextRunCell = document.querySelector(`tr[onclick*="${list.id}"] td[data-next-run]`);
      if (nextRunCell) {
        nextRunCell.setAttribute("data-next-run", list.next_run || "");
        const timeSpan = nextRunCell.querySelector(".relative-time");
        if (timeSpan) {
          if (list.next_run) {
            timeSpan.textContent = formatRelativeTime(list.next_run);
          } else if (list.has_schedule && data.paused) {
            timeSpan.className = "text-gray-400 dark:text-gray-500";
            timeSpan.textContent = "Paused";
          } else {
            timeSpan.textContent = "-";
          }
        }
      }
    });

    // Update polling based on running jobs
    if (hasRunning && !state.pollingInterval) {
      startPolling();
    } else if (!hasRunning && state.pollingInterval) {
      stopPolling();
    }

    state.hasRunningJobs = hasRunning;
  } catch (error) {
    console.error("Failed to refresh schedule status:", error);
  }
}

/**
 * Start polling for schedule updates.
 */
function startPolling() {
  if (state.pollingInterval) return;
  console.log("Starting schedule polling (5s interval)");
  state.pollingInterval = setInterval(refreshScheduleStatus, 5000);
}

/**
 * Stop polling for schedule updates.
 */
function stopPolling() {
  if (!state.pollingInterval) return;
  console.log("Stopping schedule polling");
  clearInterval(state.pollingInterval);
  state.pollingInterval = null;
}

/**
 * Initialize the schedule page.
 */
document.addEventListener("DOMContentLoaded", () => {
  // Attach global toggle handler
  const toggleBtn = document.getElementById("global-toggle-btn");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", toggleGlobalScheduler);
  }

  // Update relative times immediately
  updateRelativeTimes();

  // Check if any jobs are running
  const runningBadges = document.querySelectorAll('.status-badge[data-status="Running"]');
  if (runningBadges.length > 0) {
    state.hasRunningJobs = true;
    startPolling();
  }

  // Update relative times every 30 seconds
  setInterval(updateRelativeTimes, 30000);
});

// Stop polling when page is hidden
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopPolling();
  } else if (state.hasRunningJobs) {
    startPolling();
  }
});
