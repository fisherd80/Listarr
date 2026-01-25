// ----------------------
// Lists JavaScript - Toggle Functionality
// ----------------------

/**
 * Gets the CSRF token from the meta tag.
 * @returns {string} CSRF token value
 */
function getCsrfToken() {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.content : "";
}

/**
 * Toggles a list's active status via AJAX.
 * @param {number} listId - The ID of the list to toggle
 * @param {HTMLButtonElement} button - The button that was clicked
 */
function toggleList(listId, button) {
  // Disable button during request
  button.disabled = true;

  fetch(`/lists/toggle/${listId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
  })
    .then((response) => {
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("List not found");
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        // Update the badge in the DOM
        const row = button.closest("tr");
        const badge = row.querySelector("[data-status-badge]");

        if (badge) {
          if (data.is_active) {
            badge.className =
              "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
            badge.textContent = "Active";
          } else {
            badge.className =
              "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
            badge.textContent = "Inactive";
          }
        }

        // Update button text
        button.textContent = data.is_active ? "Disable" : "Enable";

        // Update Run button visibility
        const runButton = row.querySelector("[data-run-list]");
        if (runButton) {
          runButton.style.display = data.is_active ? "" : "none";
          runButton.setAttribute("data-list-active", data.is_active ? "true" : "false");
        }
      } else {
        console.error("Toggle failed:", data.message);
        showToast(data.message || "Failed to toggle list status", "error");
      }
    })
    .catch((error) => {
      console.error("Error toggling list:", error);
      showToast("Error toggling list. Please try again.", "error");
    })
    .finally(() => {
      // Re-enable button
      button.disabled = false;
    });
}

/**
 * Note: Toast notification functions (showToast, escapeHtml, TOAST_CONFIG)
 * are now defined in the shared toast.js file, loaded in base.html
 */

/**
 * Show a success toast for wizard actions (legacy wrapper)
 * @param {string} action - "created" or "updated"
 */
function showSuccessMessage(action) {
  showToast(`List ${action} successfully!`, "success");

  // Remove success param from URL without reload
  const url = new URL(window.location);
  url.searchParams.delete("success");
  window.history.replaceState({}, "", url);
}

/**
 * Deletes a list via AJAX.
 * @param {number} listId - The ID of the list to delete
 * @param {HTMLButtonElement} button - The button that was clicked
 */
function deleteList(listId, button) {
  // Confirm deletion
  if (!confirm("Are you sure you want to delete this list?")) {
    return;
  }

  // Disable button during request
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = "Deleting...";

  fetch(`/lists/delete/${listId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
  })
    .then((response) => {
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("List not found");
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        // Remove the row from the DOM
        const row = button.closest("tr");
        if (row) {
          row.style.transition = "opacity 0.3s";
          row.style.opacity = "0";
          setTimeout(() => {
            row.remove();
            // Check if table is now empty
            const tbody = document.querySelector("table tbody");
            if (tbody && tbody.children.length === 0) {
              // Reload to show empty state
              window.location.reload();
            }
          }, 300);
        }
        showToast(data.message || "List deleted successfully!", "success");
      } else {
        console.error("Delete failed:", data.message);
        showToast(data.message || "Failed to delete list", "error");
        button.disabled = false;
        button.textContent = originalText;
      }
    })
    .catch((error) => {
      console.error("Error deleting list:", error);
      showToast("Error deleting list. Please try again.", "error");
      button.disabled = false;
      button.textContent = originalText;
    });
}

// ----------------------
// Job Tracking and Polling (Plan 05-02)
// ----------------------

// Constants
const STORAGE_KEY = "listarr_running_jobs";
const POLL_INTERVAL_MS = 2000; // 2 seconds
const TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

// Active polling controllers (listId -> AbortController)
const activePollers = new Map();

/**
 * Get running jobs from localStorage.
 * @returns {Object} Map of listId -> {startTime: number}
 */
function getRunningJobs() {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : {};
  } catch (e) {
    console.error("Error reading running jobs from localStorage:", e);
    return {};
  }
}

/**
 * Save running jobs to localStorage.
 * @param {Object} jobs - Map of listId -> {startTime: number}
 */
