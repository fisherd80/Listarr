// ----------------------
// Jobs Page JavaScript
// ----------------------

/**
 * State management for jobs page
 */
var state = {
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
};


/**
 * Load lists for the filter dropdown.
 */
async function loadLists() {
  try {
    var response = await fetch("/api/lists");
    if (!response.ok) throw new Error("HTTP " + response.status);
    var data = await response.json();

    var select = document.getElementById("filter-list");
    if (!select) return;

    // Clear existing options except "All Lists"
    select.innerHTML = '<option value="">All Lists</option>';

    // Add list options
    if (data.lists && Array.isArray(data.lists)) {
      for (var i = 0; i < data.lists.length; i++) {
        var list = data.lists[i];
        var option = document.createElement("option");
        option.value = list.id;
        option.textContent = list.name + " (" + list.target_service + ")";
        select.appendChild(option);
      }
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
    var params = new URLSearchParams({
      page: state.currentPage,
      per_page: state.perPage,
    });

    if (state.filters.list_id) {
      params.append("list_id", state.filters.list_id);
    }
    if (state.filters.status) {
      params.append("status", state.filters.status);
    }

    var response = await fetch("/api/activity?" + params);
    if (!response.ok) throw new Error("HTTP " + response.status);
    var data = await response.json();

    state.totalPages = data.pages || 1;
    state.totalJobs = data.total || 0;
    state.currentPage = data.current_page || 1;

    // Track running jobs
    state.runningJobs.clear();
    for (var i = 0; i < data.jobs.length; i++) {
      if (data.jobs[i].status === "running") {
        state.runningJobs.add(data.jobs[i].id);
      }
    }

    renderJobs(data.jobs);
    renderPaginationButtons();

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
  var tbody = document.getElementById("jobs-tbody");
  var loading = document.getElementById("jobs-loading");
  var empty = document.getElementById("jobs-empty");
  var tableContainer = document.getElementById("jobs-table-container");

  if (!tbody) return;

  // Hide loading
  if (loading) loading.classList.add("hidden");

  if (!jobs || jobs.length === 0) {
    if (empty) empty.classList.remove("hidden");
    if (tableContainer) tableContainer.classList.add("hidden");
    return;
  }

  if (empty) empty.classList.add("hidden");
  if (tableContainer) tableContainer.classList.remove("hidden");

  // Build rows HTML
  var rowsHtml = "";
  for (var i = 0; i < jobs.length; i++) {
    rowsHtml += renderJobRow(jobs[i]);
  }

  tbody.innerHTML = rowsHtml;

  // Attach event listeners to rerun buttons
  var rerunBtns = tbody.querySelectorAll("[data-rerun-job]");
  for (var j = 0; j < rerunBtns.length; j++) {
    rerunBtns[j].addEventListener("click", function () {
      var jobId = parseInt(this.getAttribute("data-rerun-job"));
      rerunJob(jobId, this);
    });
  }

  initOverflowMenus();
}

/**
 * Determine display status from raw job status.
 * Completed jobs with activity show "success"; zero-count completed show "no_change".
 * @param {Object} job - Job object
 * @returns {string} Display status key
 */
function getDisplayStatus(job) {
  if (job.status === "completed") {
    var hasActivity = (job.items_added > 0) || (job.items_skipped > 0) || (job.items_failed > 0);
    return hasActivity ? "success" : "no_change";
  }
  return job.status;
}

/**
 * Render compact result summary (N added / N skip format).
 * @param {Object} job - Job object
 * @returns {string} Text string for result column
 */
function renderResultCompact(job) {
  if (job.status === "running") {
    return "-";
  }
  var added = job.items_added || 0;
  var skipped = job.items_skipped || 0;
  if (added === 0 && skipped === 0 && job.status !== "failed") {
    return "\u2014";
  }
  return added + " added / " + skipped + " skip";
}

/**
 * Render overflow [...] actions menu for a job row.
 * @param {Object} job - Job object
 * @returns {string} HTML string for actions column
 */
function renderOverflowMenu(job) {
  var menuId = "job-" + job.id;
  var rerunItem = "";
  if (job.status === "failed") {
    rerunItem = '<button data-rerun-job="' + job.id + '" class="block w-full text-left px-3 py-1.5 text-sm text-text-base dark:text-gray-300 hover:bg-bg-table-head dark:hover:bg-bg-table-head">Rerun</button>';
  }
  return (
    '<div class="relative">' +
      '<button data-overflow-list="' + menuId + '" title="Actions" class="text-gray-400 hover:text-gray-100 focus:outline-none text-lg leading-none px-1">&#x2026;</button>' +
      '<div data-overflow-menu="' + menuId + '" class="hidden fixed z-50 w-32 bg-bg-panel dark:bg-bg-panel border border-gray-200 dark:border-border-subtle py-1" style="display:none;">' +
        '<a href="/activity/' + job.id + '" class="block w-full text-left px-3 py-1.5 text-sm text-text-base dark:text-gray-300 hover:bg-bg-table-head dark:hover:bg-bg-table-head">View</a>' +
        rerunItem +
      '</div>' +
    '</div>'
  );
}

/**
 * Render a single job row with 7 columns.
 * @param {Object} job - Job object
 * @returns {string} HTML string for the row
 */
function renderJobRow(job) {
  var displayStatus = getDisplayStatus(job);
  var statusBadge = renderStatusBadge(displayStatus);
  var result = renderResultCompact(job);
  var actions = renderOverflowMenu(job);
  var targetCell = job.target_service ? generateServiceBadge(job.target_service) : "-";

  return (
    '<tr data-job-row="' + job.id + '">' +
      '<td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">' +
        escapeHtml(job.list_name || ("List #" + job.list_id)) +
      '</td>' +
      '<td class="px-4 py-3 whitespace-nowrap">' +
        targetCell +
      '</td>' +
      '<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">' +
        formatTimestamp(job.started_at, "absolute") +
      '</td>' +
      '<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">' +
        formatDuration(job.duration) +
      '</td>' +
      '<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">' +
        result +
      '</td>' +
      '<td class="px-4 py-3 whitespace-nowrap">' +
        statusBadge +
      '</td>' +
      '<td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">' +
        actions +
      '</td>' +
    '</tr>'
  );
}

/**
 * Render status badge HTML matching server-side macro colors.
 * Colors match listarr/templates/macros/status.html exactly.
 * @param {string} status - Job status (running, completed, failed, pending)
 * @returns {string} HTML string for status badge
 */
function renderStatusBadge(status) {
  // Color map matches listarr/templates/macros/status.html exactly
  var statusConfig = {
    running: {
      color: "bg-primary/10 text-primary",
      label: "Running",
      icon: '<svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>',
    },
    completed: {
      color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      label: "Completed",
      icon: "",
    },
    failed: {
      color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
      label: "Failed",
      icon: "",
    },
    pending: {
      color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
      label: "Pending",
      icon: "",
    },
    success: {
      color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      label: "Success",
      icon: "",
    },
    no_change: {
      color: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
      label: "No Change",
      icon: "",
    },
  };

  var config = statusConfig[status] || {
    color: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
    label: status || "Unknown",
    icon: "",
  };

  return '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ' + config.color + '">' + config.icon + escapeHtml(config.label) + '</span>';
}

/**
 * Rerun a failed job.
 * @param {number} jobId - Job ID
 * @param {HTMLButtonElement} button - The button element
 */
async function rerunJob(jobId, button) {
  button.disabled = true;
  var originalText = button.textContent;
  button.textContent = "Starting...";

  try {
    var response = await fetch("/api/activity/" + jobId + "/rerun", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    if (!response.ok) {
      var errorData = await response.json().catch(function () { return {}; });
      throw new Error(errorData.message || "HTTP " + response.status);
    }
    var data = await response.json();

    if (response.ok && data.success) {
      showToast("Job restarted successfully", "success");
      // Reload jobs to show the new running job
      loadJobs();
    } else {
      throw new Error(data.message || "Failed to rerun job");
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
  var listSelect = document.getElementById("filter-list");
  var statusSelect = document.getElementById("filter-status");

  state.filters.list_id = listSelect ? listSelect.value : "";
  state.filters.status = statusSelect ? statusSelect.value : "";
  state.currentPage = 1;

  loadJobs();
}

/**
 * Navigate to a specific page.
 * @param {number} n - Target page number
 */
function goToPage(n) {
  if (n >= 1 && n <= state.totalPages) {
    state.currentPage = n;
    loadJobs();
  }
}

/**
 * Render numbered pagination buttons in div#pagination-buttons.
 */
function renderPaginationButtons() {
  var startEl = document.getElementById("pagination-start");
  var endEl = document.getElementById("pagination-end");
  var totalEl = document.getElementById("pagination-total");

  var start = state.totalJobs === 0 ? 0 : (state.currentPage - 1) * state.perPage + 1;
  var end = Math.min(state.currentPage * state.perPage, state.totalJobs);

  if (startEl) startEl.textContent = start;
  if (endEl) endEl.textContent = end;
  if (totalEl) totalEl.textContent = state.totalJobs;

  var container = document.getElementById("pagination-buttons");
  if (!container) return;

  if (state.totalPages <= 1) {
    container.innerHTML = "";
    return;
  }

  var MAX_VISIBLE = 5;
  var half = Math.floor(MAX_VISIBLE / 2);
  var pageStart = Math.max(1, state.currentPage - half);
  var pageEnd = Math.min(state.totalPages, pageStart + MAX_VISIBLE - 1);
  if ((pageEnd - pageStart) < MAX_VISIBLE - 1) {
    pageStart = Math.max(1, pageEnd - MAX_VISIBLE + 1);
  }

  var activeClass = "bg-primary text-white border border-gray-600 rounded inline-flex items-center px-2.5 py-1.5 text-xs";
  var inactiveClass = "text-gray-300 hover:bg-gray-600 border border-gray-600 rounded inline-flex items-center px-2.5 py-1.5 text-xs";

  var html = "";

  // First page button
  html += '<button data-page="1"' + (state.currentPage === 1 ? ' disabled' : '') + ' class="' + inactiveClass + '">&laquo;</button>';
  // Prev button
  html += '<button data-page="' + (state.currentPage - 1) + '"' + (state.currentPage === 1 ? ' disabled' : '') + ' class="' + inactiveClass + '">&lsaquo;</button>';

  // Numbered page buttons
  for (var p = pageStart; p <= pageEnd; p++) {
    var cls = (p === state.currentPage) ? activeClass : inactiveClass;
    html += '<button data-page="' + p + '" class="' + cls + '">' + p + '</button>';
  }

  // Next button
  html += '<button data-page="' + (state.currentPage + 1) + '"' + (state.currentPage === state.totalPages ? ' disabled' : '') + ' class="' + inactiveClass + '">&rsaquo;</button>';
  // Last page button
  html += '<button data-page="' + state.totalPages + '"' + (state.currentPage === state.totalPages ? ' disabled' : '') + ' class="' + inactiveClass + '">&raquo;</button>';

  container.innerHTML = html;

  // Attach click listeners to enabled page buttons
  var pageBtns = container.querySelectorAll("button[data-page]:not([disabled])");
  for (var i = 0; i < pageBtns.length; i++) {
    pageBtns[i].addEventListener("click", function () {
      goToPage(parseInt(this.getAttribute("data-page")));
    });
  }
}

/**
 * Close all open overflow menus.
 */
function closeAllOverflowMenus() {
  var menus = document.querySelectorAll("div[data-overflow-menu]");
  for (var i = 0; i < menus.length; i++) {
    menus[i].style.display = "none";
  }
}

/**
 * Initialize overflow menu toggle logic.
 * Each [...] button toggles its associated dropdown; clicking outside closes all.
 */
function initOverflowMenus() {
  var buttons = document.querySelectorAll("button[data-overflow-list]");
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener("click", function (e) {
      e.stopPropagation();
      var listId = this.getAttribute("data-overflow-list");
      var menu = document.querySelector('div[data-overflow-menu="' + listId + '"]');
      if (!menu) { return; }
      var isOpen = menu.style.display === "block";
      closeAllOverflowMenus();
      if (!isOpen) {
        var rect = this.getBoundingClientRect();
        menu.style.display = "block";
        var menuW = menu.offsetWidth;
        var menuH = menu.offsetHeight;
        var left = rect.right - menuW;
        if (left < 4) { left = 4; }
        if (left + menuW > window.innerWidth - 4) { left = window.innerWidth - menuW - 4; }
        menu.style.left = left + "px";
        var top = rect.bottom + 4;
        if (top + menuH > window.innerHeight) {
          top = rect.top - menuH - 4;
        }
        menu.style.top = top + "px";
      }
    });
  }

  document.addEventListener("click", closeAllOverflowMenus);
  window.addEventListener("scroll", closeAllOverflowMenus, true);
}

/**
 * Start polling for running job updates.
 */
function startPolling() {
  if (state.pollingInterval) return; // Already polling

  state.pollingInterval = setInterval(async function () {
    if (document.visibilityState !== "visible") return;
    if (state.runningJobs.size === 0) {
      stopPolling();
      return;
    }

    try {
      var response = await fetch("/api/activity/running");
      if (!response.ok) return;
      var data = await response.json();

      var currentlyRunning = new Set();
      for (var i = 0; i < data.running_jobs.length; i++) {
        currentlyRunning.add(data.running_jobs[i].job_id);
      }

      // Check if any running jobs have completed
      var needsReload = false;
      state.runningJobs.forEach(function (jobId) {
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
  var loading = document.getElementById("jobs-loading");
  var empty = document.getElementById("jobs-empty");
  var tableContainer = document.getElementById("jobs-table-container");
  if (loading) loading.classList.remove("hidden");
  if (empty) empty.classList.add("hidden");
  if (tableContainer) tableContainer.classList.add("hidden");
}

/**
 * Show empty state.
 */
function showEmpty() {
  var loading = document.getElementById("jobs-loading");
  var empty = document.getElementById("jobs-empty");
  var tableContainer = document.getElementById("jobs-table-container");
  if (loading) loading.classList.add("hidden");
  if (empty) empty.classList.remove("hidden");
  if (tableContainer) tableContainer.classList.add("hidden");
}

/**
 * Initialize the jobs page.
 */
function initJobsPage() {
  // Load lists for filter dropdown
  loadLists();

  // Load initial jobs
  loadJobs();

  // Auto-apply filters on dropdown change
  var filterList = document.getElementById("filter-list");
  var filterStatus = document.getElementById("filter-status");
  if (filterList) filterList.addEventListener("change", applyFilters);
  if (filterStatus) filterStatus.addEventListener("change", applyFilters);
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initJobsPage);

// Stop polling on page unload
window.addEventListener("beforeunload", stopPolling);

// Pause/resume polling on tab visibility change
document.addEventListener("visibilitychange", function () {
  if (document.hidden) {
    stopPolling();
  } else if (state.runningJobs.size > 0) {
    startPolling();
  }
});
