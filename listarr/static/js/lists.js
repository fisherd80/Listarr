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
