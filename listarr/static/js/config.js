// ----------------------
// Data Loading State Tracking
// ----------------------
// Tracks whether Radarr/Sonarr import settings data has been fetched
// Prevents redundant API calls when toggling Import Settings visibility
let radarrDataLoaded = false;
let sonarrDataLoaded = false;

// ----------------------
// Helper Functions
// ----------------------
function formatTimestamp(isoTimestamp) {
  const date = new Date(isoTimestamp);
  return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

function generateStatusHTML(success, timestamp) {
  const statusIcon = success ? "✓" : "✗";
  const statusClass = success
    ? "text-green-600 dark:text-green-400"
    : "text-red-600 dark:text-red-400";
  const formattedTime = formatTimestamp(timestamp);

  return `
    <span class="inline-flex items-center gap-1">
      <span class="${statusClass}">${statusIcon}</span>
      Last tested: <span data-timestamp="${timestamp}">${formattedTime}</span>
    </span>
  `;
}

// ----------------------
// Toggle Functions
// ----------------------

/**
 * Toggle a collapsible Import Settings section.
 * Rotates the chevron icon and fetches data on first open.
 *
 * @param {string} id - The ID of the div containing the collapsible content.
 * @param {HTMLElement} button - The button element that was clicked.
 */
function toggleImportSettings(id, button) {
  const content = document.getElementById(id);
  if (!content) return;

  const wasHidden = content.classList.contains("hidden");

  // Toggle hidden class
  content.classList.toggle("hidden");

  // Rotate the chevron icon
  const svg = button.querySelector("svg");
  if (svg) {
    svg.classList.toggle("rotate-180");
  }

  // Fetch data when expanding Radarr import settings for the first time
  if (wasHidden && id === "radarr-import-settings" && !radarrDataLoaded) {
    // Set flag immediately to prevent duplicate requests
    radarrDataLoaded = true;

    // Fetch both dropdowns, then load saved settings
    Promise.all([
      fetchRadarrRootFolders(),
      fetchRadarrQualityProfiles()
    ]).then(() => {
      loadRadarrSavedSettings();
    }).catch((error) => {
      // Reset flag on error so user can retry
      radarrDataLoaded = false;
      console.error("Failed to load Radarr import settings:", error);
    });
  }

  // Fetch data when expanding Sonarr import settings for the first time
  if (wasHidden && id === "sonarr-import-settings" && !sonarrDataLoaded) {
    // Set flag immediately to prevent duplicate requests
    sonarrDataLoaded = true;

    // Fetch both dropdowns, then load saved settings
    Promise.all([
      fetchSonarrRootFolders(),
      fetchSonarrQualityProfiles()
    ]).then(() => {
      loadSonarrSavedSettings();
    }).catch((error) => {
      // Reset flag on error so user can retry
      sonarrDataLoaded = false;
      console.error("Failed to load Sonarr import settings:", error);
    });
  }
}

/**
 * Toggle API key visibility for Radarr or Sonarr.
 *
 * @param {string} inputId - The ID of the API input field.
 * @param {HTMLElement} button - The eye button element clicked.
 */
function toggleApiKey(inputId, button) {
  const input = document.getElementById(inputId);
  if (!input) return;

  input.type = input.type === "password" ? "text" : "password";
}

// ----------------------
// Radarr Data Fetching Functions
// ----------------------

/**
 * Fetches root folders from Radarr and populates the dropdown.
 * Returns a Promise that resolves when the dropdown is populated.
 */
function fetchRadarrRootFolders() {
  const select = document.getElementById("radarr-root-folder");
  if (!select) return Promise.resolve();

  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  // Show loading state
  select.innerHTML = '<option value="">Loading...</option>';
  select.disabled = true;

  return fetch("/config/radarr/root-folders", {
    method: "GET",
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.folders) {
        // Clear existing options
        select.innerHTML = '<option value="">Select Root Folder</option>';

        // Populate with fetched folders
        data.folders.forEach((folder) => {
          const option = document.createElement("option");
          option.value = folder.id;
          option.textContent = folder.path;
          select.appendChild(option);
        });

        select.disabled = false;
      } else {
        select.innerHTML = '<option value="">Failed to load</option>';
        console.error("Failed to fetch root folders:", data.message);
      }
    })
    .catch((error) => {
      select.innerHTML = '<option value="">Error loading</option>';
      console.error("Error fetching root folders:", error);
    });
}

