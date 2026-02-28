// ----------------------
// Create List JavaScript — tab switching, accordion, live preview, cron picker, AJAX submit
// ----------------------

// ---------------------
// Constants
// ---------------------

var PREVIEW_DEBOUNCE_MS = 500;
var CRON_VALIDATE_DEBOUNCE_MS = 600;

// Currently active tab: 'presets' or 'custom'
var activeTab = 'presets';

// Selected preset key (e.g. 'trending_movies')
var selectedPreset = null;

// Debounce timer IDs
var previewTimer = null;
var cronValidateTimer = null;

// ---------------------
// Tab Switching
// ---------------------

/**
 * Initialize tab toggle buttons (#tab-presets, #tab-custom).
 */
function initTabs() {
  var btnPresets = document.getElementById('tab-presets');
  var btnCustom = document.getElementById('tab-custom');

  if (!btnPresets || !btnCustom) { return; }

  btnPresets.addEventListener('click', function () {
    switchTab('presets');
  });

  btnCustom.addEventListener('click', function () {
    switchTab('custom');
  });
}

/**
 * Switch the active tab and reset accordion state on newly visible panel.
 * @param {string} tab - 'presets' or 'custom'
 */
function switchTab(tab) {
  activeTab = tab;

  var panelPresets = document.getElementById('panel-presets');
  var panelCustom = document.getElementById('panel-custom');
  var btnPresets = document.getElementById('tab-presets');
  var btnCustom = document.getElementById('tab-custom');

  if (!panelPresets || !panelCustom) { return; }

  if (tab === 'presets') {
    panelPresets.classList.remove('hidden');
    panelCustom.classList.add('hidden');

    btnPresets.classList.add('border-blue-500', 'text-white');
    btnPresets.classList.remove('border-transparent', 'text-gray-400');
    btnCustom.classList.add('border-transparent', 'text-gray-400');
    btnCustom.classList.remove('border-blue-500', 'text-white');

    // Reset custom panel to step 1
    resetPanelToStep('custom', 1);
  } else {
    panelCustom.classList.remove('hidden');
    panelPresets.classList.add('hidden');

    btnCustom.classList.add('border-blue-500', 'text-white');
    btnCustom.classList.remove('border-transparent', 'text-gray-400');
    btnPresets.classList.add('border-transparent', 'text-gray-400');
    btnPresets.classList.remove('border-blue-500', 'text-white');

    // Reset preset panel to step 1
    resetPanelToStep('preset', 1);
  }
}

/**
 * Reset a panel's accordion to show only the first step expanded.
 * @param {string} panelName - 'preset' or 'custom'
 * @param {number} targetStep - step number to leave expanded
 */
function resetPanelToStep(panelName, targetStep) {
  var sections = document.querySelectorAll('[data-step][data-panel="' + panelName + '"].accordion-body');
  for (var i = 0; i < sections.length; i++) {
    var stepNum = parseInt(sections[i].getAttribute('data-step'), 10);
    if (stepNum === targetStep) {
      sections[i].classList.remove('hidden');
    } else {
      sections[i].classList.add('hidden');
    }
  }
  updateStepBadges(panelName);
}

// ---------------------
// Accordion
// ---------------------

/**
 * Initialize all accordion headers for click-toggle.
 */
function initAccordion() {
  var headers = document.querySelectorAll('.accordion-header');
  for (var i = 0; i < headers.length; i++) {
    headers[i].addEventListener('click', (function (header) {
      return function () {
        var step = parseInt(header.getAttribute('data-step'), 10);
        var panel = header.getAttribute('data-panel');
        toggleStep(panel, step);
      };
    })(headers[i]));
  }

  // "Next" buttons
  var nextBtns = document.querySelectorAll('.next-step-btn');
  for (var j = 0; j < nextBtns.length; j++) {
    nextBtns[j].addEventListener('click', (function (btn) {
      return function (e) {
        e.stopPropagation();
        var currentStep = parseInt(btn.getAttribute('data-current-step'), 10);
        var panel = btn.getAttribute('data-panel');
        collapseStep(panel, currentStep);
        expandStep(panel, currentStep + 1);
      };
    })(nextBtns[j]));
  }
}

/**
 * Toggle accordion step open/closed.
 * @param {string} panelName - 'preset' or 'custom'
 * @param {number} stepNum - step number
 */
function toggleStep(panelName, stepNum) {
  var body = document.querySelector('.accordion-body[data-step="' + stepNum + '"][data-panel="' + panelName + '"]');
  if (!body) { return; }

  if (body.classList.contains('hidden')) {
    expandStep(panelName, stepNum);
  } else {
    collapseStep(panelName, stepNum);
  }
}

