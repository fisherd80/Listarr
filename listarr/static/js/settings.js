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
        btn.classList.remove('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'text-btn-secondary-text', 'border-border-subtle', 'bg-error/15', 'text-error', 'border-error/30');
        btn.classList.add('bg-success/15', 'text-success', 'border-success/30');
        setStatus(statusEl, true, 'Connection successful.');
        showToast('Connection successful.', 'success');
      } else {
        btn.textContent = 'Failed';
        btn.classList.remove('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'text-btn-secondary-text', 'border-border-subtle', 'bg-success/15', 'text-success', 'border-success/30');
        btn.classList.add('bg-error/15', 'text-error', 'border-error/30');
        setStatus(statusEl, false, data.message || 'Connection failed.');
        showToast(data.message || 'Connection failed.', 'error');
      }
      // Reset button text after 3 seconds
      setTimeout(function () {
        btn.textContent = 'Test Connection';
        btn.classList.remove('bg-success/15', 'text-success', 'border-success/30', 'bg-error/15', 'text-error', 'border-error/30');
        btn.classList.add('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'text-btn-secondary-text', 'border-border-subtle');
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
        btn.classList.remove('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'text-btn-secondary-text', 'border-border-subtle', 'bg-error/15', 'text-error', 'border-error/30');
        btn.classList.add('bg-success/15', 'text-success', 'border-success/30');
        setStatus(statusEl, true, 'TMDB API key is valid.');
        showToast('TMDB API key is valid.', 'success');
      } else {
        btn.textContent = 'Failed';
        btn.classList.remove('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'text-btn-secondary-text', 'border-border-subtle', 'bg-success/15', 'text-success', 'border-success/30');
        btn.classList.add('bg-error/15', 'text-error', 'border-error/30');
        setStatus(statusEl, false, data.message || 'Invalid API key.');
        showToast(data.message || 'Invalid API key.', 'error');
      }
      setTimeout(function () {
        btn.textContent = 'Test Connection';
        btn.classList.remove('bg-success/15', 'text-success', 'border-success/30', 'bg-error/15', 'text-error', 'border-error/30');
        btn.classList.add('bg-btn-secondary-bg', 'hover:bg-btn-secondary-hover', 'text-btn-secondary-text', 'border-border-subtle');
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
        var monitorModeSelect = document.getElementById(service + '-monitor-mode');
        if (monitorModeSelect && s.monitor_mode) {
          monitorModeSelect.value = s.monitor_mode;
        }
      }

      // Hide skeleton, show form
      if (skeletonEl) skeletonEl.classList.add('hidden');
      formEl.classList.remove('hidden');
      applyMonitorModeGating(service);
    })
    .catch(function (err) {
      if (skeletonEl) skeletonEl.classList.add('hidden');
      formEl.classList.remove('hidden');
      applyMonitorModeGating(service);
      console.error('loadImportDefaults error for ' + service + ':', err);
    });
}

/**
 * Apply Sonarr import-default monitor/search gating in Settings.
 * @param {string} service - 'radarr' or 'sonarr'
 */
function applyMonitorModeGating(service) {
  var monitorSelect = document.getElementById(service + '-monitor');
  var monitorModeSelect = document.getElementById(service + '-monitor-mode');
  var monitorModeHelp = document.getElementById(service + '-monitor-mode-help');
  var searchSelect = document.getElementById(service + '-search-on-add');
  var searchHelp = document.getElementById(service + '-search-on-add-help');

  if (!monitorModeSelect || !monitorSelect || !searchSelect) { return; }

  applyMonitorGating({
    modeEl: monitorModeSelect,
    searchEl: searchSelect,
    modeHelpEl: monitorModeHelp,
    searchHelpEl: searchHelp,
    unmonitored: monitorSelect.value === 'false',
    modeIsNone: monitorModeSelect.value === 'none',
    beforeDisableSearch: function () { rememberSearchOnAddValue(searchSelect); },
    clearSearch: function () { searchSelect.value = 'false'; },
    restoreSearch: function () {
      if (searchSelect.dataset.restoreValue) {
        searchSelect.value = searchSelect.dataset.restoreValue;
      }
    },
  });
}

/**
 * Stash a search-on-add <select>'s value so gating can restore it after re-enabling.
 * Module-level so the wiring in initImportSettingsButtons shares one definition of the
 * restore key with the gating above.
 */
function rememberSearchOnAddValue(searchSelect) {
  if (searchSelect && !searchSelect.disabled) {
    searchSelect.dataset.restoreValue = searchSelect.value || 'false';
  }
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
  var monitorModeEl = document.getElementById(service + '-monitor-mode');
  if (monitorModeEl) {
    body.monitor_mode = monitorModeEl.value;
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
    var monitorSelect = document.getElementById(service + '-monitor');
    if (monitorSelect) {
      monitorSelect.addEventListener('change', function () {
        applyMonitorModeGating(service);
      });
    }
    var monitorModeSelect = document.getElementById(service + '-monitor-mode');
    if (monitorModeSelect) {
      monitorModeSelect.addEventListener('change', function () {
        applyMonitorModeGating(service);
      });
    }
    var searchSelect = document.getElementById(service + '-search-on-add');
    if (searchSelect) {
      searchSelect.addEventListener('change', function () {
        rememberSearchOnAddValue(searchSelect);
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Initialise on DOM ready
// ---------------------------------------------------------------------------


// ---------------------------------------------------------------------------
// General tab: timezone filter, live preview, save (Phase 14)
// ---------------------------------------------------------------------------

function initTimezoneFilter() {
  var filter = document.getElementById('tz-filter');
  var select = document.getElementById('app-timezone');
  var emptyEl = document.getElementById('tz-filter-empty');
  if (!filter || !select) return;

  // IN-05: several native <select> implementations ignore the `hidden` attribute on
  // <option>/<optgroup>. Toggling a display:none class is the portable form; the
  // property is set too for the engines that do honour it.
  function setHidden(el, hidden) {
    el.classList.toggle('hidden', hidden);
    el.hidden = hidden;
  }

  function isHidden(el) {
    return el.classList.contains('hidden');
  }

  // WR-06: "matches the query" and "is visible" are no longer the same set, because the
  // System default entry and the current selection stay visible regardless. The Enter
  // shortcut must key off matches, or a lone hit would stop being a lone hit.
  var matches = null;

  function resetAll() {
    var i;
    var options = select.options;
    matches = null;
    for (i = 0; i < options.length; i++) setHidden(options[i], false);
    var groups = select.getElementsByTagName('optgroup');
    for (i = 0; i < groups.length; i++) setHidden(groups[i], false);
    if (emptyEl) {
      emptyEl.textContent = '';
      emptyEl.classList.add('hidden');
    }
  }

  function applyFilter() {
    var typed = filter.value.trim();
    if (!typed) {
      resetAll();
      return;
    }

    var query = typed.toLowerCase();
    var options = select.options;
    var groups = select.getElementsByTagName('optgroup');
    var i;
    var j;

    matches = [];

    for (i = 0; i < options.length; i++) {
      var hit = options[i].textContent.toLowerCase().indexOf(query) !== -1;
      if (hit && options[i].value !== '') matches.push(options[i]);
      // The "System default" entry has no value and always stays selectable.
      // WR-06: so does the current selection. Chrome and Safari render a <select>
      // whose selected <option> is hidden as an empty control, so filtering while a
      // zone is saved blanked the field and implied the setting had been lost.
      if (options[i].value === '' || options[i].selected) {
        setHidden(options[i], false);
        continue;
      }
      setHidden(options[i], !hit);
    }

    for (i = 0; i < groups.length; i++) {
      var kids = groups[i].getElementsByTagName('option');
      var anyMatch = false;
      for (j = 0; j < kids.length; j++) {
        // IN-05: ask whether the child *matched*, not whether it is visible. The WR-06
        // fix forces the selected option visible whether it matches or not, so reading
        // the hidden class kept the saved zone's region header on screen for a query
        // that matched nothing in it - one unrelated entry under a heading that implied
        // it was a result.
        if (matches.indexOf(kids[j]) !== -1) {
          anyMatch = true;
          break;
        }
      }
      setHidden(groups[i], !anyMatch);
    }

    if (emptyEl) {
      if (matches.length === 0) {
        // textContent, never innerHTML - the query is user input (T-14-02).
        emptyEl.textContent = 'No zones match "' + typed + '".';
        emptyEl.classList.remove('hidden');
      } else {
        emptyEl.textContent = '';
        emptyEl.classList.add('hidden');
      }
    }
  }

  filter.addEventListener('input', applyFilter);

  filter.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      // Never submit anything from the filter.
      e.preventDefault();
      if (matches && matches.length === 1) {
        select.value = matches[0].value;
        select.dispatchEvent(new Event('change'));
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      filter.value = '';
      resetAll();
      filter.focus();
    }
  });
}

function initTimezonePreview() {
  var previewEl = document.getElementById('tz-preview');
  var select = document.getElementById('app-timezone');
  if (!previewEl) return;

  var valueSpan = previewEl.querySelector('span');
  var spanClass = valueSpan ? valueSpan.className : 'text-text-base font-medium tabular-nums';

  // WR-03: "System default" (value === '') must preview the fallback zone the label
  // promises, not window.APP_TZ (which is the currently *saved* zone).
  var fallbackZone = previewEl.dataset.fallbackZone || window.APP_TZ;

  function renderPreview() {
    var zone = select && select.value ? select.value : fallbackZone;
    try {
      // IN-05: hour12:false matches the server-rendered %H:%M:%S preview, so the
      // value does not visibly flip format one second after load.
      var fmt = new Intl.DateTimeFormat(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: zone,
        timeZoneName: 'short',
      });
      var text = fmt.format(new Date());
      // The error branch replaces the whole node, so rebuild the styled span on recovery.
      if (!previewEl.contains(valueSpan)) {
        previewEl.textContent = 'Current time: ';
        valueSpan = document.createElement('span');
        valueSpan.className = spanClass;
        previewEl.appendChild(valueSpan);
      }
      valueSpan.textContent = text;
    } catch (err) {
      previewEl.textContent = 'Current time: unavailable for this zone';
    }
  }

  renderPreview();
  if (select) select.addEventListener('change', renderPreview);

  // IN-05: the timer used to run unconditionally and forever, rebuilding an
  // Intl.DateTimeFormat every second even while the General panel sat hidden behind
  // another settings tab. Skip the work when it cannot be seen, and keep the handle so
  // it can actually be cancelled. It still ticks after a failure, so recovery is
  // automatic once a valid zone is picked.
  var panel = document.getElementById('tab-general');
  var previewTimer = setInterval(function () {
    if (!panel || !panel.classList.contains('hidden')) renderPreview();
  }, 1000);

  window.addEventListener('pagehide', function () {
    clearInterval(previewTimer);
  });
}

/**
 * WR-04: bring the already-rendered page into line with the zone that was just saved.
 *
 * Everything below was emitted server-side against the previous zone, so without this a
 * green "Timezone saved" toast sat next to timestamps still formatted in the old zone
 * and, in the unresolvable case, next to a warning banner that had become false.
 *
 * Deliberately not refreshed: the "System default (currently X)" label and
 * data-fallback-zone. Both derive from get_app_timezone_fallback_name(), which reads only
 * the TZ environment variable — saving an application timezone cannot change it.
 */
function applySavedTimezoneToPage(data) {
  if (data.effective_tz) {
    window.APP_TZ = data.effective_tz;
    // Re-render every tooltip that was built from the old zone.
    if (typeof applyAppTzTooltips === 'function') applyAppTzTooltips();
  }

  // A save can only store a zone that resolves, so this banner is stale by definition
  // once the request succeeds. Guarded on the server's own answer rather than assumed.
  if (!data.unresolvable) {
    var notice = document.getElementById('tz-fallback-notice');
    if (notice) notice.remove();
  }

  // The "Current" optgroup exists only to carry a saved zone that is not in the curated
  // list. Once something else is selected it is no longer current, and leaving the label
  // as-is presents a stale zone as the active one.
  //
  // IN-04: relabel rather than remove. That group is the only place a non-curated zone
  // appears in the picker, so removing it made the zone the user had just moved away from
  // unreachable - it is in no region group, and nothing else would ever re-add it. They
  // could not change their mind without reloading the page.
  var select = document.getElementById('app-timezone');
  if (select) {
    var groups = select.getElementsByTagName('optgroup');
    for (var i = groups.length - 1; i >= 0; i--) {
      if (groups[i].label !== 'Current') continue;
      var opt = groups[i].getElementsByTagName('option')[0];
      if (!opt || opt.value !== select.value) groups[i].label = 'Other';
    }
  }
}

function saveGeneralTimezone() {
  var select = document.getElementById('app-timezone');
  var saveBtn = document.getElementById('general-save-btn');
  var statusEl = document.getElementById('general-status');
  if (!select || !saveBtn) return;

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving\u2026';

  apiFetch('/api/settings/general', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ timezone: select.value }),
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';

      if (data.success) {
        // WR-04: the zone is saved, so the page's rendered state now describes the
        // *previous* one. Refresh it before anything returns early below - this holds
        // whether or not the reschedule succeeded.
        applySavedTimezoneToPage(data);

        // IN-02: the save succeeded but the reschedule blew up - do not toast the
        // reassuring "nothing needed rescheduling" message.
        if (data.reschedule_error) {
          var failMsg = 'Timezone saved, but scheduled lists could not be re-applied \u2014 see logs.';
          setStatus(statusEl, false, failMsg);
          showToast(failMsg, 'warning', 6000);
          return;
        }

        setStatus(statusEl, true, 'Timezone saved.');

        var n = data.n_rescheduled || 0;
        var m = data.n_failed || 0;
        var msg;

        // WR-04: the rebuild declined rather than failed (locked DB, busy scheduler), so
        // it returned zero counts without raising. Reporting that as "nothing needed
        // rescheduling" told the user the opposite of the truth - every list is still on
        // the old zone. The convergence poll retries on its own, so say that instead.
        if (data.reschedule_pending) {
          var q = data.n_pending || 0;
          if (q === 1) {
            msg = 'Timezone saved. 1 scheduled list could not be re-applied yet — retrying within ~60s.';
          } else if (q > 1) {
            msg = 'Timezone saved. ' + q + ' scheduled lists could not be re-applied yet — retrying within ~60s.';
          } else {
            msg = 'Timezone saved. Scheduled lists could not be re-applied yet — retrying within ~60s.';
          }
          showToast(msg, 'warning', 6000);
          return;
        }

        if (data.scheduler_worker) {
          if (n === 0) {
            msg = 'Timezone saved. No scheduled lists needed rescheduling.';
          } else if (n === 1) {
            msg = 'Timezone saved. 1 scheduled list rescheduled.';
          } else {
            msg = 'Timezone saved. ' + n + ' scheduled lists rescheduled.';
          }
          if (m > 0) {
            msg += m === 1
              ? ' (1 list could not be rescheduled \u2014 see logs)'
              : ' (' + m + ' lists could not be rescheduled \u2014 see logs)';
          }
        } else {
          // IN-03: this worker rescheduled nothing; n_pending is what the scheduler
          // worker still has to pick up on its next convergence poll.
          var p = data.n_pending || 0;
          if (p === 0) {
            msg = 'Timezone saved. No scheduled lists to re-apply.';
          } else if (p === 1) {
            msg = 'Timezone saved. 1 scheduled list will re-apply within ~60s.';
          } else {
            msg = 'Timezone saved. ' + p + ' scheduled lists will re-apply within ~60s.';
          }
        }

        showToast(msg, m > 0 ? 'warning' : 'success', m > 0 ? 6000 : 3000);
      } else {
        var errMsg = data.message || 'Unknown or invalid timezone. Nothing was saved.';
        setStatus(statusEl, false, errMsg);
        showToast(errMsg, 'error', 5000);
      }
    })
    .catch(function (err) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
      setStatus(statusEl, false, 'Request failed.');
      console.error('saveGeneralTimezone error:', err);
    });
}

document.addEventListener('DOMContentLoaded', function () {
  initSettingsTabs();
  initTimezoneFilter();
  initTimezonePreview();
  initServiceTabs();
  initImportSettingsButtons();

  // If the URL contains a hash that matches a settings tab, activate it.
  // e.g. /settings#account activates the Account tab.
  // WR-09: never splice location.hash into a selector - a hash containing a quote
  // makes querySelector throw SyntaxError out of this listener, which would stop
  // maybeLoadImportDefaults() below from ever running.
  var hash = window.location.hash ? window.location.hash.slice(1) : '';
  if (hash) {
    var targetTab = Array.prototype.find.call(
      document.querySelectorAll('.settings-tab'),
      function (tab) { return tab.dataset.tab === hash; }
    );
    if (targetTab) {
      targetTab.click();
    }
  }

  // Load import defaults for pre-configured services on initial page load
  maybeLoadImportDefaults();
});