function saveRunningJobs(jobs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  } catch (e) {
    console.error("Error saving running jobs to localStorage:", e);
  }
}

/**
 * Track a running job in localStorage.
 * @param {number|string} listId - The list ID
 * @param {number} startTime - Timestamp when job started
 */
function trackRunningJob(listId, startTime) {
  const jobs = getRunningJobs();
  jobs[listId] = { startTime };
  saveRunningJobs(jobs);
}

/**
 * Remove a job from tracking.
 * @param {number|string} listId - The list ID
 */
function removeRunningJob(listId) {
  const jobs = getRunningJobs();
  delete jobs[listId];
  saveRunningJobs(jobs);
}

/**
 * Check if a job is being tracked.
 * @param {number|string} listId - The list ID
 * @returns {boolean}
 */
function isJobTracked(listId) {
  const jobs = getRunningJobs();
  return !!jobs[listId];
}

/**
 * Get the Run button for a list.
 * @param {number|string} listId - The list ID
 * @returns {HTMLButtonElement|null}
 */
function getRunButton(listId) {
  return document.querySelector(`[data-run-list="${listId}"]`);
}

/**
 * Set button to running state.
 * @param {HTMLButtonElement} button - The button element
 */
function setButtonRunning(button) {
  if (button) {
    button.disabled = true;
    button.textContent = "Running...";
  }
}

/**
 * Restore button to normal state.
 * @param {HTMLButtonElement} button - The button element
 */
function restoreButton(button) {
  if (button) {
    button.disabled = false;
    button.textContent = "Run";
  }
}

/**
 * Show color-coded result toast based on import outcome.
 * @param {Object} result - Import result with summary containing counts
 */
function showResultToast(result) {
  // API returns arrays with counts in summary object
  const added = result.summary?.added_count || 0;
  const skipped = result.summary?.skipped_count || 0;
  const failed = result.summary?.failed_count || 0;

  // Determine toast type based on results
  let toastType = "success";
  if (failed > 0 && added === 0) {
    toastType = "error";
  } else if (failed > 0) {
    toastType = "warning";
  }

  showToast(
    `Import complete: ${added} added, ${skipped} skipped, ${failed} failed`,
    toastType
  );
}

/**
 * Poll job status until completion or timeout.
 * @param {number|string} listId - The list ID to poll
 */