/**
 * Expand (show) an accordion step and update chevron.
 * @param {string} panelName - 'preset' or 'custom'
 * @param {number} stepNum - step number
 */
function expandStep(panelName, stepNum) {
  var body = document.querySelector('.accordion-body[data-step="' + stepNum + '"][data-panel="' + panelName + '"]');
  if (!body) { return; }

  body.classList.remove('hidden');
  updateChevron(panelName, stepNum, true);
  updateStepBadges(panelName);

  // Scroll into view
  var header = document.querySelector('.accordion-header[data-step="' + stepNum + '"][data-panel="' + panelName + '"]');
  if (header) {
    setTimeout(function () {
      header.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }
}

/**
 * Collapse (hide) an accordion step.
 * @param {string} panelName - 'preset' or 'custom'
 * @param {number} stepNum - step number
 */
function collapseStep(panelName, stepNum) {
  var body = document.querySelector('.accordion-body[data-step="' + stepNum + '"][data-panel="' + panelName + '"]');
  if (!body) { return; }

  body.classList.add('hidden');
  updateChevron(panelName, stepNum, false);
}

/**
 * Update the chevron rotation for a step header.
 * @param {string} panelName - 'preset' or 'custom'
 * @param {number} stepNum - step number
 * @param {boolean} expanded - true = rotated (open), false = default (closed)
 */
function updateChevron(panelName, stepNum, expanded) {
  var header = document.querySelector('.accordion-header[data-step="' + stepNum + '"][data-panel="' + panelName + '"]');
  if (!header) { return; }
  var chevron = header.querySelector('.accordion-chevron');
  if (!chevron) { return; }

  if (expanded) {
    chevron.classList.add('rotate-180');
  } else {
    chevron.classList.remove('rotate-180');
  }
}

/**
 * Update step number badge colors: active steps get blue-600, inactive get gray-600.
 * @param {string} panelName - 'preset' or 'custom'
 */
function updateStepBadges(panelName) {
  var headers = document.querySelectorAll('.accordion-header[data-panel="' + panelName + '"]');
  for (var i = 0; i < headers.length; i++) {
    var header = headers[i];
    var stepNum = parseInt(header.getAttribute('data-step'), 10);
    var body = document.querySelector('.accordion-body[data-step="' + stepNum + '"][data-panel="' + panelName + '"]');
    var badge = header.querySelector('span.flex-shrink-0');
    var titleEl = header.querySelector('span.text-sm');
    var expanded = body && !body.classList.contains('hidden');

    if (badge) {
      if (expanded) {
        badge.className = badge.className.replace('bg-gray-600 text-gray-300', 'bg-blue-600 text-white');
        badge.classList.remove('bg-gray-600', 'text-gray-300');
        badge.classList.add('bg-blue-600', 'text-white');
      } else {
        badge.classList.remove('bg-blue-600', 'text-white');
        badge.classList.add('bg-gray-600', 'text-gray-300');
      }
    }

    if (titleEl) {
      if (expanded) {
        titleEl.classList.remove('text-gray-400');
        titleEl.classList.add('text-gray-100');
      } else {
        titleEl.classList.remove('text-gray-100');
        titleEl.classList.add('text-gray-400');
      }
    }
  }
}

// ---------------------
// Preset Cards
// ---------------------

/**
 * Initialize preset card click listeners.
 */
function initPresetCards() {
  var cards = document.querySelectorAll('.preset-card');
  for (var i = 0; i < cards.length; i++) {
    cards[i].addEventListener('click', (function (card) {
      return function () {
        selectPresetCard(card);
      };
    })(cards[i]));
  }
}

/**
 * Handle preset card selection: highlight card, set service, load defaults, expand step 2.
 * @param {Element} card - The clicked preset card button
 */
function selectPresetCard(card) {
  var preset = card.getAttribute('data-preset');
  var service = card.getAttribute('data-service');
  var title = card.getAttribute('data-title');

  selectedPreset = preset;

  // Update visual selection: clear all cards, highlight selected
  var allCards = document.querySelectorAll('.preset-card');
  for (var i = 0; i < allCards.length; i++) {
    allCards[i].classList.remove('border-amber-500', 'border-blue-500', 'bg-amber-900/30', 'bg-blue-900/30');
    allCards[i].classList.add('border-gray-600');
  }

  if (service === 'radarr') {
    card.classList.remove('border-gray-600');
    card.classList.add('border-amber-500', 'bg-amber-900/30');
  } else {
    card.classList.remove('border-gray-600');
    card.classList.add('border-blue-500', 'bg-blue-900/30');
  }

  // Update step 1 summary
  var summary = document.querySelector('.preset-step1-summary');
  if (summary) { summary.textContent = '— ' + title; }

  // Set service
  var serviceInput = document.getElementById('preset-service');
  if (serviceInput) { serviceInput.value = service; }

  // Update service display
  var serviceDisplay = document.getElementById('preset-service-display');
  if (serviceDisplay) {
    var serviceLabel = service === 'radarr' ? 'Radarr (Movies)' : 'Sonarr (TV Shows)';
    serviceDisplay.textContent = serviceLabel;
    serviceDisplay.className = service === 'radarr' ? 'text-sm text-amber-400 font-medium' : 'text-sm text-blue-400 font-medium';
  }

  // Auto-populate list name
  var nameInput = document.getElementById('preset-list-name');
  if (nameInput && !nameInput.dataset.userEdited) {
    nameInput.value = title;
  }

  // Load import defaults
  loadImportDefaults(service, 'preset');

  // Trigger preview
  fetchPreview('preset');

  // Expand step 2
  collapseStep('preset', 1);
  expandStep('preset', 2);
}

// ---------------------
// Service Selector (Custom Panel)
// ---------------------

/**
 * Initialize service selection buttons in the custom panel.
 */
function initServiceSelector() {
  var btns = document.querySelectorAll('.custom-service-btn');
  for (var i = 0; i < btns.length; i++) {
    btns[i].addEventListener('click', (function (btn) {
      return function () {
        selectCustomService(btn.getAttribute('data-service'));
      };
    })(btns[i]));
  }
}

/**
 * Handle custom service selection.
 * @param {string} service - 'radarr' or 'sonarr'
 */
function selectCustomService(service) {
  var serviceInput = document.getElementById('custom-service');
  if (serviceInput) { serviceInput.value = service; }

  // Update button styles
  var btns = document.querySelectorAll('.custom-service-btn');
  for (var i = 0; i < btns.length; i++) {
    var btn = btns[i];
    var btnService = btn.getAttribute('data-service');
    btn.classList.remove('border-amber-500', 'bg-amber-900/20', 'text-amber-300',
                         'border-blue-500', 'bg-blue-900/20', 'text-blue-300',
                         'border-gray-600', 'text-gray-400');

    if (btnService === service) {
      if (service === 'radarr') {
        btn.classList.add('border-amber-500', 'bg-amber-900/20', 'text-amber-300');
      } else {
        btn.classList.add('border-blue-500', 'bg-blue-900/20', 'text-blue-300');
      }
    } else {
      btn.classList.add('border-gray-600', 'text-gray-400');
    }
  }

  // Swap genre grids for selected service
  var movieGenres = document.getElementById('custom-movie-genres');
  var tvGenres = document.getElementById('custom-tv-genres');

  if (service === 'radarr') {
    if (movieGenres) { movieGenres.classList.remove('hidden'); }
    if (tvGenres) { tvGenres.classList.add('hidden'); }
  } else {
    if (movieGenres) { movieGenres.classList.add('hidden'); }
    if (tvGenres) { tvGenres.classList.remove('hidden'); }
  }

  // Reset all genre pills to neutral state when switching services
  var allPills = document.querySelectorAll('.genre-pill');
  for (var j = 0; j < allPills.length; j++) {
    var pill = allPills[j];
    pill.setAttribute('data-state', 'neutral');
    pill.classList.remove('border-green-500', 'text-green-300', 'bg-green-900/20',
                          'border-red-500', 'text-red-300', 'bg-red-900/20');
    pill.classList.add('border-gray-600', 'text-gray-300', 'bg-transparent');
    var pillIcon = pill.querySelector('.genre-pill-icon');
    if (pillIcon) { pillIcon.classList.add('hidden'); }
  }

  // Update step 1 summary
  var summary = document.querySelector('.custom-step1-summary');
  if (summary) {
    summary.textContent = service === 'radarr' ? '— Radarr (Movies)' : '— Sonarr (TV Shows)';
  }

  // Load import defaults for new service
  loadImportDefaults(service, 'custom');

  // Trigger preview refresh
  schedulePreview('custom');
}

// ---------------------
// Live Preview
// ---------------------

/**
 * Schedule a debounced preview refresh.
 * @param {string} panelName - 'preset' or 'custom'
 */
function schedulePreview(panelName) {
  if (previewTimer) { clearTimeout(previewTimer); }
  previewTimer = setTimeout(function () {
    fetchPreview(panelName);
  }, PREVIEW_DEBOUNCE_MS);
}

/**
 * Collect filter values and fetch a live preview from /lists/wizard/preview.
 * @param {string} panelName - 'preset' or 'custom'
 */
function fetchPreview(panelName) {
  // Custom panel preview only (preset panel uses the preset endpoint)
  if (panelName === 'preset') {
    // For presets we don't show a separate preview panel — skip
    return;
  }

  var previewPanel = document.getElementById('custom-preview-panel');
  var previewCount = document.getElementById('custom-preview-count');
  if (!previewPanel) { return; }

  var serviceInput = document.getElementById('custom-service');
  var service = serviceInput ? serviceInput.value : 'radarr';

  var filters = collectFilters();

  // Show loading state
  previewPanel.innerHTML = '<div class="text-sm text-gray-500 text-center py-8">Loading...</div>';
  if (previewCount) { previewCount.textContent = ''; }

  fetch('/lists/wizard/preview', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      service: service,
      preset: null,
      filters: filters
    })
  })
  .then(function (response) { return response.json(); })
  .then(function (data) {
    if (data.error) {
      previewPanel.innerHTML = '<div class="text-sm text-red-400 text-center py-8">' + escapeHtml(data.error) + '</div>';
      return;
    }

    var items = data.items || [];

    if (items.length === 0) {
      previewPanel.innerHTML = '<div class="text-sm text-gray-400 text-center py-8 px-4">No titles match these filters. Try broadening your criteria.</div>';
      if (previewCount) { previewCount.textContent = '0 results'; }
      return;
    }

    if (previewCount) { previewCount.textContent = items.length + ' results'; }

    var html = '<ul class="divide-y divide-gray-700">';
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var rating = item.rating ? parseFloat(item.rating).toFixed(1) : '—';
      html += '<li class="flex items-center justify-between py-2 px-1 gap-2">' +
              '<span class="text-sm text-gray-200 truncate" title="' + escapeHtml(item.title) + '">' + escapeHtml(item.title) + '</span>' +
              '<span class="flex-shrink-0 text-xs text-gray-500 whitespace-nowrap">' + escapeHtml(String(item.year || '')) + ' · ' + rating + '</span>' +
              '</li>';
    }
    html += '</ul>';
    previewPanel.innerHTML = html;
  })
  .catch(function (err) {
    previewPanel.innerHTML = '<div class="text-sm text-red-400 text-center py-8">Preview unavailable.</div>';
    if (previewCount) { previewCount.textContent = ''; }
  });
}

