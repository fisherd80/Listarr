// ----------------------
// Dashboard JavaScript - Radarr Card Implementation
// ----------------------

// ----------------------
// Dashboard JavaScript - Recent Jobs Implementation
// ----------------------

// Jobs polling state
let jobsPollingInterval = null;
const JOBS_POLLING_INTERVAL_MS = 2000; // 2 seconds

/**
 * Escapes HTML to prevent XSS.
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Fetches recent jobs from the API.
 * @returns {Promise<Array>} Promise that resolves with jobs array
 */
function fetchRecentJobs() {
  return fetch("/api/jobs/recent", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      return data.jobs || [];
    })
    .catch((error) => {
      console.error("Error fetching recent jobs:", error);
      // Return empty array on error
      return [];
    });
}

/**
 * Formats a date to relative time or formatted date string.
 * @param {string} dateStr - ISO format date string
 * @returns {string} Formatted date string
 */
function formatDate(dateStr) {
  if (!dateStr) return "—";

  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    // Relative time for recent dates (< 24 hours)
    if (diffMins < 1) {
      return "Just now";
    } else if (diffMins < 60) {
      return `${diffMins} minute${diffMins !== 1 ? "s" : ""} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`;
    } else {
      // Formatted date for older dates
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    }
  } catch (error) {
    console.warn("Error formatting date:", error);
    return dateStr; // Fallback to ISO string
  }
}

/**
 * Formats job summary based on status.
 * @param {Object} job - Job object from API
 * @returns {string} Formatted summary string
 */
function formatJobSummary(job) {
  if (!job) return "—";

  switch (job.status) {
    case "running":
      return '<span class="inline-flex items-center"><svg class="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Running...</span>';
    case "completed":
      const added = job.items_added || 0;
      const skipped = job.items_skipped || 0;
      return `${added} added, ${skipped} skipped`;
    case "failed":
      const errMsg = job.error_message || "Unknown error";
      // Truncate long error messages
      const truncated = errMsg.length > 50 ? errMsg.substring(0, 47) + "..." : errMsg;
      return escapeHtml(truncated);
    case "pending":
      return "Pending...";
    default:
      return "—";
  }
}

/**
 * Gets status color class based on job status.
 * @param {string} status - Job status
 * @returns {string} Tailwind CSS color class
 */
function getStatusColorClass(status) {
  switch (status) {
    case "completed":
      return "text-green-600 dark:text-green-400";
    case "failed":
      return "text-red-600 dark:text-red-400";
    case "running":
      return "text-yellow-600 dark:text-yellow-400";
    case "pending":
      return "text-gray-600 dark:text-gray-400";
    default:
      return "text-gray-600 dark:text-gray-400";
  }
}

/**
 * Capitalizes first letter of a string.
 * @param {string} str - String to capitalize
 * @returns {string} Capitalized string
 */
function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Checks if any jobs are running and starts/stops polling accordingly.
 * @param {Array} jobs - Array of job objects
 */
function checkAndManagePolling(jobs) {
  const hasRunningJobs = jobs && jobs.some((job) => job.status === "running");

  if (hasRunningJobs && !jobsPollingInterval) {
    startJobsPolling();
  } else if (!hasRunningJobs && jobsPollingInterval) {
    stopJobsPolling();
  }
}

/**
 * Starts polling for job updates.
 */
function startJobsPolling() {
  if (jobsPollingInterval) {
    return; // Already polling
  }

  console.log("Starting jobs polling (running job detected)");
  jobsPollingInterval = setInterval(() => {
    fetchRecentJobs()
      .then((jobs) => {
        updateJobsTable(jobs);
        checkAndManagePolling(jobs);
      })
      .catch((error) => {
        console.error("Error polling jobs:", error);
      });

    // Also refresh upcoming jobs during polling
    loadUpcoming();
  }, JOBS_POLLING_INTERVAL_MS);
}

/**
 * Stops polling for job updates.
 */
function stopJobsPolling() {
  if (jobsPollingInterval) {
    console.log("Stopping jobs polling (no running jobs)");
    clearInterval(jobsPollingInterval);
    jobsPollingInterval = null;
  }
}

/**
 * Loads and displays recent jobs.
 */
function loadRecentJobs() {
  fetchRecentJobs()
    .then((jobs) => {
      updateJobsTable(jobs);
      checkAndManagePolling(jobs);
    })
    .catch((error) => {
      console.error("Error loading recent jobs:", error);
      updateJobsTable([]);
    });
}

