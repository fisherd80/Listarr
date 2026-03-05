/**
 * settings.js — Client-side behavior for the Settings page.
 *
 * Handles:
 *   - Top-level tab switching (Integrations, TMDB, Account)
 *   - Service sub-tab switching (Radarr, Sonarr)
 *   - API key visibility toggle
 *   - Connection test and save (Radarr, Sonarr)
 *   - TMDB settings save
 *   - Password change form
 *   - Import defaults loading and saving
 */

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

/**
 * Return the CSRF token from the page meta tag.
 * @returns {string}
 */
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

/**
 * Fetch wrapper that automatically includes CSRF header for non-GET requests.
 * @param {string} url
 * @param {object} options - Standard fetch options (method, headers, body, etc.)
 * @returns {Promise<Response>}
 */
function apiFetch(url, options) {
  const opts = Object.assign({ headers: {} }, options);
  if (opts.method && opts.method.toUpperCase() !== 'GET') {
    opts.headers['X-CSRFToken'] = getCsrfToken();
  }
  return fetch(url, opts);
}

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

/**
 * Initialise top-level Settings tabs (Integrations / TMDB / Account).
 * All panels stay in DOM; tab switching only toggles "hidden".
 */
function initSettingsTabs() {
  const tabs = document.querySelectorAll('.settings-tab');
  const panels = document.querySelectorAll('.settings-panel');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      // Deactivate all tabs
      tabs.forEach(function (t) {
        t.classList.remove('border-primary', 'text-text-heading');
        t.classList.add('border-transparent', 'text-text-muted');
      });
      // Hide all panels
      panels.forEach(function (p) {
        p.classList.add('hidden');
      });
      // Activate clicked tab
      tab.classList.add('border-primary', 'text-text-heading');
      tab.classList.remove('border-transparent', 'text-text-muted');
      // Show matching panel
      var panelId = 'tab-' + tab.dataset.tab;
      var panel = document.getElementById(panelId);
      if (panel) {
        panel.classList.remove('hidden');
      }
      // When Integrations tab is activated, trigger import defaults for configured services
      if (tab.dataset.tab === 'integrations') {
        maybeLoadImportDefaults();
      }
    });
  });
}

/**
 * Initialise Radarr/Sonarr service sub-tabs within the Integrations panel.
 */
function initServiceTabs() {
  var container = document.getElementById('tab-integrations');
  if (!container) return;

  var tabs = container.querySelectorAll('.service-tab');
  var panels = container.querySelectorAll('.service-panel');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      // Deactivate all service tabs
      tabs.forEach(function (t) {
        t.classList.remove('border-primary', 'text-text-heading');
        t.classList.add('border-transparent', 'text-text-muted');
      });
      // Hide all service panels
      panels.forEach(function (p) {
        p.classList.add('hidden');
      });
      // Activate clicked tab
      tab.classList.add('border-primary', 'text-text-heading');
      tab.classList.remove('border-transparent', 'text-text-muted');
      // Show matching panel
      var service = tab.dataset.service;
      var panel = document.getElementById('service-panel-' + service);
      if (panel) {
        panel.classList.remove('hidden');
      }
    });
  });
}

// ---------------------------------------------------------------------------
// API key visibility toggle
// ---------------------------------------------------------------------------

/**
 * Toggle an API key input between password (masked) and text (visible).
 * @param {string} inputId - The id of the input element
 * @param {HTMLElement} button - The toggle button element (for aria feedback)
 */
function togglePasswordVisibility(inputId, button) {
  var input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    button.setAttribute('title', 'Hide API key');
  } else {
    input.type = 'password';
    button.setAttribute('title', 'Show API key');
  }
}

// ---------------------------------------------------------------------------
// Connection test (Radarr / Sonarr)
// ---------------------------------------------------------------------------

/**
 * Test a Radarr or Sonarr connection using current URL + API key inputs.
 * Updates the test button text/colour to indicate result.
 * @param {string} service - 'radarr' or 'sonarr'
 */