/**
 * Collect all filter inputs from the custom panel.
 * @returns {Object} filters object matching wizard/preview API shape
 */
function collectFilters() {
  var genresInclude = [];
  var genresExclude = [];

  var serviceInput = document.getElementById('custom-service');
  var service = serviceInput ? serviceInput.value : 'radarr';

  // Collect included genre pills (only from current service)
  var includeActive = document.querySelectorAll('.genre-pill[data-state="include"][data-service="' + service + '"]');
  for (var i = 0; i < includeActive.length; i++) {
    genresInclude.push(parseInt(includeActive[i].getAttribute('data-genre-id'), 10));
  }

  // Collect excluded genre pills (only from current service)
  var excludeActive = document.querySelectorAll('.genre-pill[data-state="exclude"][data-service="' + service + '"]');
  for (var j = 0; j < excludeActive.length; j++) {
    genresExclude.push(parseInt(excludeActive[j].getAttribute('data-genre-id'), 10));
  }

  var languageEl = document.getElementById('custom-language');
  var yearMinEl = document.getElementById('custom-year-min');
  var yearMaxEl = document.getElementById('custom-year-max');
  var ratingMinEl = document.getElementById('custom-rating-min');
  var limitEl = document.getElementById('custom-limit');

  return {
    genres_include: genresInclude,
    genres_exclude: genresExclude,
    language: languageEl ? languageEl.value : '',
    year_min: yearMinEl && yearMinEl.value ? parseInt(yearMinEl.value, 10) : null,
    year_max: yearMaxEl && yearMaxEl.value ? parseInt(yearMaxEl.value, 10) : null,
    rating_min: ratingMinEl && ratingMinEl.value ? parseFloat(ratingMinEl.value) : null,
    limit: limitEl && limitEl.value ? parseInt(limitEl.value, 10) : 20
  };
}

