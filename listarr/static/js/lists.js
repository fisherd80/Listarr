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
        alert(data.message || "Failed to toggle list status");
      }
    })
    .catch((error) => {
      console.error("Error toggling list:", error);
      alert("Error toggling list. Please try again.");
    })
    .finally(() => {
      // Re-enable button
      button.disabled = false;
    });
}

/**
 * Initializes toggle buttons on the lists page.
 */
function initListsPage() {
  // Attach click handlers to all toggle buttons
  const toggleButtons = document.querySelectorAll("[data-toggle-list]");

  toggleButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const listId = this.getAttribute("data-toggle-list");
      toggleList(listId, this);
    });
  });
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initListsPage);
