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
 * Toast notification configuration by type
 */
const TOAST_CONFIG = {
  success: {
    bgClass: "bg-green-100 dark:bg-green-900 border-green-200 dark:border-green-800",
    iconClass: "text-green-500 dark:text-green-400",
    textClass: "text-green-800 dark:text-green-200",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />',
  },
  error: {
    bgClass: "bg-red-100 dark:bg-red-900 border-red-200 dark:border-red-800",
    iconClass: "text-red-500 dark:text-red-400",
    textClass: "text-red-800 dark:text-red-200",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />',
  },
  warning: {
    bgClass: "bg-yellow-100 dark:bg-yellow-900 border-yellow-200 dark:border-yellow-800",
    iconClass: "text-yellow-500 dark:text-yellow-400",
    textClass: "text-yellow-800 dark:text-yellow-200",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />',
  },
  info: {
    bgClass: "bg-blue-100 dark:bg-blue-900 border-blue-200 dark:border-blue-800",
    iconClass: "text-blue-500 dark:text-blue-400",
    textClass: "text-blue-800 dark:text-blue-200",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />',
  },
};

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Toast type: "success", "error", "warning", "info"
 * @param {number} duration - Duration in ms before auto-dismiss (default 3000)
 */
function showToast(message, type = "success", duration = 3000) {
  const config = TOAST_CONFIG[type] || TOAST_CONFIG.success;

  // Create toast element
  const toast = document.createElement("div");
  toast.className = `fixed top-4 right-4 ${config.bgClass} border rounded-lg p-4 shadow-lg z-50 flex items-center max-w-md`;
  toast.innerHTML = `
    <svg class="w-5 h-5 ${config.iconClass} mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      ${config.icon}
    </svg>
    <span class="text-sm font-medium ${config.textClass}">${escapeHtml(message)}</span>
  `;

  document.body.appendChild(toast);

  // Remove after duration
  setTimeout(() => {
    toast.style.transition = "opacity 0.3s";
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

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
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initListsPage);
