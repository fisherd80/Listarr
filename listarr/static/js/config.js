// Data Loading State Tracking
const dataLoaded = { radarr: false, sonarr: false };

// Toggle Functions
function toggleImportSettings(id, button) {
  const content = document.getElementById(id);
  if (!content) return;

  const wasHidden = content.classList.contains("hidden");
  content.classList.toggle("hidden");

  const svg = button.querySelector("svg");
  if (svg) svg.classList.toggle("rotate-180");

  const service = id.includes("radarr") ? "radarr" : "sonarr";

  if (wasHidden && !dataLoaded[service]) {
    dataLoaded[service] = true;

    Promise.all([
      fetchRootFolders(service),
      fetchQualityProfiles(service)
    ]).then(() => {
      loadSavedSettings(service);
    }).catch((error) => {
      dataLoaded[service] = false;
      console.error(`Failed to load ${service} import settings:`, error);
    });
  }
}

function toggleApiKey(inputId, button) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.type = input.type === "password" ? "text" : "password";
}

// Parameterized Data Fetching Functions
function fetchRootFolders(service) {
  const select = document.getElementById(`${service}-root-folder`);
  if (!select) return Promise.resolve();

  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  select.innerHTML = '<option value="">Loading...</option>';
  select.disabled = true;

  return fetch(`/config/${service}/root-folders`, {
    method: "GET",
    headers: { "X-CSRFToken": csrfToken },
  })
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (data.success && data.folders) {
        select.innerHTML = '<option value="">Select Root Folder</option>';
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

function fetchQualityProfiles(service) {
  const select = document.getElementById(`${service}-quality-profile`);
  if (!select) return Promise.resolve();

  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  select.innerHTML = '<option value="">Loading...</option>';
  select.disabled = true;

  return fetch(`/config/${service}/quality-profiles`, {
    method: "GET",
    headers: { "X-CSRFToken": csrfToken },
  })
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (data.success && data.profiles) {
        select.innerHTML = '<option value="">Select Quality Profile</option>';
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

function loadSavedSettings(service) {
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  fetch(`/config/${service}/import-settings`, {
    method: "GET",
    headers: { "X-CSRFToken": csrfToken },
  })
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (data.success && data.settings) {
        const rootFolderSelect = document.getElementById(`${service}-root-folder`);
        const qualityProfileSelect = document.getElementById(`${service}-quality-profile`);
        const monitorSelect = document.getElementById(`${service}-monitor`);
        const searchOnAddSelect = document.getElementById(`${service}-search-on-add`);
        const tagsInput = document.getElementById(`${service}-tags`);

        if (rootFolderSelect && data.settings.root_folder_id) {
          rootFolderSelect.value = data.settings.root_folder_id;
        }

        if (qualityProfileSelect && data.settings.quality_profile_id) {
          qualityProfileSelect.value = data.settings.quality_profile_id;
        }

        if (monitorSelect && data.settings.monitored !== undefined) {
          monitorSelect.value = data.settings.monitored ? "true" : "false";
        }

        if (service === "sonarr") {
          const seasonFolderSelect = document.getElementById("sonarr-season-folder");
          if (seasonFolderSelect && data.settings.season_folder !== undefined) {
            seasonFolderSelect.value = data.settings.season_folder ? "true" : "false";
          }
        }

        if (searchOnAddSelect && data.settings.search_on_add !== undefined) {
          searchOnAddSelect.value = data.settings.search_on_add ? "true" : "false";
        }

        if (tagsInput && data.settings.tag_label) {
          tagsInput.value = data.settings.tag_label;
        }
      }
    })
    .catch((error) => {
      console.error("Error loading saved settings:", error);
    });
}

// Parameterized Event Handler Setup
function setupTestConnection(service) {
  const testButton = document.getElementById(`test-${service}-button`);

  if (testButton) {
    testButton.addEventListener("click", function () {
      const baseUrl = document.getElementById(`${service}_url`).value;
      const apiKey = document.getElementById(`${service}-api`).value;
      const button = this;
      const lastTestDiv = document.getElementById(`${service}-last-test`);

      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

      button.disabled = true;
      button.textContent = "Testing...";

      fetch(`/config/test_${service}_api`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ base_url: baseUrl, api_key: apiKey }),
      })
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.json();
        })
        .then((data) => {
          showToast(data.message, data.success ? "success" : "error");
          lastTestDiv.innerHTML = generateStatusHTML(data.success, data.timestamp);
          button.disabled = false;
          button.textContent = "Test Connection";
        })
        .catch((error) => {
          showToast(`Error testing ${service} connection.`, "error");
          console.error(error);
          button.disabled = false;
          button.textContent = "Test Connection";
        });
    });
  }
}

function setupSaveImportSettings(service) {
  const saveButton = document.getElementById(`save-${service}-import-settings`);

  if (saveButton) {
    saveButton.addEventListener("click", function () {
      const rootFolderSelect = document.getElementById(`${service}-root-folder`);
      const qualityProfileSelect = document.getElementById(`${service}-quality-profile`);
      const monitorSelect = document.getElementById(`${service}-monitor`);
      const searchOnAddSelect = document.getElementById(`${service}-search-on-add`);
      const tagsInput = document.getElementById(`${service}-tags`);
      const button = this;

      const rootFolderId = rootFolderSelect.value;
      const qualityProfileId = qualityProfileSelect.value;
      const monitorValue = monitorSelect.value;
      const searchOnAddValue = searchOnAddSelect.value;
      const tagLabel = tagsInput ? tagsInput.value.trim() : "";

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

      const monitored = monitorValue === "true";
      const searchOnAdd = searchOnAddValue === "true";

      const requestBody = {
        root_folder_id: rootFolderId,
        quality_profile_id: qualityProfileId,
        monitored: monitored,
        search_on_add: searchOnAdd,
        tag_label: tagLabel || null,
      };

      if (service === "sonarr") {
        const seasonFolderSelect = document.getElementById("sonarr-season-folder");
        const seasonFolderValue = seasonFolderSelect.value;

        if (!seasonFolderValue) {
          alert("Please select Season Folder option.");
          return;
        }

        requestBody.season_folder = seasonFolderValue === "true";
      }

      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

      button.disabled = true;
      button.textContent = "Saving...";

      fetch(`/config/${service}/import-settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(requestBody),
      })
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.json();
        })
        .then((data) => {
          if (data.success) {
            showToast(data.message, "success");
          } else {
            showToast("Error: " + data.message, "error");
          }
          button.disabled = false;
          button.textContent = "Save Import Settings";
        })
        .catch((error) => {
          showToast(`Error saving ${service} import settings.`, "error");
          console.error(error);
          button.disabled = false;
          button.textContent = "Save Import Settings";
        });
    });
  }
}

// DOMContentLoaded Event Handler
document.addEventListener("DOMContentLoaded", () => {
  setupTestConnection("radarr");
  setupTestConnection("sonarr");

  const collapsibles = document.querySelectorAll(".collapsible");
  collapsibles.forEach((c) => {
    c.style.transition = "max-height 0.3s ease-in-out, opacity 0.3s ease-in-out";
    if (!c.classList.contains("hidden")) {
      c.style.maxHeight = c.scrollHeight + "px";
      c.style.opacity = 1;
    } else {
      c.style.maxHeight = "0px";
      c.style.opacity = 0;
    }
  });

  setupSaveImportSettings("radarr");
  setupSaveImportSettings("sonarr");
});