// ---------------------
// Cron Picker
// ---------------------

/**
 * Initialize the visual cron pickers for both panels.
 */
function initCronPicker() {
  initCronPickerForPanel('preset');
  initCronPickerForPanel('custom');
  initCronPickerForPanel('edit');
}

/**
 * Initialize cron picker for a specific panel.
 * @param {string} panelName - 'preset' or 'custom'
 */
function initCronPickerForPanel(panelName) {
  var freqSelect = document.getElementById(panelName + '-freq');
  var timeSelect = document.getElementById(panelName + '-time');
  var daySelect = document.getElementById(panelName + '-day');
  var timeRow = document.getElementById(panelName + '-time-row');
  var dayRow = document.getElementById(panelName + '-day-row');
  var advancedToggle = document.getElementById(panelName + '-advanced-toggle');
  var advancedSection = document.getElementById(panelName + '-cron-advanced');
  var cronRaw = document.getElementById(panelName + '-cron-raw');
  var cronDescription = document.getElementById(panelName + '-cron-description');
  var cronValue = document.getElementById(panelName + '-cron-value');

  if (!freqSelect) { return; }

  // Build cron string from current picker state
  function buildCron() {
    var freq = freqSelect.value;
    var hour = timeSelect ? timeSelect.value : '0';
    var day = daySelect ? daySelect.value : '0';

    var cron = '';
    if (freq === 'manual') {
      cron = '';
    } else if (freq === 'hourly') {
      cron = '0 * * * *';
    } else if (freq === 'daily') {
      cron = '0 ' + parseInt(hour, 10) + ' * * *';
    } else if (freq === 'weekly') {
      cron = '0 ' + parseInt(hour, 10) + ' * * ' + day;
    } else if (freq === 'custom') {
      cron = cronRaw ? cronRaw.value : '';
    }

    if (cronValue) { cronValue.value = cron; }

    // Update step summary
    var summaryEl = document.querySelector('.' + panelName + '-step4-summary');
    if (summaryEl) {
      if (freq === 'manual') {
        summaryEl.textContent = '— Manual';
      } else if (cron) {
        summaryEl.textContent = '— ' + cron;
      }
    }
  }

  // Update time/day row visibility
  function updateRowVisibility() {
    var freq = freqSelect.value;

    if (timeRow) {
      if (freq === 'daily' || freq === 'weekly') {
        timeRow.classList.remove('hidden');
      } else {
        timeRow.classList.add('hidden');
      }
    }

    if (dayRow) {
      if (freq === 'weekly') {
        dayRow.classList.remove('hidden');
      } else {
        dayRow.classList.add('hidden');
      }
    }

    if (advancedSection) {
      if (freq === 'custom') {
        advancedSection.classList.remove('hidden');
      } else if (freq !== 'custom') {
        // Only hide if not toggled manually
      }
    }
  }

  freqSelect.addEventListener('change', function () {
    updateRowVisibility();
    buildCron();
  });

  if (timeSelect) {
    timeSelect.addEventListener('change', function () { buildCron(); });
  }

  if (daySelect) {
    daySelect.addEventListener('change', function () { buildCron(); });
  }

  // Advanced toggle
  if (advancedToggle && advancedSection) {
    advancedToggle.addEventListener('click', function () {
      advancedSection.classList.toggle('hidden');
      var isVisible = !advancedSection.classList.contains('hidden');
      advancedToggle.textContent = isVisible
        ? 'Hide advanced cron expression'
        : 'Advanced: Enter raw cron expression';
    });
  }

  // Raw cron input validation
  if (cronRaw) {
    cronRaw.addEventListener('input', function () {
      buildCron();
      if (cronValidateTimer) { clearTimeout(cronValidateTimer); }
      cronValidateTimer = setTimeout(function () {
        validateCronExpression(cronRaw.value, cronDescription);
      }, CRON_VALIDATE_DEBOUNCE_MS);
    });
  }

  // Initialize row visibility and build initial cron
  updateRowVisibility();
  buildCron();
}