/**
 * Fetches quality profiles from Radarr and populates the dropdown.
 * Returns a Promise that resolves when the dropdown is populated.
 */
function fetchRadarrQualityProfiles() {
  const select = document.getElementById("radarr-quality-profile");
  if (!select) return Promise.resolve();

  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  // Show loading state
  select.innerHTML = '<option value="">Loading...</option>';
  select.disabled = true;

  return fetch("/config/radarr/quality-profiles", {
    method: "GET",
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.profiles) {
        // Clear existing options
        select.innerHTML = '<option value="">Select Quality Profile</option>';

        // Populate with fetched profiles
        data.profiles.forEach((profile) => {
          const option = document.createElement("option");
          option.value = profile.id;
          option.textContent = profile.name;
          select.appendChild(option);
        });

        select.disabled = false;
      } else {
        select.innerHTML = '<option value="">Failed to load</option>';
        console.error("Failed to fetch quality profiles:", data.message);
      }
    })
    .catch((error) => {
      select.innerHTML = '<option value="">Error loading</option>';
      console.error("Error fetching quality profiles:", error);
    });
}

/**
 * Fetches and applies saved Radarr import settings to the dropdowns.
 */
function loadRadarrSavedSettings() {
  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  fetch("/config/radarr/import-settings", {
    method: "GET",
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.settings) {
        const rootFolderSelect = document.getElementById("radarr-root-folder");
        const qualityProfileSelect = document.getElementById("radarr-quality-profile");
        const monitorSelect = document.getElementById("radarr-monitor");
        const searchOnAddSelect = document.getElementById("radarr-search-on-add");

        // Apply saved values to dropdowns
        if (rootFolderSelect && data.settings.root_folder_id) {
          rootFolderSelect.value = data.settings.root_folder_id;
        }

        if (qualityProfileSelect && data.settings.quality_profile_id) {
          qualityProfileSelect.value = data.settings.quality_profile_id;
        }

        if (monitorSelect && data.settings.monitored !== undefined) {
          monitorSelect.value = data.settings.monitored ? "true" : "false";
        }

        if (searchOnAddSelect && data.settings.search_on_add !== undefined) {
          searchOnAddSelect.value = data.settings.search_on_add ? "true" : "false";
        }
      }
    })
    .catch((error) => {
      console.error("Error loading saved settings:", error);
    });
}

// ----------------------
// Sonarr Data Fetching Functions
// ----------------------

/**
 * Fetches root folders from Sonarr and populates the dropdown.
 * Returns a Promise that resolves when the dropdown is populated.
 */
function fetchSonarrRootFolders() {
  const select = document.getElementById("sonarr-root-folder");
  if (!select) return Promise.resolve();

  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  // Show loading state
  select.innerHTML = '<option value="">Loading...</option>';
  select.disabled = true;

  return fetch("/config/sonarr/root-folders", {
    method: "GET",
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.folders) {
        // Clear existing options
        select.innerHTML = '<option value="">Select Root Folder</option>';

        // Populate with fetched folders
        data.folders.forEach((folder) => {
          const option = document.createElement("option");
          option.value = folder.id;
          option.textContent = folder.path;
          select.appendChild(option);
        });

        select.disabled = false;
      } else {
        select.innerHTML = '<option value="">Failed to load</option>';
        console.error("Failed to fetch root folders:", data.message);
      }
    })
    .catch((error) => {
      select.innerHTML = '<option value="">Error loading</option>';
      console.error("Error fetching root folders:", error);
    });
}

/**
 * Fetches quality profiles from Sonarr and populates the dropdown.
 * Returns a Promise that resolves when the dropdown is populated.
 */
function fetchSonarrQualityProfiles() {
  const select = document.getElementById("sonarr-quality-profile");
  if (!select) return Promise.resolve();

  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  // Show loading state
  select.innerHTML = '<option value="">Loading...</option>';
  select.disabled = true;

  return fetch("/config/sonarr/quality-profiles", {
    method: "GET",
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.profiles) {
        // Clear existing options
        select.innerHTML = '<option value="">Select Quality Profile</option>';

        // Populate with fetched profiles
        data.profiles.forEach((profile) => {
          const option = document.createElement("option");
          option.value = profile.id;
          option.textContent = profile.name;
          select.appendChild(option);
        });

        select.disabled = false;
      } else {
        select.innerHTML = '<option value="">Failed to load</option>';
        console.error("Failed to fetch quality profiles:", data.message);
      }
    })
    .catch((error) => {
      select.innerHTML = '<option value="">Error loading</option>';
      console.error("Error fetching quality profiles:", error);
    });
}

