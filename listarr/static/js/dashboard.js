// Dashboard JavaScript

let jobsPollingInterval = null;
const JOBS_POLLING_INTERVAL_MS = 2000; // 2 seconds

// Offline/error fallback data used in multiple error handlers
const OFFLINE_DATA = {
  radarr: {
    status: "offline",
    configured: false,
    version: null,
    total_movies: 0,
    missing_movies: 0,
    error: true,
  },
  sonarr: {
    status: "offline",
    configured: false,
    version: null,
    total_series: 0,
    missing_episodes: 0,
    error: true,
  },
};

// Service card configuration for parameterized updates
const SERVICE_CONFIG = {
  radarr: {
    statusId: "radarr-status",
    stats: [
      { id: "radarr-total-movies", key: "total_movies", needsOnline: true },
      { id: "radarr-missing-movies", key: "missing_movies", needsOnline: true },
      {
        id: "radarr-added-by-listarr",
        key: "added_by_listarr",
        needsOnline: false,
      },
    ],
  },
  sonarr: {
    statusId: "sonarr-status",
    stats: [
      { id: "sonarr-total-series", key: "total_series", needsOnline: true },
      {
        id: "sonarr-missing-episodes",
        key: "missing_episodes",
        needsOnline: true,
      },
      {
        id: "sonarr-added-by-listarr",
        key: "added_by_listarr",
        needsOnline: false,
      },
    ],
  },
};

/** Fetches recent jobs from the API. */
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
      return [];
    });
}

/** Formats job summary based on status. */
function formatJobSummary(job) {
  if (!job) return "\u2014";

  switch (job.status) {
    case "running":
      return '<span class="inline-flex items-center"><svg class="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Running...</span>';
    case "completed":
      const added = job.items_added || 0;
      const skipped = job.items_skipped || 0;
      return `${added} added, ${skipped} skipped`;
    case "failed":
      const errMsg = job.error_message || "Unknown error";
      const truncated =
        errMsg.length > 50 ? errMsg.substring(0, 47) + "..." : errMsg;
      return escapeHtml(truncated);
    case "pending":
      return "Pending...";
    default:
      return "\u2014";
  }
}

/** Gets Tailwind CSS color class for a job status. */
function getStatusColorClass(status) {
  switch (status) {
    case "completed":
      return "text-green-600 dark:text-green-400";
    case "failed":
      return "text-red-600 dark:text-red-400";
    case "running":
      return "text-yellow-600 dark:text-yellow-400";
    case "pending":
    default:
      return "text-gray-600 dark:text-gray-400";
  }
}

/** Starts/stops polling based on whether any jobs are running. */
function checkAndManagePolling(jobs) {
  const hasRunningJobs = jobs && jobs.some((job) => job.status === "running");

  if (hasRunningJobs && !jobsPollingInterval) {
    startJobsPolling();
  } else if (!hasRunningJobs && jobsPollingInterval) {
    stopJobsPolling();
  }
}

/** Starts polling for job updates. */
function startJobsPolling() {
  if (jobsPollingInterval) {
    return; // Already polling
  }

  console.log("Starting jobs polling (running job detected)");
  jobsPollingInterval = setInterval(() => {
    if (document.visibilityState !== "visible") return;

    fetchRecentJobs()
      .then((jobs) => {
        updateJobsTable(jobs);
        checkAndManagePolling(jobs);
      })
      .catch((error) => {
        console.error("Error polling jobs:", error);
      });

    loadUpcoming();
  }, JOBS_POLLING_INTERVAL_MS);
}

/** Stops polling for job updates. */
function stopJobsPolling() {
  if (jobsPollingInterval) {
    console.log("Stopping jobs polling (no running jobs)");
    clearInterval(jobsPollingInterval);
    jobsPollingInterval = null;
  }
}

/** Loads and displays recent jobs. */
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

/** Fetches upcoming scheduled jobs from the API. */
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
      return { upcoming: [], scheduler_paused: false };
    });
}

/** Updates the Upcoming widget with fetched data. */
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

    listItem.innerHTML = `
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
          ${escapeHtml(job.list_name)}
        </p>
        <p class="text-xs text-gray-500 dark:text-gray-400">
          ${escapeHtml(job.next_run_relative)}
        </p>
      </div>
      <span class="ml-2">${generateServiceBadge(job.service)}</span>
    `;

    upcomingList.appendChild(listItem);
  });
}

/** Loads and displays upcoming scheduled jobs. */
function loadUpcoming() {
  fetchUpcomingJobs()
    .then((data) => {
      updateUpcomingWidget(data);
    })
    .catch((error) => {
      console.error("Error loading upcoming jobs:", error);
      updateUpcomingWidget({ upcoming: [], scheduler_paused: false });
    });
}

/** Updates the jobs table with fetched jobs data. */
function updateJobsTable(jobs) {
  const tableBody = document.getElementById("recent-jobs-table-body");
  if (!tableBody) {
    console.warn("Jobs table body not found");
    return;
  }

  tableBody.innerHTML = "";

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

  jobs.forEach((job) => {
    const row = document.createElement("tr");
    const statusColorClass = getStatusColorClass(job.status);
    const executedAt = formatTimestamp(job.started_at);
    const summary = formatJobSummary(job);
    const service = job.target_service ? capitalize(job.target_service) : "\u2014";
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

/** Fetches dashboard statistics from the API. */
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
      return OFFLINE_DATA;
    });
}

