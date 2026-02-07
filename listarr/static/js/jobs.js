// ----------------------
// Jobs Page JavaScript
// ----------------------

/**
 * State management for jobs page
 */
const state = {
  currentPage: 1,
  totalPages: 1,
  totalJobs: 0,
  perPage: 25,
  filters: {
    list_id: "",
    status: "",
  },
  runningJobs: new Set(),
  pollingInterval: null,
  expandedRows: new Set(),
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
 * Escape HTML to prevent XSS.
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtmlLocal(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Format ISO date string to local readable format.
 * @param {string} isoString - ISO date string
 * @returns {string} Formatted date string
 */
function formatDate(isoString) {
  if (!isoString) return "-";
  try {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      year: "numeric",
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
 * Format duration in seconds to human readable format.
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration string
 */
function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "-";
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Load lists for the filter dropdown.
 */
async function loadLists() {
  try {
    const response = await fetch("/api/lists");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    const select = document.getElementById("filter-list");
    if (!select) return;

    // Clear existing options except "All Lists"
    select.innerHTML = '<option value="">All Lists</option>';

    // Add list options
    if (data.lists && Array.isArray(data.lists)) {
      data.lists.forEach((list) => {
        const option = document.createElement("option");
        option.value = list.id;
        option.textContent = `${list.name} (${list.target_service})`;
        select.appendChild(option);
      });
    }
  } catch (error) {
    console.error("Error loading lists:", error);
  }
}

/**
 * Load jobs from the API with current filters and pagination.
 */
async function loadJobs() {
  showLoading();

  try {
    const params = new URLSearchParams({
      page: state.currentPage,
      per_page: state.perPage,
    });

    if (state.filters.list_id) {
      params.append("list_id", state.filters.list_id);
    }
    if (state.filters.status) {
      params.append("status", state.filters.status);
    }

    const response = await fetch(`/api/jobs?${params}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    state.totalPages = data.pages || 1;
    state.totalJobs = data.total || 0;
    state.currentPage = data.current_page || 1;

    // Track running jobs
    state.runningJobs.clear();
    data.jobs.forEach((job) => {
      if (job.status === "running") {
        state.runningJobs.add(job.id);
      }
    });

    renderJobs(data.jobs);
    updatePagination();

    // Start polling if there are running jobs
    if (state.runningJobs.size > 0) {
      startPolling();
    } else {
      stopPolling();
    }
  } catch (error) {
    console.error("Error loading jobs:", error);
    showToast("Failed to load jobs", "error");
    showEmpty();
  }
}

/**
 * Render jobs in the table.
 * @param {Array} jobs - Array of job objects
 */
function renderJobs(jobs) {
  const tbody = document.getElementById("jobs-tbody");
  const loading = document.getElementById("jobs-loading");
  const empty = document.getElementById("jobs-empty");
  const tableContainer = document.getElementById("jobs-table-container");

  if (!tbody) return;

  // Hide loading
  loading?.classList.add("hidden");

  if (!jobs || jobs.length === 0) {
    empty?.classList.remove("hidden");
    tableContainer?.classList.add("hidden");
    return;
  }

  empty?.classList.add("hidden");
  tableContainer?.classList.remove("hidden");

  // Build rows HTML
  let rowsHtml = "";
  jobs.forEach((job) => {
    const isExpanded = state.expandedRows.has(job.id);
    rowsHtml += renderJobRow(job, isExpanded);
  });

  tbody.innerHTML = rowsHtml;

  // Attach event listeners to expand buttons
  tbody.querySelectorAll("[data-expand-job]").forEach((btn) => {
    btn.addEventListener("click", function () {
      const jobId = parseInt(this.getAttribute("data-expand-job"));
      toggleExpand(jobId);
    });
  });

  // Attach event listeners to rerun buttons
  tbody.querySelectorAll("[data-rerun-job]").forEach((btn) => {
    btn.addEventListener("click", function () {
      const jobId = parseInt(this.getAttribute("data-rerun-job"));
      rerunJob(jobId, this);
    });
  });
}

/**
 * Render a single job row.
 * @param {Object} job - Job object
 * @param {boolean} isExpanded - Whether the row is expanded
 * @returns {string} HTML string for the row
 */
function renderJobRow(job, isExpanded) {
  const expandIcon = isExpanded
    ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />'
    : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />';

  const statusBadge = renderStatus(job.status);
  const results = renderResults(job);
  const actions = renderActions(job);

  let row = `
    <tr data-job-row="${job.id}">
      <td class="px-4 py-4 whitespace-nowrap">
        <button
          type="button"
          data-expand-job="${job.id}"
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none"
        >
          <svg class="w-5 h-5 transition-transform ${isExpanded ? "rotate-90" : ""}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            ${expandIcon}
          </svg>
        </button>
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
        ${escapeHtmlLocal(job.list_name || `List #${job.list_id}`)}
      </td>
      <td class="px-6 py-4 whitespace-nowrap">
        ${statusBadge}
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
        ${formatDate(job.started_at)}
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
        ${formatDuration(job.duration)}
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
        ${results}
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        ${actions}
      </td>
    </tr>
  `;

  // Add expanded details row if expanded
  if (isExpanded) {
    row += `
      <tr data-job-details="${job.id}" class="bg-gray-50 dark:bg-gray-900">
        <td colspan="7" class="px-6 py-4">
          <div id="job-details-${job.id}" class="text-sm">
            <div class="text-center py-4">
              <svg class="animate-spin h-5 w-5 mx-auto text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p class="mt-1 text-gray-500 dark:text-gray-400">Loading details...</p>
            </div>
          </div>
        </td>
      </tr>
    `;
  }

  return row;
}

/**
 * Render status badge.
 * @param {string} status - Job status
 * @returns {string} HTML string for status badge
 */
function renderStatus(status) {
  const statusConfig = {
    running: {
      bg: "bg-blue-100 dark:bg-blue-900",
      text: "text-blue-800 dark:text-blue-200",
      label: "Running",
      icon: '<svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>',
    },
    completed: {
      bg: "bg-green-100 dark:bg-green-900",
      text: "text-green-800 dark:text-green-200",
      label: "Completed",
      icon: "",
    },
    failed: {
      bg: "bg-red-100 dark:bg-red-900",
      text: "text-red-800 dark:text-red-200",
      label: "Failed",
      icon: "",
    },
  };

  const config = statusConfig[status] || {
    bg: "bg-gray-100 dark:bg-gray-700",
    text: "text-gray-800 dark:text-gray-300",
    label: status || "Unknown",
    icon: "",
  };

  return `
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}">
      ${config.icon}${escapeHtmlLocal(config.label)}
    </span>
  `;
}

/**
 * Render results summary (added/skipped/failed counts).
 * @param {Object} job - Job object
 * @returns {string} HTML string for results
 */
function renderResults(job) {
  if (job.status === "running") {
    return "-";
  }

  const added = job.items_added || 0;
  const skipped = job.items_skipped || 0;
  const failed = job.items_failed || 0;

  if (added === 0 && skipped === 0 && failed === 0) {
    return "-";
  }

  const parts = [];
  if (added > 0) {
    parts.push(`<span class="text-green-600 dark:text-green-400">${added} added</span>`);
  }
  if (skipped > 0) {
    parts.push(`<span class="text-gray-500 dark:text-gray-400">${skipped} skipped</span>`);
  }
  if (failed > 0) {
    parts.push(`<span class="text-red-600 dark:text-red-400">${failed} failed</span>`);
  }

  return parts.join(", ");
}

/**
 * Render actions column (rerun button for failed jobs).
 * @param {Object} job - Job object
 * @returns {string} HTML string for actions
 */
function renderActions(job) {
  if (job.status !== "failed") {
    return "-";
  }

  return `
    <button
      type="button"
      data-rerun-job="${job.id}"
      class="text-primary hover:text-indigo-900 dark:hover:text-indigo-300"
    >
      Rerun
    </button>
  `;
}

/**
 * Toggle row expansion to show job details.
 * @param {number} jobId - Job ID
 */
async function toggleExpand(jobId) {
  if (state.expandedRows.has(jobId)) {
    state.expandedRows.delete(jobId);
    // Remove details row
    const detailsRow = document.querySelector(`[data-job-details="${jobId}"]`);
    if (detailsRow) {
      detailsRow.remove();
    }
    // Update expand icon
    const btn = document.querySelector(`[data-expand-job="${jobId}"]`);
    if (btn) {
      btn.querySelector("svg").classList.remove("rotate-90");
      btn.querySelector("svg").innerHTML =
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />';
    }
  } else {
    state.expandedRows.add(jobId);
    // Add details row
    const jobRow = document.querySelector(`[data-job-row="${jobId}"]`);
    if (jobRow) {
      // Update expand icon
      const btn = document.querySelector(`[data-expand-job="${jobId}"]`);
      if (btn) {
        btn.querySelector("svg").classList.add("rotate-90");
        btn.querySelector("svg").innerHTML =
          '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />';
      }

      // Insert details row
      const detailsRow = document.createElement("tr");
      detailsRow.setAttribute("data-job-details", jobId);
      detailsRow.className = "bg-gray-50 dark:bg-gray-900";
      detailsRow.innerHTML = `
        <td colspan="7" class="px-6 py-4">
          <div id="job-details-${jobId}" class="text-sm">
            <div class="text-center py-4">
              <svg class="animate-spin h-5 w-5 mx-auto text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p class="mt-1 text-gray-500 dark:text-gray-400">Loading details...</p>
            </div>
          </div>
        </td>
      `;
      jobRow.after(detailsRow);

      // Load job details
      loadJobDetails(jobId);
    }
  }
}

/**
 * Load and render job details with items.
 * @param {number} jobId - Job ID
 */
async function loadJobDetails(jobId) {
  const container = document.getElementById(`job-details-${jobId}`);
  if (!container) return;

  try {
    const response = await fetch(`/api/jobs/${jobId}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const job = await response.json();

    container.innerHTML = renderJobDetails(job);
  } catch (error) {
    console.error(`Error loading job details for ${jobId}:`, error);
    container.innerHTML = `
      <div class="text-red-500 dark:text-red-400">
        Failed to load job details
      </div>
    `;
  }
}

/**
 * Render job details with items table.
 * @param {Object} job - Job object with items
 * @returns {string} HTML string for job details
 */
function renderJobDetails(job) {
  let html = '<div class="space-y-4">';

  // Job metadata
  html += `
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
      <div>
        <span class="text-gray-500 dark:text-gray-400">Triggered By:</span>
        <span class="ml-1 text-gray-900 dark:text-gray-100">${escapeHtmlLocal(job.triggered_by || "manual")}</span>
      </div>
      <div>
        <span class="text-gray-500 dark:text-gray-400">Items Found:</span>
        <span class="ml-1 text-gray-900 dark:text-gray-100">${job.items_found || 0}</span>
      </div>
      <div>
        <span class="text-gray-500 dark:text-gray-400">Retry Count:</span>
        <span class="ml-1 text-gray-900 dark:text-gray-100">${job.retry_count || 0}</span>
      </div>
      ${
        job.completed_at
          ? `
      <div>
        <span class="text-gray-500 dark:text-gray-400">Completed:</span>
        <span class="ml-1 text-gray-900 dark:text-gray-100">${formatDate(job.completed_at)}</span>
      </div>
      `
          : ""
      }
    </div>
  `;

  // Error message if failed
  if (job.status === "failed" && job.error_message) {
    html += `
      <div class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-3">
        <span class="font-medium text-red-800 dark:text-red-200">Error:</span>
        <span class="text-red-700 dark:text-red-300">${escapeHtmlLocal(job.error_message)}</span>
      </div>
    `;
  }

  // Items table
  if (job.items && job.items.length > 0) {
    html += `
      <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-100 dark:bg-gray-800">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Title</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">TMDB ID</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Message</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
    `;

    job.items.forEach((item) => {
      const itemStatus = item.status || "unknown";
      let statusClass = "text-gray-500 dark:text-gray-400";
      if (itemStatus === "added") {
        statusClass = "text-green-600 dark:text-green-400";
      } else if (itemStatus === "skipped") {
        statusClass = "text-yellow-600 dark:text-yellow-400";
      } else if (itemStatus === "failed") {
        statusClass = "text-red-600 dark:text-red-400";
      }

      html += `
        <tr>
          <td class="px-4 py-2 text-sm text-gray-900 dark:text-gray-100">${escapeHtmlLocal(item.title || "Unknown")}</td>
          <td class="px-4 py-2 text-sm text-gray-500 dark:text-gray-400">${item.tmdb_id || "-"}</td>
          <td class="px-4 py-2 text-sm ${statusClass} capitalize">${escapeHtmlLocal(itemStatus)}</td>
          <td class="px-4 py-2 text-sm text-gray-500 dark:text-gray-400">${escapeHtmlLocal(item.message || "-")}</td>
        </tr>
      `;
    });

    html += `
          </tbody>
        </table>
      </div>
    `;
  } else if (job.status !== "running") {
    html += `
      <div class="text-gray-500 dark:text-gray-400 text-center py-4">
        No items recorded for this job.
      </div>
    `;
  }

  html += "</div>";
  return html;
}

/**
 * Rerun a failed job.
 * @param {number} jobId - Job ID
 * @param {HTMLButtonElement} button - The button element
 */
async function rerunJob(jobId, button) {
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = "Starting...";

  try {
    const response = await fetch(`/api/jobs/${jobId}/rerun`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    const data = await response.json();

    if (response.ok && data.success) {
      showToast("Job restarted successfully", "success");
      // Reload jobs to show the new running job
      loadJobs();
    } else {
      throw new Error(data.error || "Failed to rerun job");
    }
  } catch (error) {
    console.error("Error rerunning job:", error);
    showToast(error.message || "Failed to rerun job", "error");
    button.disabled = false;
    button.textContent = originalText;
  }
}

/**
 * Apply filters and reload jobs.
 */
function applyFilters() {
  const listSelect = document.getElementById("filter-list");
  const statusSelect = document.getElementById("filter-status");

  state.filters.list_id = listSelect?.value || "";
  state.filters.status = statusSelect?.value || "";
  state.currentPage = 1;

  loadJobs();
}

/**
 * Clear all job history with confirmation.
 */
async function clearAllJobs() {
  if (!confirm("Are you sure you want to clear all job history? Running jobs will not be affected.")) {
    return;
  }

  const button = document.getElementById("clear-all-btn");
  if (button) {
    button.disabled = true;
    button.textContent = "Clearing...";
  }

  try {
    const response = await fetch("/api/jobs/clear", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    const data = await response.json();

    if (response.ok && data.success) {
      showToast(`Cleared ${data.deleted_count} jobs`, "success");
      loadJobs();
    } else {
      throw new Error(data.error || "Failed to clear jobs");
    }
  } catch (error) {
    console.error("Error clearing jobs:", error);
    showToast(error.message || "Failed to clear jobs", "error");
  } finally {
    if (button) {
      button.disabled = false;
      button.innerHTML = `
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        Clear All
      `;
    }
  }
}

/**
 * Update pagination controls based on current state.
 */
function updatePagination() {
  const start = state.totalJobs === 0 ? 0 : (state.currentPage - 1) * state.perPage + 1;
  const end = Math.min(state.currentPage * state.perPage, state.totalJobs);

  document.getElementById("pagination-start").textContent = start;
  document.getElementById("pagination-end").textContent = end;
  document.getElementById("pagination-total").textContent = state.totalJobs;
  document.getElementById("pagination-current").textContent = state.currentPage;
  document.getElementById("pagination-pages").textContent = state.totalPages;

  const prevBtn = document.getElementById("pagination-prev");
  const nextBtn = document.getElementById("pagination-next");

  if (prevBtn) {
    prevBtn.disabled = state.currentPage <= 1;
  }
  if (nextBtn) {
    nextBtn.disabled = state.currentPage >= state.totalPages;
  }
}

/**
 * Change to a different page.
 * @param {number} delta - Page change (+1 for next, -1 for previous)
 */
function changePage(delta) {
  const newPage = state.currentPage + delta;
  if (newPage >= 1 && newPage <= state.totalPages) {
    state.currentPage = newPage;
    loadJobs();
  }
}

/**
 * Start polling for running job updates.
 */
function startPolling() {
  if (state.pollingInterval) return; // Already polling

  state.pollingInterval = setInterval(async () => {
    if (state.runningJobs.size === 0) {
      stopPolling();
      return;
    }

    try {
      const response = await fetch("/api/jobs/running");
      if (!response.ok) return;
      const data = await response.json();

      const currentlyRunning = new Set(data.running_jobs.map((j) => j.job_id));

      // Check if any running jobs have completed
      let needsReload = false;
      state.runningJobs.forEach((jobId) => {
        if (!currentlyRunning.has(jobId)) {
          needsReload = true;
        }
      });

      if (needsReload) {
        // Jobs have completed, reload the list
        loadJobs();
      }
    } catch (error) {
      console.error("Error polling running jobs:", error);
    }
  }, 3000); // Poll every 3 seconds
}

/**
 * Stop polling for running job updates.
 */
function stopPolling() {
  if (state.pollingInterval) {
    clearInterval(state.pollingInterval);
    state.pollingInterval = null;
  }
}

/**
 * Show loading state.
 */
function showLoading() {
  document.getElementById("jobs-loading")?.classList.remove("hidden");
  document.getElementById("jobs-empty")?.classList.add("hidden");
  document.getElementById("jobs-table-container")?.classList.add("hidden");
}

/**
 * Show empty state.
 */
function showEmpty() {
  document.getElementById("jobs-loading")?.classList.add("hidden");
  document.getElementById("jobs-empty")?.classList.remove("hidden");
  document.getElementById("jobs-table-container")?.classList.add("hidden");
}

/**
 * Initialize the jobs page.
 */
function initJobsPage() {
  // Load lists for filter dropdown
  loadLists();

  // Load initial jobs
  loadJobs();

  // Attach event listeners
  document.getElementById("apply-filters-btn")?.addEventListener("click", applyFilters);
  document.getElementById("clear-all-btn")?.addEventListener("click", clearAllJobs);
  document.getElementById("pagination-prev")?.addEventListener("click", () => changePage(-1));
  document.getElementById("pagination-next")?.addEventListener("click", () => changePage(1));

  // Allow Enter key to apply filters
  document.getElementById("filter-list")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") applyFilters();
  });
  document.getElementById("filter-status")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") applyFilters();
  });
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initJobsPage);

// Stop polling on page unload
window.addEventListener("beforeunload", stopPolling);