/**
 * Validate a cron expression via /api/cron/validate and display the description.
 * @param {string} expr - cron expression
 * @param {Element} descEl - element to display description in
 */
function validateCronExpression(expr, descEl) {
  if (!expr || !descEl) { return; }

  var encoded = encodeURIComponent(expr);
  fetch('/api/cron/validate?expr=' + encoded)
  .then(function (response) { return response.json(); })
  .then(function (data) {
    if (data.valid && data.description) {
      descEl.textContent = data.description;
      descEl.className = 'text-xs text-green-400';
    } else if (data.error) {
      descEl.textContent = data.error;
      descEl.className = 'text-xs text-red-400';
    } else {
      descEl.textContent = '';
    }
  })
  .catch(function () {
    descEl.textContent = '';
  });
}

// ---------------------
// Import Defaults
// ---------------------

/**
 * Load quality profiles, root folders, and tags from wizard/defaults endpoint.
 * @param {string} service - 'radarr' or 'sonarr'
 * @param {string} panelName - 'preset' or 'custom'
 */
function loadImportDefaults(service, panelName) {
  var containerId = panelName + '-import-settings';
  var container = document.getElementById(containerId);
  if (!container) { return; }

  container.innerHTML = '<div class="text-sm text-gray-500 italic">Loading import settings...</div>';

  fetch('/lists/wizard/defaults/' + service)
  .then(function (response) { return response.json(); })
  .then(function (data) {
    if (data.error) {
      container.innerHTML = '<div class="text-sm text-red-400">' + escapeHtml(data.error) + '</div>';
      return;
    }

    var options = data.options || {};
    var profiles = options.quality_profiles || [];
    var folders = options.root_folders || [];
    var tags = options.tags || [];
    var defaults = data.defaults || {};

    var prefix = panelName + '-import';

    var html = '<div class="space-y-3">';

    // Quality profile
    html += '<div>';
    html += '<label for="' + prefix + '-quality" class="block text-xs font-medium text-gray-300 mb-1">Quality Profile</label>';
    html += '<select id="' + prefix + '-quality" class="text-sm bg-gray-700 border border-gray-600 text-gray-100 rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500">';
    for (var i = 0; i < profiles.length; i++) {
      var p = profiles[i];
      var sel = (defaults.quality_profile_id && defaults.quality_profile_id === p.id) ? ' selected' : '';
      html += '<option value="' + p.id + '"' + sel + '>' + escapeHtml(p.name) + '</option>';
    }
    if (profiles.length === 0) {
      html += '<option value="">No profiles available</option>';
    }
    html += '</select></div>';

    // Root folder
    html += '<div>';
    html += '<label for="' + prefix + '-folder" class="block text-xs font-medium text-gray-300 mb-1">Root Folder</label>';
    html += '<select id="' + prefix + '-folder" class="w-full text-sm bg-gray-700 border border-gray-600 text-gray-100 rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500">';
    for (var j = 0; j < folders.length; j++) {
      var f = folders[j];
      var fSel = (defaults.root_folder && defaults.root_folder === f.path) ? ' selected' : '';
      html += '<option value="' + escapeHtml(f.path) + '"' + fSel + '>' + escapeHtml(f.path) + '</option>';
    }
    if (folders.length === 0) {
      html += '<option value="">No root folders available</option>';
    }
    html += '</select></div>';

    // Tag (optional) — text input with datalist for existing tags + ability to create new
    html += '<div>';
    html += '<label for="' + prefix + '-tag" class="block text-xs font-medium text-gray-300 mb-1">Tag (optional)</label>';
    html += '<input type="text" id="' + prefix + '-tag" list="' + prefix + '-tag-list" placeholder="None"';
    html += ' class="text-sm bg-gray-700 border border-gray-600 text-gray-100 rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 w-full">';
    html += '<datalist id="' + prefix + '-tag-list">';
    for (var k = 0; k < tags.length; k++) {
      var t = tags[k];
      html += '<option value="' + escapeHtml(t.label || String(t.id)) + '">';
    }
    html += '</datalist>';
    html += '<p class="mt-1 text-xs text-gray-500">Created automatically if it doesn\'t exist. Letters, numbers, hyphens.</p>';
    html += '</div>';

    // Monitored checkbox
    var monitoredChecked = (defaults.monitored !== false) ? ' checked' : '';
    html += '<div class="flex items-center gap-3">';
    html += '<input type="checkbox" id="' + prefix + '-monitored" ' + monitoredChecked + ' class="w-4 h-4 rounded border-gray-500 bg-gray-700 text-blue-500 focus:ring-blue-500">';
    html += '<label for="' + prefix + '-monitored" class="text-sm text-gray-300">Monitor items</label>';
    html += '</div>';

    // Search on add checkbox
    var searchChecked = (defaults.search_on_add !== false) ? ' checked' : '';
    html += '<div class="flex items-center gap-3">';
    html += '<input type="checkbox" id="' + prefix + '-search-on-add" ' + searchChecked + ' class="w-4 h-4 rounded border-gray-500 bg-gray-700 text-blue-500 focus:ring-blue-500">';
    html += '<label for="' + prefix + '-search-on-add" class="text-sm text-gray-300">Search on add</label>';
    html += '</div>';

    html += '</div>';

    container.innerHTML = html;
  })
  .catch(function (err) {
    container.innerHTML = '<div class="text-sm text-red-400">Failed to load import settings.</div>';
  });
}

