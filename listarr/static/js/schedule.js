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
 * Update all relative time displays.
 */
function updateRelativeTimes() {
  document.querySelectorAll(".relative-time").forEach((element) => {
    const isoString = element.closest("td").getAttribute("data-last-run") || element.closest("td").getAttribute("data-next-run");
    if (isoString) {
      element.textContent = formatTimestamp(isoString);
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

    // Update status badges using server-rendered HTML
    let hasRunning = false;
    data.lists.forEach((list) => {
      const badge = document.querySelector(`tr[onclick*="${list.id}"] .status-badge`);
      if (badge && list.status_html) {
        // Replace badge with server-rendered HTML
        badge.outerHTML = list.status_html;
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
            timeSpan.textContent = formatTimestamp(list.next_run);
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
 * State for the edit modal.
 */
const modalState = {
  listId: null,
  useCustom: false,
};

/**
 * Open the schedule edit modal for a list.
 * @param {number} listId - List ID
 * @param {string} listName - List name for modal title
 * @param {string} currentCron - Current cron expression
 */
function openEditModal(listId, listName, currentCron) {
  modalState.listId = listId;
  modalState.useCustom = false;

  document.getElementById("modal-list-id").value = listId;
  document.getElementById("modal-title").textContent = `Edit Schedule: ${escapeHtml(listName)}`;

  // Try to match current cron to a preset
  const select = document.getElementById("modal-schedule-select");
  const customInput = document.getElementById("modal-cron-input");
  const customWrapper = document.getElementById("modal-cron-input-wrapper");
  const toggleBtn = document.getElementById("modal-toggle-custom");

  let matchedPreset = false;
  for (const option of select.options) {
    if (option.value === currentCron) {
      select.value = currentCron;
      matchedPreset = true;
      break;
    }
  }

  if (!matchedPreset && currentCron) {
    // Custom cron expression — show custom input
    modalState.useCustom = true;
    select.classList.add("hidden");
    customWrapper.classList.remove("hidden");
    customInput.value = currentCron;
    toggleBtn.textContent = "Use preset schedule";
  } else {
    select.classList.remove("hidden");
    customWrapper.classList.add("hidden");
    customInput.value = "";
    toggleBtn.textContent = "Use custom cron expression";
  }

  // Show modal
  document.getElementById("schedule-edit-modal").classList.remove("hidden");
}

/**
 * Close the schedule edit modal.
 */
function closeEditModal() {
  document.getElementById("schedule-edit-modal").classList.add("hidden");
  modalState.listId = null;
}

/**
 * Toggle between preset dropdown and custom cron input.
 */
function toggleCustomCron() {
  modalState.useCustom = !modalState.useCustom;
  const select = document.getElementById("modal-schedule-select");
  const customWrapper = document.getElementById("modal-cron-input-wrapper");
  const toggleBtn = document.getElementById("modal-toggle-custom");

  if (modalState.useCustom) {
    select.classList.add("hidden");
    customWrapper.classList.remove("hidden");
    toggleBtn.textContent = "Use preset schedule";
  } else {
    select.classList.remove("hidden");
    customWrapper.classList.add("hidden");
    toggleBtn.textContent = "Use custom cron expression";
  }
}

/**
 * Save the schedule from the modal.
 */
async function saveSchedule() {
  const listId = modalState.listId;
  if (!listId) return;

  let cronValue;
  if (modalState.useCustom) {
    cronValue = document.getElementById("modal-cron-input").value.trim();
  } else {
    cronValue = document.getElementById("modal-schedule-select").value;
  }

  const saveBtn = document.getElementById("modal-save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving...";

  try {
    const response = await fetch(`/api/schedule/${listId}/update`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ schedule_cron: cronValue }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP ${response.status}`);
    }

    const data = await response.json();
    if (!data.success) throw new Error(data.message || "Save failed");

    // Close modal and refresh status
    closeEditModal();
    await refreshScheduleStatus();

    // Reload page to get updated data (simplest approach for table update)
    window.location.reload();
  } catch (error) {
    console.error("Failed to save schedule:", error);
    if (window.showToast) {
      window.showToast(error.message || "Failed to save schedule", "error");
    }
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save";
  }
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

  // Close modal on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeEditModal();
  });
});

// Stop polling when page is hidden
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopPolling();
  } else if (state.hasRunningJobs) {
    startPolling();
  }
});