/**
 * Fetches and applies saved Sonarr import settings to the dropdowns.
 */
function loadSonarrSavedSettings() {
  // Get CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  fetch("/config/sonarr/import-settings", {
    method: "GET",
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.settings) {
        const rootFolderSelect = document.getElementById("sonarr-root-folder");
        const qualityProfileSelect = document.getElementById("sonarr-quality-profile");
        const monitorSelect = document.getElementById("sonarr-monitor");
        const seasonFolderSelect = document.getElementById("sonarr-season-folder");
        const searchOnAddSelect = document.getElementById("sonarr-search-on-add");

        // Apply saved values to dropdowns
        if (rootFolderSelect && data.settings.root_folder_id) {
          rootFolderSelect.value = data.settings.root_folder_id;
        }

        if (qualityProfileSelect && data.settings.quality_profile_id) {
          qualityProfileSelect.value = data.settings.quality_profile_id;
        }

        if (monitorSelect && data.settings.monitored !== undefined) {
          monitorSelect.value = data.settings.monitored ? "true" : "false";
        }

        if (seasonFolderSelect && data.settings.season_folder !== undefined) {
          seasonFolderSelect.value = data.settings.season_folder ? "true" : "false";
        }

        if (searchOnAddSelect && data.settings.search_on_add !== undefined) {
          searchOnAddSelect.value = data.settings.search_on_add ? "true" : "false";
        }
      }
    })
    .catch((error) => {
      console.error("Error loading saved settings:", error);
    });
}

// ----------------------
// Test Connection Handlers
// ----------------------