// ---------------------
// Submit
// ---------------------

/**
 * Submit the list creation form via AJAX.
 * @param {string} panelName - 'preset' or 'custom'
 */
function submitList(panelName) {
  var errorEl = document.getElementById(panelName + '-submit-error');
  var submitBtn = document.getElementById(panelName + '-submit-btn');

  function showError(msg) {
    if (errorEl) {
      errorEl.textContent = msg;
      errorEl.classList.remove('hidden');
    }
  }

  function clearError() {
    if (errorEl) {
      errorEl.textContent = '';
      errorEl.classList.add('hidden');
    }
  }

  clearError();

  // Collect data based on panel
  var payload = {};

  if (panelName === 'preset') {
    var service = document.getElementById('preset-service');
    var nameInput = document.getElementById('preset-list-name');
    var isActiveInput = document.getElementById('preset-is-active');
    var cronValue = document.getElementById('preset-cron-value');
    var limitInput = document.getElementById('preset-limit');
    var yearMinInput = document.getElementById('preset-year-min');
    var yearMaxInput = document.getElementById('preset-year-max');
    var prefix = 'preset-import';

    if (!selectedPreset) {
      showError('Please select a template first.');
      return;
    }

    var name = nameInput ? nameInput.value.trim() : '';
    if (!name) {
      showError('Please enter a list name.');
      return;
    }

    var qualityEl = document.getElementById(prefix + '-quality');
    var folderEl = document.getElementById(prefix + '-folder');
    var tagEl = document.getElementById(prefix + '-tag');
    var monitoredEl = document.getElementById(prefix + '-monitored');
    var searchEl = document.getElementById(prefix + '-search-on-add');

    payload = {
      list_id: null,
      name: name,
      service: service ? service.value : 'radarr',
      preset: selectedPreset,
      filters: {
        limit: limitInput && limitInput.value ? parseInt(limitInput.value, 10) : 20,
        year_min: yearMinInput && yearMinInput.value ? parseInt(yearMinInput.value, 10) : null,
        year_max: yearMaxInput && yearMaxInput.value ? parseInt(yearMaxInput.value, 10) : null
      },
      import_settings: {
        quality_profile_id: qualityEl ? parseInt(qualityEl.value, 10) || null : null,
        root_folder: folderEl ? folderEl.value : '',
        tag: tagEl && tagEl.value.trim() ? tagEl.value.trim() : null,
        monitored: monitoredEl ? monitoredEl.checked : true,
        search_on_add: searchEl ? searchEl.checked : true
      },
      schedule: {
        cron: cronValue ? cronValue.value : '',
        is_active: isActiveInput ? isActiveInput.checked : true
      }
    };

  } else {
    // Custom panel
    var customService = document.getElementById('custom-service');
    var customName = document.getElementById('custom-list-name');
    var customIsActive = document.getElementById('custom-is-active');
    var customCronValue = document.getElementById('custom-cron-value');
    var customPrefix = 'custom-import';

    var serviceVal = customService ? customService.value : 'radarr';
    var customNameVal = customName ? customName.value.trim() : '';

    if (!customNameVal) {
      showError('Please enter a list name.');
      return;
    }

    var cqEl = document.getElementById(customPrefix + '-quality');
    var cfEl = document.getElementById(customPrefix + '-folder');
    var ctEl = document.getElementById(customPrefix + '-tag');
    var cmEl = document.getElementById(customPrefix + '-monitored');
    var csEl = document.getElementById(customPrefix + '-search-on-add');

    payload = {
      list_id: null,
      name: customNameVal,
      service: serviceVal,
      preset: null,
      filters: collectFilters(),
      import_settings: {
        quality_profile_id: cqEl ? parseInt(cqEl.value, 10) || null : null,
        root_folder: cfEl ? cfEl.value : '',
        tag: ctEl && ctEl.value.trim() ? ctEl.value.trim() : null,
        monitored: cmEl ? cmEl.checked : true,
        search_on_add: csEl ? csEl.checked : true
      },
      schedule: {
        cron: customCronValue ? customCronValue.value : '',
        is_active: customIsActive ? customIsActive.checked : true
      }
    };
  }

  // Disable button during submit
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating...';
  }

  fetch('/lists/wizard/submit', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(payload)
  })
  .then(function (response) { return response.json(); })
  .then(function (data) {
    if (data.success) {
      window.location.href = '/lists';
    } else {
      showError(data.error || 'Failed to create list. Please try again.');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create List';
      }
    }
  })
  .catch(function (err) {
    showError('Network error. Please try again.');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Create List';
    }
  });
}