function testConnection(service) {
  var urlInput = document.getElementById(service + '-url');
  var keyInput = document.getElementById(service + '-api-key');
  var btn = document.getElementById(service + '-test-btn');
  var statusEl = document.getElementById(service + '-status');

  if (!urlInput || !keyInput || !btn) return;

  var baseUrl = urlInput.value.trim();
  var apiKey = keyInput.value.trim();
  var formContainer = document.getElementById(service + '-connection-form');
  var isConfigured = formContainer && formContainer.dataset.configured === 'true';

  if (!baseUrl) {
    setStatus(statusEl, false, 'URL is required to test.');
    return;
  }
  if (!apiKey && !isConfigured) {
    setStatus(statusEl, false, 'API key is required to test.');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Testing...';

  var endpoint = '/api/settings/test_' + service + '_api';

  apiFetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_url: baseUrl, api_key: apiKey }),
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      btn.disabled = false;
      if (data.success) {
        btn.textContent = 'Connected';
        btn.classList.remove('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'bg-red-600', 'hover:bg-red-700');
        btn.classList.add('bg-success', 'hover:bg-success/90');
        setStatus(statusEl, true, 'Connection successful.');
      } else {
        btn.textContent = 'Failed';
        btn.classList.remove('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'bg-success', 'hover:bg-success/90');
        btn.classList.add('bg-error', 'hover:bg-error/90');
        setStatus(statusEl, false, data.message || 'Connection failed.');
      }
      // Reset button text after 3 seconds
      setTimeout(function () {
        btn.textContent = 'Test Connection';
        btn.classList.remove('bg-success', 'hover:bg-success/90', 'bg-error', 'hover:bg-error/90');
        btn.classList.add('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover');
      }, 3000);
    })
    .catch(function (err) {
      btn.disabled = false;
      btn.textContent = 'Test Connection';
      setStatus(statusEl, false, 'Request failed. Check console for details.');
      console.error('testConnection error:', err);
    });
}

// ---------------------------------------------------------------------------
// Connection save (Radarr / Sonarr)
// ---------------------------------------------------------------------------

/**
 * Save a Radarr or Sonarr connection (auto-tests first).
 * On test failure, reveals the "Save Anyway" button.
 * On success, reveals the import defaults panel.
 * @param {string} service - 'radarr' or 'sonarr'
 * @param {boolean} [force] - If true, skip the connection test
 */
function saveConnection(service, force) {
  var urlInput = document.getElementById(service + '-url');
  var keyInput = document.getElementById(service + '-api-key');
  var saveBtn = document.getElementById(service + '-save-btn');
  var forceBtn = document.getElementById(service + '-force-save-btn');
  var statusEl = document.getElementById(service + '-status');

  if (!urlInput || !keyInput || !saveBtn) return;

  var baseUrl = urlInput.value.trim();
  var apiKey = keyInput.value.trim();
  var formContainer = document.getElementById(service + '-connection-form');
  var isConfigured = formContainer && formContainer.dataset.configured === 'true';

  if (!baseUrl) {
    setStatus(statusEl, false, 'URL is required.');
    return;
  }
  if (!apiKey && !isConfigured) {
    setStatus(statusEl, false, 'API key is required.');
    return;
  }

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';
  if (forceBtn) forceBtn.classList.add('hidden');

  var body = { base_url: baseUrl, api_key: apiKey };
  if (force) body.force_save = true;

  apiFetch('/api/settings/' + service + '/connection', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';

      if (data.success) {
        setStatus(statusEl, true, data.message || 'Saved successfully.');
        // Reveal import defaults panel and load data
        var importPanel = document.getElementById(service + '-import-defaults');
        if (importPanel) {
          importPanel.classList.remove('hidden');
          loadImportDefaults(service);
        }
        // Ensure the saved key is in the input value (for toggle reveal)
        if (keyInput.value) {
          keyInput.type = 'password';
        }
      } else if (data.test_failed) {
        setStatus(statusEl, false, data.message || 'Connection test failed.');
        // Show "Save Anyway" button
        if (forceBtn) forceBtn.classList.remove('hidden');
      } else {
        setStatus(statusEl, false, data.message || 'Save failed.');
      }
    })
    .catch(function (err) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
      setStatus(statusEl, false, 'Request failed. Check console for details.');
      console.error('saveConnection error:', err);
    });
}