function pollJobStatus(listId) {
  // Check if already polling this list
  if (activePollers.has(listId)) {
    console.log(`Already polling list ${listId}`);
    return;
  }

  const jobs = getRunningJobs();
  const job = jobs[listId];

  if (!job) {
    console.log(`No tracked job for list ${listId}`);
    return;
  }

  const startTime = job.startTime;
  const controller = new AbortController();
  activePollers.set(listId, controller);

  const poll = async () => {
    // Check for timeout
    const elapsed = Date.now() - startTime;
    if (elapsed > TIMEOUT_MS) {
      console.warn(`Polling timeout for list ${listId}`);
      showToast(
        "Import is taking longer than expected. Check the list later.",
        "warning"
      );
      stopPolling(listId);
      restoreButton(getRunButton(listId));
      removeRunningJob(listId);
      return;
    }

    try {
      const response = await fetch(`/lists/${listId}/status`, {
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.status === "completed") {
        // Job finished successfully
        stopPolling(listId);
        removeRunningJob(listId);
        restoreButton(getRunButton(listId));
        if (data.result) {
          showResultToast(data.result);
        } else {
          showToast("Import completed", "success");
        }
      } else if (data.status === "error") {
        // Job failed
        stopPolling(listId);
        removeRunningJob(listId);
        restoreButton(getRunButton(listId));
        showToast(data.error || "Import failed", "error");
      } else if (data.status === "running") {
        // Still running, continue polling
        setTimeout(poll, POLL_INTERVAL_MS);
      } else {
        // Idle - job not found in memory (server restart?)
        // Remove from tracking but don't show error
        stopPolling(listId);
        removeRunningJob(listId);
        restoreButton(getRunButton(listId));
      }
    } catch (error) {
      if (error.name === "AbortError") {
        // Polling was cancelled (page unload)
        return;
      }
      console.error(`Error polling status for list ${listId}:`, error);
      // Continue polling on transient errors
      setTimeout(poll, POLL_INTERVAL_MS);
    }
  };

  // Start polling
  poll();
}

/**
 * Stop polling for a list.
 * @param {number|string} listId - The list ID
 */
function stopPolling(listId) {
  const controller = activePollers.get(listId);
  if (controller) {
    controller.abort();
    activePollers.delete(listId);
  }
}

/**
 * Restore running states from localStorage on page load.
 * Called from initListsPage().
 */
function restoreRunningStates() {
  const jobs = getRunningJobs();

  for (const listId of Object.keys(jobs)) {
    const button = getRunButton(listId);
    const job = jobs[listId];

    // Check if job has timed out
    const elapsed = Date.now() - job.startTime;
    if (elapsed > TIMEOUT_MS) {
      // Job timed out while away - clean up
      removeRunningJob(listId);
      continue;
    }

    // Restore button state and start polling
    setButtonRunning(button);
    pollJobStatus(listId);
  }
}

/**
 * Cleanup polling on page unload.
 */
function cleanupPolling() {
  for (const [listId, controller] of activePollers) {
    controller.abort();
  }
  activePollers.clear();
}

/**
 * Runs an import for a list via AJAX.
 * Handles 202 async response - tracks job and starts polling.
 * @param {number} listId - The ID of the list to run
 * @param {HTMLButtonElement} button - The button that was clicked
 */
function runList(listId, button) {
  // Check if already running (client-side)
  if (isJobTracked(listId)) {
    showToast("This list is already running", "warning");
    return;
  }

  // Immediately disable button and change text to prevent double-click
  button.disabled = true;
  button.textContent = "Running...";

  fetch(`/lists/${listId}/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
  })
    .then((response) => {
      // Handle both 202 (async) and potential errors
      return response.json().then((data) => {
        if (!response.ok) {
          throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        return { data, status: response.status };
      });
    })
    .then(({ data, status }) => {
      if (data.success) {
        if (status === 202) {
          // Async - job started, track and poll
          showToast("Import started", "info");
          const startTime = Date.now();
          trackRunningJob(listId, startTime);
          pollJobStatus(listId);
          // Button stays in "Running..." state until job completes
        } else {
          // Legacy sync response (shouldn't happen after 05-02)
          if (data.result) {
            showResultToast(data.result);
          } else {
            showToast("Import completed", "success");
          }
          restoreButton(button);
        }
      } else {
        throw new Error(data.error || "Import failed");
      }
    })
    .catch((error) => {
      console.error("Error running list:", error);
      showToast(error.message || "Error running import. Please try again.", "error");
      restoreButton(button);
    });
}

/**
 * Initializes run buttons on the lists page.
 */
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

/**
 * Initializes toggle buttons on the lists page.
 */
function initListsPage() {
  // Check for success message in URL
  const urlParams = new URLSearchParams(window.location.search);
  const successAction = urlParams.get("success");
  if (successAction === "created" || successAction === "updated") {
    showSuccessMessage(successAction);
  }

  // Check for deleted message in URL
  if (urlParams.get("deleted") === "true") {
    showToast("List deleted successfully!", "success");
    const url = new URL(window.location);
    url.searchParams.delete("deleted");
    window.history.replaceState({}, "", url);
  }

  // Attach click handlers to all toggle buttons
  const toggleButtons = document.querySelectorAll("[data-toggle-list]");
  toggleButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const listId = this.getAttribute("data-toggle-list");
      toggleList(listId, this);
    });
  });

  // Attach click handlers to all delete buttons
  const deleteButtons = document.querySelectorAll("[data-delete-list]");
  deleteButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const listId = this.getAttribute("data-delete-list");
      deleteList(listId, this);
    });
  });

  // Initialize run buttons
  initRunButtons();

  // Restore running states from localStorage (persists across navigation)
  restoreRunningStates();
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initListsPage);

// Cleanup polling on page unload
window.addEventListener("beforeunload", cleanupPolling);