// ---------------------
// Genre Pill Toggles
// ---------------------

/**
 * Initialize pill/chip genre buttons with three-state cycle: neutral -> include -> exclude -> neutral.
 * Neutral: gray border, no icon.
 * Include: green border + checkmark icon.
 * Exclude: red border + X icon.
 */
function initGenreToggles() {
  var pills = document.querySelectorAll('.genre-pill');
  for (var i = 0; i < pills.length; i++) {
    pills[i].addEventListener('click', (function (pill) {
      return function () {
        var state = pill.getAttribute('data-state') || 'neutral';
        var icon = pill.querySelector('.genre-pill-icon');
        var path = icon ? icon.querySelector('path') : null;

        if (state === 'neutral') {
          // neutral -> include (green + checkmark)
          pill.classList.remove('border-gray-600', 'text-gray-300', 'bg-transparent');
          pill.classList.add('border-green-500', 'text-green-300', 'bg-green-900/20');
          if (icon) { icon.classList.remove('hidden'); }
          if (path) { path.setAttribute('d', 'M5 13l4 4L19 7'); }
          pill.setAttribute('data-state', 'include');

        } else if (state === 'include') {
          // include -> exclude (red + X)
          pill.classList.remove('border-green-500', 'text-green-300', 'bg-green-900/20');
          pill.classList.add('border-red-500', 'text-red-300', 'bg-red-900/20');
          if (icon) { icon.classList.remove('hidden'); }
          if (path) { path.setAttribute('d', 'M6 18L18 6M6 6l12 12'); }
          pill.setAttribute('data-state', 'exclude');

        } else {
          // exclude -> neutral (gray, no icon)
          pill.classList.remove('border-red-500', 'text-red-300', 'bg-red-900/20');
          pill.classList.add('border-gray-600', 'text-gray-300', 'bg-transparent');
          if (icon) { icon.classList.add('hidden'); }
          if (path) { path.setAttribute('d', ''); }
          pill.setAttribute('data-state', 'neutral');
        }

        schedulePreview('custom');
      };
    })(pills[i]));
  }
}