/** Updates a status badge element with appropriate styling. */
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

  element.className = `text-xs px-2 py-1 rounded-full ${badgeClass}`;
  element.textContent = badgeText;
}

/** Shows loading state on a service card (radarr or sonarr). */
function showServiceLoadingState(service) {
  const svcConfig = SERVICE_CONFIG[service];
  if (!svcConfig) return;

  // Show skeleton, hide stats
  const skeleton = document.getElementById(`${service}-stats-skeleton`);
  const stats = document.getElementById(`${service}-stats`);
  if (skeleton) skeleton.classList.remove("hidden");
  if (stats) stats.classList.add("hidden");

  const statusEl = document.getElementById(svcConfig.statusId);
  if (statusEl) {
    statusEl.textContent = "Loading...";
    statusEl.className =
      "text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
  }
}

/** Updates a service card with fetched statistics. */
function updateServiceCard(data, service) {
  if (!data || typeof data !== "object") {
    data = {};
  }

  const serviceData = data[service] || {};
  const status = serviceData.status || "not_configured";
  const svcConfig = SERVICE_CONFIG[service];
  if (!svcConfig) return;

  // Hide skeleton, show stats
  const skeleton = document.getElementById(`${service}-stats-skeleton`);
  const stats = document.getElementById(`${service}-stats`);
  if (skeleton) skeleton.classList.add("hidden");
  if (stats) stats.classList.remove("hidden");

  const statusEl = document.getElementById(svcConfig.statusId);
  if (statusEl) {
    updateStatusBadge(statusEl, status);
  }

  svcConfig.stats.forEach((stat) => {
    const el = document.getElementById(stat.id);
    if (!el) return;

    const value = serviceData[stat.key];
    if (stat.needsOnline && status !== "online") {
      el.textContent = "\u2014";
    } else if (value !== undefined && value !== null) {
      const count = parseInt(value, 10);
      el.textContent = isNaN(count) ? "\u2014" : count;
    } else {
      el.textContent = "\u2014";
    }
  });
}

/** Refreshes dashboard data (isManual controls button loading state). */
function refreshDashboard(isManual = true) {
  const refreshBtn = document.getElementById("refresh-dashboard-btn");
  const refreshIcon = document.getElementById("refresh-icon");
  const refreshBtnText = document.getElementById("refresh-btn-text");

  if (isManual) {
    if (refreshBtn) refreshBtn.disabled = true;
    if (refreshBtnText) refreshBtnText.textContent = "Refreshing...";
    if (refreshIcon) refreshIcon.classList.add("animate-spin");
  }

  showServiceLoadingState("radarr");
  showServiceLoadingState("sonarr");

  fetchDashboardStats(true)
    .then((data) => {
      console.log("Dashboard stats refreshed:", data);
      updateServiceCard(data, "radarr");
      updateServiceCard(data, "sonarr");
    })
    .catch((error) => {
      console.error("Error refreshing dashboard data:", error);
      updateServiceCard(OFFLINE_DATA, "radarr");
      updateServiceCard(OFFLINE_DATA, "sonarr");
    });

  loadRecentJobs();
  loadUpcoming();

  if (isManual) {
    setTimeout(() => {
      if (refreshBtn) refreshBtn.disabled = false;
      if (refreshBtnText) refreshBtnText.textContent = "Refresh";
      if (refreshIcon) refreshIcon.classList.remove("animate-spin");
    }, 500);
  }
}

// Auto-refresh interval (5 minutes = 300000 milliseconds)
let autoRefreshInterval = null;
const AUTO_REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

/** Starts the auto-refresh interval. */
function startAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
  }

  autoRefreshInterval = setInterval(() => {
    if (document.visibilityState === "visible") {
      console.log("Auto-refreshing dashboard...");
      refreshDashboard(false);
    }
  }, AUTO_REFRESH_INTERVAL_MS);

  console.log("Auto-refresh started (every 5 minutes)");
}

/** Stops the auto-refresh interval. */
function stopAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
    console.log("Auto-refresh stopped");
  }
}

/** Initializes dashboard functionality on page load. */
function initDashboard() {
  showServiceLoadingState("radarr");
  showServiceLoadingState("sonarr");

  fetchDashboardStats()
    .then((data) => {
      console.log("Dashboard stats received:", data);
      updateServiceCard(data, "radarr");
      updateServiceCard(data, "sonarr");
    })
    .catch((error) => {
      console.error("Error loading dashboard data:", error);
      updateServiceCard(OFFLINE_DATA, "radarr");
      updateServiceCard(OFFLINE_DATA, "sonarr");
    });

  const refreshBtn = document.getElementById("refresh-dashboard-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", refreshDashboard);
  }

  startAutoRefresh();
  loadRecentJobs();
  loadUpcoming();
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initDashboard);

// Clean up intervals when page is unloaded to prevent memory leaks
window.addEventListener("beforeunload", () => {
  stopAutoRefresh();
  stopJobsPolling();
});

// Resume auto-refresh when page becomes visible again
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && !autoRefreshInterval) {
    startAutoRefresh();
  }
});