/**
 * Re-submit connection save with force_save: true (bypass test).
 * @param {string} service - 'radarr' or 'sonarr'
 */
function saveConnectionForce(service) {
  saveConnection(service, true);
}

// ---------------------------------------------------------------------------
// TMDB settings save
// ---------------------------------------------------------------------------

/**
 * Test TMDB API key only (no save).
 */
function testTmdb() {
  var keyInput = document.getElementById('tmdb-api-key');
  var btn = document.getElementById('tmdb-test-btn');
  var statusEl = document.getElementById('tmdb-status');

  if (!keyInput || !btn) return;

  var apiKey = keyInput.value.trim();
  var formContainer = document.getElementById('tmdb-connection-form');
  var isConfigured = formContainer && formContainer.dataset.configured === 'true';
  if (!apiKey && !isConfigured) {
    setStatus(statusEl, false, 'API key is required to test.');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Testing...';

  apiFetch('/settings/test_tmdb_api', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      btn.disabled = false;
      if (data.success) {
        btn.textContent = 'Connected';
        btn.classList.remove('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'bg-red-600', 'hover:bg-red-700');
        btn.classList.add('bg-success', 'hover:bg-success/90');
        setStatus(statusEl, true, 'TMDB API key is valid.');
      } else {
        btn.textContent = 'Failed';
        btn.classList.remove('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'bg-success', 'hover:bg-success/90');
        btn.classList.add('bg-error', 'hover:bg-error/90');
        setStatus(statusEl, false, data.message || 'Invalid API key.');
      }
      setTimeout(function () {
        btn.textContent = 'Test Connection';
        btn.classList.remove('bg-success', 'hover:bg-success/90', 'bg-error', 'hover:bg-error/90');
        btn.classList.add('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover');
      }, 3000);
    })
    .catch(function (err) {
      btn.disabled = false;
      btn.textContent = 'Test Connection';
      setStatus(statusEl, false, 'Request failed.');
      console.error('testTmdb error:', err);
    });
}

/**
 * Save TMDB API key and region (auto-tests first unless force=true).
 * @param {boolean} [force] - Skip connection test
 */
function saveTmdbSettings(force) {
  var keyInput = document.getElementById('tmdb-api-key');
  var regionSelect = document.getElementById('tmdb-region');
  var saveBtn = document.getElementById('tmdb-save-btn');
  var forceBtn = document.getElementById('tmdb-force-save-btn');
  var statusEl = document.getElementById('tmdb-status');

  if (!keyInput || !saveBtn) return;

  var apiKey = keyInput.value.trim();
  var region = regionSelect ? regionSelect.value : '';
  var formContainer = document.getElementById('tmdb-connection-form');
  var isConfigured = formContainer && formContainer.dataset.configured === 'true';
  if (!apiKey && !isConfigured) {
    setStatus(statusEl, false, 'API key is required.');
    return;
  }

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';
  if (forceBtn) forceBtn.classList.add('hidden');

  var body = { api_key: apiKey, region: region };
  if (force) body.force_save = true;

  apiFetch('/api/settings/tmdb', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';

      if (data.success) {
        setStatus(statusEl, true, data.message || 'TMDB settings saved.');
        // Ensure the saved key stays masked (for toggle reveal)
        if (keyInput.value) {
          keyInput.type = 'password';
        }
      } else if (data.test_failed) {
        setStatus(statusEl, false, data.message || 'Connection test failed.');
        if (forceBtn) forceBtn.classList.remove('hidden');
      } else {
        setStatus(statusEl, false, data.message || 'Save failed.');
      }
    })
    .catch(function (err) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
      setStatus(statusEl, false, 'Request failed.');
      console.error('saveTmdbSettings error:', err);
    });
}