// ---------------------
// Filter change listeners
// ---------------------

/**
 * Attach change listeners to all custom filter inputs to trigger debounced preview.
 */
function initFilterListeners() {
  var filterInputIds = [
    'custom-language', 'custom-year-min', 'custom-year-max',
    'custom-rating-min', 'custom-limit'
  ];

  for (var i = 0; i < filterInputIds.length; i++) {
    var el = document.getElementById(filterInputIds[i]);
    if (el) {
      el.addEventListener('change', function () { schedulePreview('custom'); });
      el.addEventListener('input', function () { schedulePreview('custom'); });
    }
  }

  // Genre toggle buttons — preview on click (listeners attached after initGenreToggles runs)
}

/**
 * Prevent auto-populated name field from being overwritten after user edits.
 */
function initNameFieldTracking() {
  var presetName = document.getElementById('preset-list-name');
  if (presetName) {
    presetName.addEventListener('input', function () {
      presetName.dataset.userEdited = 'true';
    });
  }
}

// ---------------------
// DOMContentLoaded
// ---------------------

document.addEventListener('DOMContentLoaded', function () {
  initTabs();
  initAccordion();
  initGenreToggles();
  initPresetCards();
  initServiceSelector();
  initCronPicker();
  initFilterListeners();
  initNameFieldTracking();

  // Load import defaults for custom panel (radarr is default)
  loadImportDefaults('radarr', 'custom');

  // Submit button listeners
  var presetSubmitBtn = document.getElementById('preset-submit-btn');
  if (presetSubmitBtn) {
    presetSubmitBtn.addEventListener('click', function () {
      submitList('preset');
    });
  }

  var customSubmitBtn = document.getElementById('custom-submit-btn');
  if (customSubmitBtn) {
    customSubmitBtn.addEventListener('click', function () {
      submitList('custom');
    });
  }

  // Initial badge state
  updateStepBadges('preset');
  updateStepBadges('custom');
});