/**
 * Fetches upcoming scheduled jobs from the API.
 * @returns {Promise<Object>} Promise that resolves with upcoming jobs data
 */
function fetchUpcomingJobs() {
  return fetch("/api/dashboard/upcoming", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .catch((error) => {
      console.error("Error fetching upcoming jobs:", error);
      // Return empty data on error
      return {
        upcoming: [],
        scheduler_paused: false,
      };
    });
}

/**
 * Updates the Upcoming widget with fetched data.
 * @param {Object} data - Data from /api/dashboard/upcoming
 */
function updateUpcomingWidget(data) {
  const loadingDiv = document.getElementById("upcoming-loading");
  const emptyDiv = document.getElementById("upcoming-empty");
  const upcomingList = document.getElementById("upcoming-jobs-list");
  const pausedBadge = document.getElementById("scheduler-paused-badge");

  if (!upcomingList) {
    console.warn("Upcoming jobs list element not found");
    return;
  }

  // Show/hide paused badge
  if (pausedBadge) {
    if (data.scheduler_paused) {
      pausedBadge.classList.remove("hidden");
    } else {
      pausedBadge.classList.add("hidden");
    }
  }

  // Hide loading state
  if (loadingDiv) {
    loadingDiv.classList.add("hidden");
  }

  // Handle empty state
  if (!data.upcoming || data.upcoming.length === 0) {
    if (emptyDiv) {
      emptyDiv.classList.remove("hidden");
    }
    upcomingList.classList.add("hidden");
    return;
  }

  // Hide empty state and show list
  if (emptyDiv) {
    emptyDiv.classList.add("hidden");
  }
  upcomingList.classList.remove("hidden");

  // Clear existing list items
  upcomingList.innerHTML = "";

  // Create list items for each upcoming job
  data.upcoming.forEach((job) => {
    const listItem = document.createElement("li");
    listItem.className = "flex items-center justify-between py-2";

    // Service badge color
    const serviceColor =
      job.service === "radarr"
        ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
        : "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";

    listItem.innerHTML = `
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
          ${escapeHtml(job.list_name)}
        </p>
        <p class="text-xs text-gray-500 dark:text-gray-400">
          ${escapeHtml(job.next_run_relative)}
        </p>
      </div>
      <span class="ml-2 text-xs px-2 py-1 rounded-full ${serviceColor}">
        ${capitalize(job.service)}
      </span>
    `;

    upcomingList.appendChild(listItem);
  });
}

/**
 * Loads and displays upcoming scheduled jobs.
 */
function loadUpcoming() {
  fetchUpcomingJobs()
    .then((data) => {
      updateUpcomingWidget(data);
    })
    .catch((error) => {
      console.error("Error loading upcoming jobs:", error);
      // Show empty state on error
      updateUpcomingWidget({ upcoming: [], scheduler_paused: false });
    });
}

/**
 * Updates the jobs table with fetched jobs data.
 * @param {Array} jobs - Array of job objects
 */
function updateJobsTable(jobs) {
  const tableBody = document.getElementById("recent-jobs-table-body");
  if (!tableBody) {
    console.warn("Jobs table body not found");
    return;
  }

  // Clear existing rows
  tableBody.innerHTML = "";

  // Handle empty state
  if (!jobs || jobs.length === 0) {
    const emptyRow = document.createElement("tr");
    emptyRow.innerHTML = `
      <td colspan="4" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
        No jobs have been executed yet
      </td>
    `;
    tableBody.appendChild(emptyRow);
    return;
  }

  // Create rows for each job
  jobs.forEach((job) => {
    const row = document.createElement("tr");
    const statusColorClass = getStatusColorClass(job.status);
    const executedAt = formatDate(job.started_at);
    const summary = formatJobSummary(job);
    const service = job.target_service ? capitalize(job.target_service) : "—";
    const listName = escapeHtml(job.list_name) || "Unknown List";

    row.innerHTML = `
      <td class="px-6 py-4 text-gray-800 dark:text-gray-100">
        ${listName}
      </td>
      <td class="px-6 py-4 text-gray-600 dark:text-gray-300">
        ${service}
      </td>
      <td class="px-6 py-4 text-gray-600 dark:text-gray-300">
        ${executedAt}
      </td>
      <td class="px-6 py-4 ${statusColorClass}">
        ${summary}
      </td>
    `;

    tableBody.appendChild(row);
  });
}

/**
 * Fetches dashboard statistics from the API.
 * @param {boolean} refresh - If true, forces a cache refresh
 * @returns {Promise<Object>} Promise that resolves with dashboard stats data
 */
function fetchDashboardStats(refresh = false) {
  const url = refresh 
    ? "/api/dashboard/stats?refresh=true"
    : "/api/dashboard/stats";
    
  return fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .catch((error) => {
      console.error("Error fetching dashboard stats:", error);
      // Return error state instead of throwing
      return {
        radarr: {
          status: "offline",
          configured: false,
          version: null,
          total_movies: 0,
          missing_movies: 0,
          error: true
        },
        sonarr: {
          status: "offline",
          configured: false,
          version: null,
          total_series: 0,
          missing_episodes: 0,
          error: true
        }
      };
    });
}

/**
 * Updates the status badge element with new status.
 * @param {HTMLElement} element - The status badge element to update
 * @param {string} status - Service status: "online", "offline", or "not_configured"
 */
function updateStatusBadge(element, status) {
  if (!element) return;

  let badgeClass, badgeText;

  switch (status) {
    case "online":
      badgeClass =
        "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      badgeText = "Connected";
      break;
    case "offline":
      badgeClass =
        "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      badgeText = "Offline";
      break;
    case "not_configured":
    default:
      badgeClass =
        "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
      badgeText = "Not Configured";
      break;
  }

  // Update classes and text
  element.className = `text-xs px-2 py-1 rounded-full ${badgeClass}`;
  element.textContent = badgeText;
}

/**
 * Shows loading state on Radarr card.
 */
function showRadarrLoadingState() {
  const radarrStatus = document.getElementById("radarr-status");
  const radarrTotalMovies = document.getElementById("radarr-total-movies");
  const radarrMissingMovies = document.getElementById("radarr-missing-movies");

  if (radarrStatus) {
    radarrStatus.textContent = "Loading...";
    radarrStatus.className =
      "text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
  }

  if (radarrTotalMovies) {
    radarrTotalMovies.textContent = "Loading...";
  }

  if (radarrMissingMovies) {
    radarrMissingMovies.textContent = "Loading...";
  }

  const radarrAddedByListarr = document.getElementById("radarr-added-by-listarr");
  if (radarrAddedByListarr) {
    radarrAddedByListarr.textContent = "Loading...";
  }
}

/**
 * Shows loading state on Sonarr card.
 */
function showSonarrLoadingState() {
  const sonarrStatus = document.getElementById("sonarr-status");
  const sonarrTotalSeries = document.getElementById("sonarr-total-series");
  const sonarrMissingEpisodes = document.getElementById("sonarr-missing-episodes");

  if (sonarrStatus) {
    sonarrStatus.textContent = "Loading...";
    sonarrStatus.className =
      "text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
  }

  if (sonarrTotalSeries) {
    sonarrTotalSeries.textContent = "Loading...";
  }

  if (sonarrMissingEpisodes) {
    sonarrMissingEpisodes.textContent = "Loading...";
  }

  const sonarrAddedByListarr = document.getElementById("sonarr-added-by-listarr");
  if (sonarrAddedByListarr) {
    sonarrAddedByListarr.textContent = "Loading...";
  }
}

/**
 * Updates the Radarr card with fetched statistics.
 * @param {Object} data - Dashboard stats data from API
 */
function updateRadarrCard(data) {
  // Step 3.2: Handle Missing Data Fields - Defensive checks
  // Ensure data exists and has expected structure
  if (!data || typeof data !== "object") {
    console.warn("Invalid data received in updateRadarrCard:", data);
    data = {};
  }

  // Extract Radarr data with defaults
  const radarrData = data.radarr || {};
  const radarrStatus = radarrData.status || "not_configured";

  // Update status badge
  const radarrStatusBadge = document.getElementById("radarr-status");
  if (radarrStatusBadge) {
    updateStatusBadge(radarrStatusBadge, radarrStatus);
  }

  // Update Total Movies - Handle missing/undefined/null values
  const radarrTotalMovies = document.getElementById("radarr-total-movies");
  if (radarrTotalMovies) {
    if (
      radarrStatus === "online" &&
      radarrData.total_movies !== undefined &&
      radarrData.total_movies !== null
    ) {
      // Ensure it's a valid number
      const count = parseInt(radarrData.total_movies, 10);
      radarrTotalMovies.textContent = isNaN(count) ? "—" : count;
    } else {
      radarrTotalMovies.textContent = "—";
    }
  }

  // Update Missing Movies - Handle missing/undefined/null values
  const radarrMissingMovies = document.getElementById("radarr-missing-movies");
  if (radarrMissingMovies) {
    if (
      radarrStatus === "online" &&
      radarrData.missing_movies !== undefined &&
      radarrData.missing_movies !== null
    ) {
      // Ensure it's a valid number
      const count = parseInt(radarrData.missing_movies, 10);
      radarrMissingMovies.textContent = isNaN(count) ? "—" : count;
    } else {
      radarrMissingMovies.textContent = "—";
    }
  }

  // Update Added by Listarr - Always show if value exists
  const radarrAddedByListarr = document.getElementById("radarr-added-by-listarr");
  if (radarrAddedByListarr) {
    if (
      radarrData.added_by_listarr !== undefined &&
      radarrData.added_by_listarr !== null
    ) {
      const count = parseInt(radarrData.added_by_listarr, 10);
      radarrAddedByListarr.textContent = isNaN(count) ? "—" : count;
    } else {
      radarrAddedByListarr.textContent = "—";
    }
  }
}

/**
 * Updates the Sonarr card with fetched statistics.
 * @param {Object} data - Dashboard stats data from API
 */
function updateSonarrCard(data) {
  // Step 3.2: Handle Missing Data Fields - Defensive checks
  // Ensure data exists and has expected structure
  if (!data || typeof data !== "object") {
    console.warn("Invalid data received in updateSonarrCard:", data);
    data = {};
  }

  // Extract Sonarr data with defaults
  const sonarrData = data.sonarr || {};
  const sonarrStatus = sonarrData.status || "not_configured";

  // Update status badge
  const sonarrStatusBadge = document.getElementById("sonarr-status");
  if (sonarrStatusBadge) {
    updateStatusBadge(sonarrStatusBadge, sonarrStatus);
  }

  // Update Total Series - Handle missing/undefined/null values
  const sonarrTotalSeries = document.getElementById("sonarr-total-series");
  if (sonarrTotalSeries) {
    if (
      sonarrStatus === "online" &&
      sonarrData.total_series !== undefined &&
      sonarrData.total_series !== null
    ) {
      // Ensure it's a valid number
      const count = parseInt(sonarrData.total_series, 10);
      sonarrTotalSeries.textContent = isNaN(count) ? "—" : count;
    } else {
      sonarrTotalSeries.textContent = "—";
    }
  }

  // Update Missing Episodes - Handle missing/undefined/null values
  const sonarrMissingEpisodes = document.getElementById("sonarr-missing-episodes");
  if (sonarrMissingEpisodes) {
    if (
      sonarrStatus === "online" &&
      sonarrData.missing_episodes !== undefined &&
      sonarrData.missing_episodes !== null
    ) {
      // Ensure it's a valid number
      const count = parseInt(sonarrData.missing_episodes, 10);
      sonarrMissingEpisodes.textContent = isNaN(count) ? "—" : count;
    } else {
      sonarrMissingEpisodes.textContent = "—";
    }
  }

  // Update Added by Listarr - Always show if value exists
  const sonarrAddedByListarr = document.getElementById("sonarr-added-by-listarr");
  if (sonarrAddedByListarr) {
    if (
      sonarrData.added_by_listarr !== undefined &&
      sonarrData.added_by_listarr !== null
    ) {
      const count = parseInt(sonarrData.added_by_listarr, 10);
      sonarrAddedByListarr.textContent = isNaN(count) ? "—" : count;
    } else {
      sonarrAddedByListarr.textContent = "—";
    }
  }
}

/**
 * Refreshes dashboard data by fetching with refresh parameter.
 * @param {boolean} isManual - If true, shows button loading state (for manual refresh)
 */
function refreshDashboard(isManual = true) {
  const refreshBtn = document.getElementById("refresh-dashboard-btn");
  const refreshIcon = document.getElementById("refresh-icon");
  const refreshBtnText = document.getElementById("refresh-btn-text");

  // Only show button loading state for manual refreshes
  if (isManual) {
    // Disable button and show loading state
    if (refreshBtn) {
      refreshBtn.disabled = true;
    }
    if (refreshBtnText) {
      refreshBtnText.textContent = "Refreshing...";
    }
    if (refreshIcon) {
      refreshIcon.classList.add("animate-spin");
    }
  }

  // Show loading state on cards
  showRadarrLoadingState();
  showSonarrLoadingState();

  // Fetch stats with refresh and load jobs
  fetchDashboardStats(true)
    .then((data) => {
      console.log("Dashboard stats refreshed:", data);
      updateRadarrCard(data);
      updateSonarrCard(data);
    })
    .catch((error) => {
      console.error("Error refreshing dashboard data:", error);
      // On error, show offline state
      updateRadarrCard({
        radarr: {
          status: "offline",
          configured: false,
          version: null,
          total_movies: 0,
          missing_movies: 0,
          error: true
        },
        sonarr: {
          status: "offline",
          configured: false,
          version: null,
          total_series: 0,
          missing_episodes: 0,
          error: true
        }
      });
    });

  // Load recent jobs
  loadRecentJobs();

  // Load upcoming jobs
  loadUpcoming();

  // Re-enable button and restore text after a short delay (only for manual refreshes)
  if (isManual) {
    setTimeout(() => {
      if (refreshBtn) {
        refreshBtn.disabled = false;
      }
      if (refreshBtnText) {
        refreshBtnText.textContent = "Refresh";
      }
      if (refreshIcon) {
        refreshIcon.classList.remove("animate-spin");
      }
    }, 500);
  }
}

// Auto-refresh interval (5 minutes = 300000 milliseconds)
let autoRefreshInterval = null;
const AUTO_REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Starts the auto-refresh interval.
 */
function startAutoRefresh() {
  // Clear any existing interval
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
  }

  // Set up new interval to refresh every 5 minutes
  autoRefreshInterval = setInterval(() => {
    // Only refresh if page is visible (optional optimization)
    if (document.visibilityState === "visible") {
      console.log("Auto-refreshing dashboard...");
      refreshDashboard(false); // false = auto-refresh, don't show button loading state
    }
  }, AUTO_REFRESH_INTERVAL_MS);

  console.log("Auto-refresh started (every 5 minutes)");
}