// Test Radarr Connection
document.addEventListener("DOMContentLoaded", () => {
  const testRadarrButton = document.getElementById("test-radarr-button");

  if (testRadarrButton) {
    testRadarrButton.addEventListener("click", function () {
      const baseUrl = document.getElementById("radarr_url").value;
      const apiKey = document.getElementById("radarr-api").value;
      const button = this;
      const lastTestDiv = document.getElementById("radarr-last-test");

      // Get CSRF token from meta tag
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

      // Disable button during test
      button.disabled = true;
      button.textContent = "Testing...";

      fetch("/config/test_radarr_api", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ base_url: baseUrl, api_key: apiKey }),
      })
        .then((response) => response.json())
        .then((data) => {
          alert(data.message);

          // Update last test status display using helper function
          lastTestDiv.innerHTML = generateStatusHTML(data.success, data.timestamp);

          // Re-enable button
          button.disabled = false;
          button.textContent = "Test Connection";
        })
        .catch((error) => {
          alert("Error testing Radarr connection.");
          console.error(error);

          // Re-enable button
          button.disabled = false;
          button.textContent = "Test Connection";
        });
    });
  }

  // Test Sonarr Connection
  const testSonarrButton = document.getElementById("test-sonarr-button");

  if (testSonarrButton) {
    testSonarrButton.addEventListener("click", function () {
      const baseUrl = document.getElementById("sonarr_url").value;
      const apiKey = document.getElementById("sonarr-api").value;
      const button = this;
      const lastTestDiv = document.getElementById("sonarr-last-test");

      // Get CSRF token from meta tag
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

      // Disable button during test
      button.disabled = true;
      button.textContent = "Testing...";

      fetch("/config/test_sonarr_api", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ base_url: baseUrl, api_key: apiKey }),
      })
        .then((response) => response.json())
        .then((data) => {
          alert(data.message);

          // Update last test status display using helper function
          lastTestDiv.innerHTML = generateStatusHTML(data.success, data.timestamp);

          // Re-enable button
          button.disabled = false;
          button.textContent = "Test Connection";
        })
        .catch((error) => {
          alert("Error testing Sonarr connection.");
          console.error(error);

          // Re-enable button
          button.disabled = false;
          button.textContent = "Test Connection";
        });
    });
  }

  // Optional: add smooth slide animation for Import Settings
  const collapsibles = document.querySelectorAll(".collapsible");
  collapsibles.forEach((c) => {
    c.style.transition =
      "max-height 0.3s ease-in-out, opacity 0.3s ease-in-out";
    if (!c.classList.contains("hidden")) {
      c.style.maxHeight = c.scrollHeight + "px";
      c.style.opacity = 1;
    } else {
      c.style.maxHeight = "0px";
      c.style.opacity = 0;
    }
  });

  // Save Radarr Import Settings
  const saveRadarrImportButton = document.getElementById("save-radarr-import-settings");

  if (saveRadarrImportButton) {
    saveRadarrImportButton.addEventListener("click", function () {
      const rootFolderSelect = document.getElementById("radarr-root-folder");
      const qualityProfileSelect = document.getElementById("radarr-quality-profile");
      const monitorSelect = document.getElementById("radarr-monitor");
      const searchOnAddSelect = document.getElementById("radarr-search-on-add");
      const button = this;

      // Get selected values
      const rootFolderId = rootFolderSelect.value;
      const qualityProfileId = qualityProfileSelect.value;
      const monitorValue = monitorSelect.value;
      const searchOnAddValue = searchOnAddSelect.value;

      // Validate selections
      if (!rootFolderId || !qualityProfileId) {
        alert("Please select Root Folder and Quality Profile.");
        return;
      }

      if (!monitorValue) {
        alert("Please select Monitor option.");
        return;
      }

      if (!searchOnAddValue) {
        alert("Please select Search on Add option.");
        return;
      }

      // Convert to boolean
      const monitored = monitorValue === "true";
      const searchOnAdd = searchOnAddValue === "true";

      // Get CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

      // Disable button during save
      button.disabled = true;
      button.textContent = "Saving...";

      fetch("/config/radarr/import-settings", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          root_folder_id: rootFolderId,
          quality_profile_id: qualityProfileId,
          monitored: monitored,
          search_on_add: searchOnAdd,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            alert(data.message);
          } else {
            alert("Error: " + data.message);
          }

          // Re-enable button
          button.disabled = false;
          button.textContent = "Save Import Settings";
        })
        .catch((error) => {
          alert("Error saving Radarr import settings.");
          console.error(error);

          // Re-enable button
          button.disabled = false;
          button.textContent = "Save Import Settings";
        });
    });
  }

  // Save Sonarr Import Settings
  const saveSonarrImportButton = document.getElementById("save-sonarr-import-settings");

  if (saveSonarrImportButton) {
    saveSonarrImportButton.addEventListener("click", function () {
      const rootFolderSelect = document.getElementById("sonarr-root-folder");
      const qualityProfileSelect = document.getElementById("sonarr-quality-profile");
      const monitorSelect = document.getElementById("sonarr-monitor");
      const seasonFolderSelect = document.getElementById("sonarr-season-folder");
      const searchOnAddSelect = document.getElementById("sonarr-search-on-add");
      const button = this;

      // Get selected values
      const rootFolderId = rootFolderSelect.value;
      const qualityProfileId = qualityProfileSelect.value;
      const monitorValue = monitorSelect.value;
      const seasonFolderValue = seasonFolderSelect.value;
      const searchOnAddValue = searchOnAddSelect.value;

      // Validate selections
      if (!rootFolderId || !qualityProfileId) {
        alert("Please select Root Folder and Quality Profile.");
        return;
      }

      if (!monitorValue) {
        alert("Please select Monitor option.");
        return;
      }

      if (!seasonFolderValue) {
        alert("Please select Season Folder option.");
        return;
      }

      if (!searchOnAddValue) {
        alert("Please select Search on Add option.");
        return;
      }

      // Convert to boolean
      const monitored = monitorValue === "true";
      const seasonFolder = seasonFolderValue === "true";
      const searchOnAdd = searchOnAddValue === "true";

      // Get CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

      // Disable button during save
      button.disabled = true;
      button.textContent = "Saving...";

      fetch("/config/sonarr/import-settings", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          root_folder_id: rootFolderId,
          quality_profile_id: qualityProfileId,
          monitored: monitored,
          season_folder: seasonFolder,
          search_on_add: searchOnAdd,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            alert(data.message);
          } else {
            alert("Error: " + data.message);
          }

          // Re-enable button
          button.disabled = false;
          button.textContent = "Save Import Settings";
        })
        .catch((error) => {
          alert("Error saving Sonarr import settings.");
          console.error(error);

          // Re-enable button
          button.disabled = false;
          button.textContent = "Save Import Settings";
        });
    });
  }
});