/**
 * Re-submit TMDB save with force_save: true.
 */
function saveTmdbSettingsForce() {
  saveTmdbSettings(true);
}

// ---------------------------------------------------------------------------
// Password change
// ---------------------------------------------------------------------------

/**
 * Submit the change-password form via AJAX (FormData, not JSON).
 * The endpoint uses form.validate_on_submit() which reads from request.form.
 * @param {Event} event - The form submit event
 */
function changePassword(event) {
  event.preventDefault();

  var form = document.getElementById('change-password-form');
  var btn = document.getElementById('change-password-btn');
  var statusEl = document.getElementById('password-status');

  if (!form || !btn) return;

  btn.disabled = true;
  btn.textContent = 'Changing...';

  var formData = new FormData(form);

  fetch('/settings/change-password', {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: formData,
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      btn.disabled = false;
      btn.textContent = 'Change Password';
      if (data.success) {
        setStatus(statusEl, true, data.message || 'Password changed successfully.');
        form.reset();
      } else {
        setStatus(statusEl, false, data.message || 'Password change failed.');
      }
    })
    .catch(function (err) {
      btn.disabled = false;
      btn.textContent = 'Change Password';
      setStatus(statusEl, false, 'Request failed.');
      console.error('changePassword error:', err);
    });
}

// ---------------------------------------------------------------------------
// Import defaults
// ---------------------------------------------------------------------------

/**
 * Load quality profiles + root folders for a service, then populate the
 * import defaults form selects. After loading, fetch saved import settings
 * and pre-select saved values.
 * @param {string} service - 'radarr' or 'sonarr'
 */
function loadImportDefaults(service) {
  var skeletonEl = document.getElementById(service + '-import-skeleton');
  var formEl = document.getElementById(service + '-import-form');

  if (!formEl) return;

  // Show skeleton, hide form
  if (skeletonEl) skeletonEl.classList.remove('hidden');
  formEl.classList.add('hidden');

  Promise.all([
    apiFetch('/api/settings/' + service + '/quality-profiles', { method: 'GET' }).then(function (r) { return r.json(); }),
    apiFetch('/api/settings/' + service + '/root-folders', { method: 'GET' }).then(function (r) { return r.json(); }),
    apiFetch('/api/settings/' + service + '/import-settings', { method: 'GET' }).then(function (r) { return r.json(); }),
  ])
    .then(function (results) {
      var profilesData = results[0];
      var foldersData = results[1];
      var settingsData = results[2];

      // Populate quality profiles
      var profileSelect = document.getElementById(service + '-quality-profile');
      if (profileSelect && profilesData.success) {
        profileSelect.innerHTML = '<option value="">Select Quality Profile</option>';
        (profilesData.profiles || []).forEach(function (p) {
          var opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = p.name;
          profileSelect.appendChild(opt);
        });
      }

      // Populate root folders
      var folderSelect = document.getElementById(service + '-root-folder');
      if (folderSelect && foldersData.success) {
        folderSelect.innerHTML = '<option value="">Select Root Folder</option>';
        (foldersData.folders || []).forEach(function (f) {
          var opt = document.createElement('option');
          opt.value = f.id;
          opt.textContent = f.path;
          folderSelect.appendChild(opt);
        });
      }

      // Pre-select saved import settings
      if (settingsData.success && settingsData.settings) {
        var s = settingsData.settings;
        if (profileSelect && s.quality_profile_id) {
          profileSelect.value = String(s.quality_profile_id);
        }
        if (folderSelect && s.root_folder_id) {
          folderSelect.value = String(s.root_folder_id);
        }
        var monitorSelect = document.getElementById(service + '-monitor');
        if (monitorSelect && s.monitored !== null && s.monitored !== undefined) {
          monitorSelect.value = String(s.monitored);
        }
        var searchSelect = document.getElementById(service + '-search-on-add');
        if (searchSelect && s.search_on_add !== null && s.search_on_add !== undefined) {
          searchSelect.value = String(s.search_on_add);
        }
        var tagsInput = document.getElementById(service + '-tags');
        if (tagsInput && s.tag_label) {
          tagsInput.value = s.tag_label;
        }
        // Sonarr only
        var seasonSelect = document.getElementById(service + '-season-folder');
        if (seasonSelect && s.season_folder !== null && s.season_folder !== undefined) {
          seasonSelect.value = String(s.season_folder);
        }
      }

      // Hide skeleton, show form
      if (skeletonEl) skeletonEl.classList.add('hidden');
      formEl.classList.remove('hidden');
    })
    .catch(function (err) {
      if (skeletonEl) skeletonEl.classList.add('hidden');
      formEl.classList.remove('hidden');
      console.error('loadImportDefaults error for ' + service + ':', err);
    });
}