/**
 * Stops the auto-refresh interval.
 */
function stopAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
    console.log("Auto-refresh stopped");
  }
}

/**
 * Initializes dashboard functionality on page load.
 */
function initDashboard() {
  // Show loading state
  showRadarrLoadingState();
  showSonarrLoadingState();

  // Step 3.1: Handle API Errors - Try/catch with error state
  try {
    fetchDashboardStats()
      .then((data) => {
        console.log("Dashboard stats received:", data);
        updateRadarrCard(data);
        updateSonarrCard(data);
      })
      .catch((error) => {
        console.error("Error loading dashboard data:", error);
        // On error, show "offline" state with error indicator
        updateRadarrCard({
          radarr: {
            status: "offline",
            configured: false,
            version: null,
            total_movies: 0,
            missing_movies: 0,
            error: true
          }
        });
        updateSonarrCard({
          sonarr: {
            status: "offline",
            configured: false,
            version: null,
            total_series: 0,
            missing_episodes: 0,
            error: true
          }
        });
      });
  } catch (error) {
    // Handle any synchronous errors
    console.error("Critical error in initDashboard:", error);
    updateRadarrCard({
      radarr: {
        status: "offline",
        configured: false,
        version: null,
        total_movies: 0,
        missing_movies: 0,
        error: true
      }
    });
    updateSonarrCard({
      sonarr: {
        status: "offline",
        configured: false,
        version: null,
        total_series: 0,
        missing_episodes: 0,
        error: true
      }
    });
  }

  // Setup refresh button event listener
  const refreshBtn = document.getElementById("refresh-dashboard-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", refreshDashboard);
  }

  // Start auto-refresh
  startAutoRefresh();

  // Load recent jobs
  loadRecentJobs();

  // Load upcoming jobs
  loadUpcoming();
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initDashboard);

// Clean up intervals when page is unloaded to prevent memory leaks
window.addEventListener("beforeunload", () => {
  stopAutoRefresh();
  stopJobsPolling();
});

// Pause auto-refresh when page is hidden, resume when visible (optional optimization)
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    // Page is hidden - could pause auto-refresh here if desired
    // For now, we'll keep it running but it won't refresh when hidden
  } else {
    // Page is visible - ensure auto-refresh is running
    if (!autoRefreshInterval) {
      startAutoRefresh();
    }
  }
});