/**
 * Save import settings for a service via AJAX.
 * @param {string} service - 'radarr' or 'sonarr'
 */
function saveImportSettings(service) {
  var saveBtn = document.getElementById('save-' + service + '-import-settings');

  var body = {
    root_folder_id: document.getElementById(service + '-root-folder') ? document.getElementById(service + '-root-folder').value : null,
    quality_profile_id: document.getElementById(service + '-quality-profile') ? document.getElementById(service + '-quality-profile').value : null,
    monitored: document.getElementById(service + '-monitor') ? document.getElementById(service + '-monitor').value === 'true' : null,
    search_on_add: document.getElementById(service + '-search-on-add') ? document.getElementById(service + '-search-on-add').value === 'true' : null,
    tag_label: document.getElementById(service + '-tags') ? document.getElementById(service + '-tags').value.trim() : '',
  };

  // Sonarr only
  var seasonEl = document.getElementById(service + '-season-folder');
  if (seasonEl) {
    body.season_folder = seasonEl.value === 'true';
  }

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
  }

  apiFetch('/api/settings/' + service + '/import-settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Import Settings';
      }
      if (data.success) {
        if (typeof showToast === 'function') showToast(data.message || 'Import settings saved.', 'success');
      } else {
        if (typeof showToast === 'function') showToast(data.message || 'Save failed.', 'error');
      }
    })
    .catch(function (err) {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Import Settings';
      }
      console.error('saveImportSettings error for ' + service + ':', err);
    });
}

// ---------------------------------------------------------------------------
// Helper: status display
// ---------------------------------------------------------------------------

/**
 * Set the inline status message in an element.
 * @param {HTMLElement|null} el - The container element
 * @param {boolean} success - True = green, false = red
 * @param {string} message - The message to display
 */
function setStatus(el, success, message) {
  if (!el) return;
  el.innerHTML = '<span class="' + (success ? 'text-success' : 'text-error') + '">' + escapeHtml(message) + '</span>';
}

/**
 * Escape HTML to prevent XSS in server-returned messages.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Auto-load import defaults for already-configured services
// ---------------------------------------------------------------------------

/**
 * On page load and on Integrations tab activation, load import defaults
 * for any service whose import defaults panel is already visible (i.e. configured).
 */
function maybeLoadImportDefaults() {
  ['radarr', 'sonarr'].forEach(function (service) {
    var panel = document.getElementById(service + '-import-defaults');
    if (panel && !panel.classList.contains('hidden')) {
      // Only load if form hasn't already been populated (check skeleton hidden state)
      var formEl = document.getElementById(service + '-import-form');
      if (formEl && formEl.classList.contains('hidden')) {
        loadImportDefaults(service);
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Wire up Save Import Settings buttons (injected by macro)
// ---------------------------------------------------------------------------

function initImportSettingsButtons() {
  ['radarr', 'sonarr'].forEach(function (service) {
    var btn = document.getElementById('save-' + service + '-import-settings');
    if (btn) {
      btn.addEventListener('click', function () {
        saveImportSettings(service);
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Initialise on DOM ready
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', function () {
  initSettingsTabs();
  initServiceTabs();
  initImportSettingsButtons();
  // Load import defaults for pre-configured services on initial page load
  maybeLoadImportDefaults();
});
