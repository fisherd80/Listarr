/**
 * List Creation Wizard - Step Navigation
 *
 * Handles multi-step wizard navigation, stepper UI updates,
 * and state management for the list creation flow.
 */

// TMDB Genre IDs (same for movies and TV)
const TMDB_GENRES = {
    28: "Action",
    35: "Comedy",
    18: "Drama",
    27: "Horror",
    878: "Sci-Fi",
    53: "Thriller",
};

// Preview debounce timer
let previewDebounceTimer = null;
const PREVIEW_DEBOUNCE_MS = 300;

// Wizard state management
const wizardState = {
    currentStep: 1,
    totalSteps: 4,
    preset: null,      // from URL or null for custom
    service: null,     // radarr or sonarr
    isPreset: false,   // true if using a preset template
    listId: null,      // for edit mode (future use)
    filters: {
        genre_ids: [],
        year_min: null,
        year_max: null,
        rating_min: null,
        limit: 20,
    },
    importSettings: {
        quality_profile_id: null,  // null = use default
        root_folder: null,
        tag_id: null,
        monitored: null,           // null = use default
        search_on_add: null,
    },
    // Cached data from defaults endpoint
    _importDefaults: null,
    _importOptions: null,
};

/**
 * Initialize wizard from URL parameters and hidden fields
 */
function initWizard() {
    // Read initial values from hidden fields (populated by server)
    const presetField = document.getElementById("wizard-preset");
    const serviceField = document.getElementById("wizard-service");
    const isPresetField = document.getElementById("wizard-is-preset");
    const listIdField = document.getElementById("wizard-list-id");

    if (presetField && presetField.value) {
        wizardState.preset = presetField.value;
    }
    if (serviceField && serviceField.value) {
        wizardState.service = serviceField.value;
    }
    if (isPresetField) {
        wizardState.isPreset = isPresetField.value === "true";
    }
    if (listIdField && listIdField.value) {
        wizardState.listId = parseInt(listIdField.value, 10);
    }

    // Set up event listeners
    const btnNext = document.getElementById("btn-next");
    const btnBack = document.getElementById("btn-back");

    if (btnNext) {
        btnNext.addEventListener("click", nextStep);
    }
    if (btnBack) {
        btnBack.addEventListener("click", prevStep);
    }

    // Set up type card click handlers (for custom lists)
    initTypeCards();

    // Set up filter change handlers (for custom lists)
    initFilters();

    // Set up import settings change handlers
    initImportSettings();

    // Initialize UI to step 1
    goToStep(1);

    // Update Next button state based on initial validation
    updateNextButtonState();
}

/**
 * Initialize type selection card click handlers
 */
function initTypeCards() {
    const typeCards = document.querySelectorAll(".type-card");

    typeCards.forEach(card => {
        card.addEventListener("click", () => {
            const service = card.dataset.service;
            selectType(service);
        });
    });
}

/**
 * Handle type card selection
 * @param {string} service - The service to select (radarr or sonarr)
 */
function selectType(service) {
    wizardState.service = service;

    // Update hidden field
    const serviceField = document.getElementById("wizard-service");
    if (serviceField) {
        serviceField.value = service;
    }

    // Update card styling
    const typeCards = document.querySelectorAll(".type-card");
    typeCards.forEach(card => {
        if (card.dataset.service === service) {
            // Selected state
            card.classList.remove("border-gray-200", "dark:border-gray-600");
            card.classList.add("border-primary", "bg-primary/5", "dark:bg-primary/10");
        } else {
            // Unselected state
            card.classList.remove("border-primary", "bg-primary/5", "dark:bg-primary/10");
            card.classList.add("border-gray-200", "dark:border-gray-600");
        }
    });

    // Hide selection hint
    const hint = document.getElementById("type-selection-hint");
    if (hint) {
        hint.classList.add("hidden");
    }

    // Update Next button state
    updateNextButtonState();
}

/**
 * Initialize filter input change handlers
 */
function initFilters() {
    // Genre checkboxes
    const genreCheckboxes = document.querySelectorAll(".genre-checkbox");
    genreCheckboxes.forEach(checkbox => {
        checkbox.addEventListener("change", handleGenreChange);
    });

    // Year inputs
    const yearMinInput = document.getElementById("filter-year-min");
    const yearMaxInput = document.getElementById("filter-year-max");
    if (yearMinInput) {
        yearMinInput.addEventListener("input", handleYearChange);
    }
    if (yearMaxInput) {
        yearMaxInput.addEventListener("input", handleYearChange);
    }

    // Rating slider
    const ratingInput = document.getElementById("filter-rating-min");
    if (ratingInput) {
        ratingInput.addEventListener("input", handleRatingChange);
    }

    // Limit select
    const limitSelect = document.getElementById("filter-limit");
    if (limitSelect) {
        limitSelect.addEventListener("change", handleLimitChange);
    }
}

/**
 * Handle genre checkbox change
 */
function handleGenreChange() {
    const checkboxes = document.querySelectorAll(".genre-checkbox:checked");
    wizardState.filters.genre_ids = Array.from(checkboxes).map(cb => parseInt(cb.dataset.genreId, 10));
    onFiltersChanged();
}

/**
 * Handle year input change
 */
function handleYearChange() {
    const yearMinInput = document.getElementById("filter-year-min");
    const yearMaxInput = document.getElementById("filter-year-max");

    wizardState.filters.year_min = yearMinInput && yearMinInput.value ? parseInt(yearMinInput.value, 10) : null;
    wizardState.filters.year_max = yearMaxInput && yearMaxInput.value ? parseInt(yearMaxInput.value, 10) : null;
    onFiltersChanged();
}

/**
 * Handle rating slider change
 */
function handleRatingChange() {
    const ratingInput = document.getElementById("filter-rating-min");
    const ratingValue = document.getElementById("rating-value");

    if (ratingInput) {
        const value = parseFloat(ratingInput.value);
        wizardState.filters.rating_min = value > 0 ? value : null;

        // Update display value
        if (ratingValue) {
            ratingValue.textContent = value > 0 ? value.toFixed(1) : "Any";
        }
    }
    onFiltersChanged();
}

/**
 * Handle limit select change
 */
function handleLimitChange() {
    const limitSelect = document.getElementById("filter-limit");
    if (limitSelect) {
        wizardState.filters.limit = parseInt(limitSelect.value, 10);
    }
    onFiltersChanged();
}

/**
 * Called when any filter value changes - triggers debounced preview update
 */
function onFiltersChanged() {
    // Clear existing timer
    if (previewDebounceTimer) {
        clearTimeout(previewDebounceTimer);
    }

    // Set new debounced timer
    previewDebounceTimer = setTimeout(() => {
        fetchPreview();
    }, PREVIEW_DEBOUNCE_MS);
}

/**
 * Fetch TMDB preview results based on current filters
 */
async function fetchPreview() {
    // Only fetch preview if on step 2 and service is selected
    if (wizardState.currentStep !== 2 || !wizardState.service) {
        return;
    }

    const loadingEl = document.getElementById("preview-loading");
    const emptyEl = document.getElementById("preview-empty");
    const errorEl = document.getElementById("preview-error");
    const resultsEl = document.getElementById("preview-results");

    // If elements don't exist (preset mode), skip
    if (!loadingEl || !resultsEl) {
        return;
    }

    // Show loading state
    loadingEl.classList.remove("hidden");
    emptyEl.classList.add("hidden");
    errorEl.classList.add("hidden");
    resultsEl.classList.add("hidden");

    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    try {
        const response = await fetch("/lists/wizard/preview", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({
                service: wizardState.service,
                preset: wizardState.preset,
                filters: wizardState.filters,
            }),
        });

        const data = await response.json();

        // Hide loading
        loadingEl.classList.add("hidden");

        if (data.error) {
            // Show error
            const errorMsgEl = document.getElementById("preview-error-message");
            if (errorMsgEl) {
                errorMsgEl.textContent = data.error;
            }
            errorEl.classList.remove("hidden");
            return;
        }

        if (!data.items || data.items.length === 0) {
            // Show empty state
            emptyEl.classList.remove("hidden");
            return;
        }

        // Render preview items
        renderPreviewItems(data.items);
        resultsEl.classList.remove("hidden");

    } catch (error) {
        console.error("Preview fetch error:", error);
        loadingEl.classList.add("hidden");
        const errorMsgEl = document.getElementById("preview-error-message");
        if (errorMsgEl) {
            errorMsgEl.textContent = "Network error - please try again";
        }
        errorEl.classList.remove("hidden");
    }
}

/**
 * Render preview items in the preview container
 * @param {Array} items - Array of preview items with id, title, year, rating
 */
function renderPreviewItems(items) {
    const resultsEl = document.getElementById("preview-results");
    if (!resultsEl) return;

    resultsEl.innerHTML = items.map(item => `
        <div class="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">${escapeHtml(item.title)}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                    ${item.year ? item.year : "Unknown year"}
                </p>
            </div>
            ${item.rating ? `
            <div class="ml-3 flex items-center">
                <svg class="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                <span class="ml-1 text-sm font-medium text-gray-700 dark:text-gray-300">${item.rating}</span>
            </div>
            ` : ""}
        </div>
    `).join("");
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Update Next button enabled/disabled state based on current step validation
 */
function updateNextButtonState() {
    const btnNext = document.getElementById("btn-next");
    if (!btnNext) return;

    const isValid = validateCurrentStep();

    if (isValid) {
        btnNext.disabled = false;
        btnNext.classList.remove("opacity-50", "cursor-not-allowed");
    } else {
        btnNext.disabled = true;
        btnNext.classList.add("opacity-50", "cursor-not-allowed");
    }
}

/**
 * Navigate to a specific step
 * @param {number} stepNumber - The step to navigate to (1-4)
 */
function goToStep(stepNumber) {
    // Validate step number
    if (stepNumber < 1 || stepNumber > wizardState.totalSteps) {
        return;
    }

    // Hide all step content
    const stepContents = document.querySelectorAll(".step-content");
    stepContents.forEach(content => {
        content.classList.add("hidden");
    });

    // Show the target step
    const targetStep = document.getElementById(`step-${stepNumber}`);
    if (targetStep) {
        targetStep.classList.remove("hidden");
    }

    // Update current step in state
    wizardState.currentStep = stepNumber;

    // Update stepper UI
    updateStepperUI();

    // Update navigation buttons
    updateNavButtons();

    // Update Next button state based on validation
    updateNextButtonState();

    // Trigger preview fetch when entering step 2 (for both preset and custom lists)
    if (stepNumber === 2 && wizardState.service) {
        fetchPreview();
    }

    // Trigger import defaults fetch when entering step 3
    if (stepNumber === 3 && wizardState.service) {
        fetchImportDefaults();
    }
}

/**
 * Advance to the next step
 */
function nextStep() {
    // Validate current step (placeholder - always true for now)
    const isValid = validateCurrentStep();

    if (!isValid) {
        return;
    }

    if (wizardState.currentStep < wizardState.totalSteps) {
        goToStep(wizardState.currentStep + 1);
    } else {
        // On step 4, "Next" becomes "Create List" - submit the form
        submitWizard();
    }
}

/**
 * Go back to the previous step
 */
function prevStep() {
    if (wizardState.currentStep > 1) {
        goToStep(wizardState.currentStep - 1);
    }
}

/**
 * Validate the current step before proceeding
 * @returns {boolean} - true if validation passes
 */
function validateCurrentStep() {
    switch (wizardState.currentStep) {
        case 1:
            return validateStep1();
        case 2:
            return validateStep2();
        case 3:
            return validateStep3();
        case 4:
            // Schedule validation will be added in 02-05
            return true;
        default:
            return true;
    }
}

/**
 * Validate Step 1 - Type Selection
 * For presets: Always valid (service is pre-set)
 * For custom: Service must be selected
 * @returns {boolean}
 */
function validateStep1() {
    // Presets have service pre-set, always valid
    if (wizardState.isPreset) {
        return true;
    }
    // Custom lists require service selection
    return wizardState.service !== null && wizardState.service !== "";
}

/**
 * Validate Step 2 - Filters
 * For presets: Always valid (filters are pre-configured)
 * For custom: Allow empty filters (will fetch all), always valid
 * @returns {boolean}
 */
function validateStep2() {
    // Both preset and custom are always valid for step 2
    // Presets have read-only filters, custom allows empty filters
    return true;
}

/**
 * Update the stepper UI to reflect current/completed/future states
 */
function updateStepperUI() {
    for (let i = 1; i <= wizardState.totalSteps; i++) {
        const indicator = document.getElementById(`step-indicator-${i}`);
        const label = document.getElementById(`step-label-${i}`);
        const connector = document.getElementById(`connector-${i}`);

        if (!indicator || !label) continue;

        if (i < wizardState.currentStep) {
            // Completed step - filled with checkmark
            indicator.className = "flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white text-sm font-medium";
            indicator.innerHTML = `<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>`;
            label.className = "ml-2 text-sm font-medium text-primary";

            // Connector after completed step is filled
            if (connector) {
                connector.className = "flex-1 h-0.5 mx-4 bg-primary";
            }
        } else if (i === wizardState.currentStep) {
            // Current step - filled primary color
            indicator.className = "flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white text-sm font-medium";
            indicator.textContent = i;
            label.className = "ml-2 text-sm font-medium text-gray-900 dark:text-gray-100";

            // Connector after current step is gray
            if (connector) {
                connector.className = "flex-1 h-0.5 mx-4 bg-gray-300 dark:bg-gray-600";
            }
        } else {
            // Future step - gray outline
            indicator.className = "flex items-center justify-center w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 text-gray-600 dark:text-gray-400 text-sm font-medium";
            indicator.textContent = i;
            label.className = "ml-2 text-sm font-medium text-gray-500 dark:text-gray-400";

            // Connector after future step is gray
            if (connector) {
                connector.className = "flex-1 h-0.5 mx-4 bg-gray-300 dark:bg-gray-600";
            }
        }
    }

    // Update step counter text
    const stepCounter = document.getElementById("current-step-number");
    if (stepCounter) {
        stepCounter.textContent = wizardState.currentStep;
    }
}

/**
 * Update navigation buttons based on current step
 */
function updateNavButtons() {
    const btnBack = document.getElementById("btn-back");
    const btnNext = document.getElementById("btn-next");

    // Show/hide Back button
    if (btnBack) {
        if (wizardState.currentStep === 1) {
            btnBack.classList.add("hidden");
        } else {
            btnBack.classList.remove("hidden");
        }
    }

    // Change Next button text on final step
    if (btnNext) {
        if (wizardState.currentStep === wizardState.totalSteps) {
            btnNext.textContent = "Create List";
        } else {
            btnNext.textContent = "Next";
        }
    }
}

// ============================================
// Step 3: Import Settings Functions
// ============================================

/**
 * Initialize import settings change handlers
 */
function initImportSettings() {
    // Quality Profile
    const qualitySelect = document.getElementById("import-quality-profile");
    if (qualitySelect) {
        qualitySelect.addEventListener("change", handleQualityProfileChange);
    }

    // Root Folder
    const rootFolderSelect = document.getElementById("import-root-folder");
    if (rootFolderSelect) {
        rootFolderSelect.addEventListener("change", handleRootFolderChange);
    }

    // Tag
    const tagSelect = document.getElementById("import-tag");
    if (tagSelect) {
        tagSelect.addEventListener("change", handleTagChange);
    }

    // Monitored
    const monitoredCheckbox = document.getElementById("import-monitored");
    if (monitoredCheckbox) {
        monitoredCheckbox.addEventListener("change", handleMonitoredChange);
    }

    // Search on Add
    const searchOnAddCheckbox = document.getElementById("import-search-on-add");
    if (searchOnAddCheckbox) {
        searchOnAddCheckbox.addEventListener("change", handleSearchOnAddChange);
    }
}

/**
 * Fetch import defaults and options from the server
 */
async function fetchImportDefaults() {
    // If already cached for this service, use cached data
    if (wizardState._importDefaults && wizardState._importOptions) {
        populateImportSettings(wizardState._importDefaults, wizardState._importOptions);
        return;
    }

    const loadingEl = document.getElementById("import-settings-loading");
    const errorEl = document.getElementById("import-settings-error");
    const formEl = document.getElementById("import-settings-form");

    // Show loading state
    if (loadingEl) loadingEl.classList.remove("hidden");
    if (errorEl) errorEl.classList.add("hidden");
    if (formEl) formEl.classList.add("hidden");

    // Update service badge
    updateImportSettingsServiceBadge();

    try {
        const response = await fetch(`/lists/wizard/defaults/${wizardState.service}`);
        const data = await response.json();

        // Hide loading
        if (loadingEl) loadingEl.classList.add("hidden");

        if (!data.configured) {
            // Show error - service not configured
            const errorMsgEl = document.getElementById("import-settings-error-message");
            if (errorMsgEl) {
                errorMsgEl.textContent = data.error || `${wizardState.service.charAt(0).toUpperCase() + wizardState.service.slice(1)} not configured`;
            }
            if (errorEl) errorEl.classList.remove("hidden");
            return;
        }

        if (data.error) {
            // Partial error - service configured but API fetch failed
            const errorMsgEl = document.getElementById("import-settings-error-message");
            if (errorMsgEl) {
                errorMsgEl.textContent = data.error;
            }
            if (errorEl) errorEl.classList.remove("hidden");
            // Still show the form with whatever data we have
        }

        // Cache the data
        wizardState._importDefaults = data.defaults;
        wizardState._importOptions = data.options;

        // Populate the form
        populateImportSettings(data.defaults, data.options);
        if (formEl) formEl.classList.remove("hidden");

    } catch (error) {
        console.error("Import defaults fetch error:", error);
        if (loadingEl) loadingEl.classList.add("hidden");
        const errorMsgEl = document.getElementById("import-settings-error-message");
        if (errorMsgEl) {
            errorMsgEl.textContent = "Network error - please try again";
        }
        if (errorEl) errorEl.classList.remove("hidden");
    }
}

/**
 * Update the service badge in Step 3
 */
function updateImportSettingsServiceBadge() {
    const badge = document.getElementById("import-settings-service-badge");
    if (!badge || !wizardState.service) return;

    if (wizardState.service === "radarr") {
        badge.className = "inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200";
        badge.innerHTML = `
            <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
            Radarr
        `;
    } else {
        badge.className = "inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
        badge.innerHTML = `
            <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Sonarr
        `;
    }
}

/**
 * Populate import settings form with defaults and options
 * @param {Object} defaults - Default values from MediaImportSettings
 * @param {Object} options - Available options (profiles, folders, tags)
 */
function populateImportSettings(defaults, options) {
    // Quality Profile dropdown
    const qualitySelect = document.getElementById("import-quality-profile");
    if (qualitySelect && options.quality_profiles) {
        // Clear existing options (except "Use Default")
        qualitySelect.innerHTML = '<option value="">Use Default</option>';

        // Add options
        options.quality_profiles.forEach(profile => {
            const option = document.createElement("option");
            option.value = profile.id;
            option.textContent = profile.name;
            qualitySelect.appendChild(option);
        });

        // Show default value
        const defaultDisplay = document.getElementById("import-quality-profile-default");
        if (defaultDisplay && defaults.quality_profile_id) {
            const defaultProfile = options.quality_profiles.find(p => p.id === defaults.quality_profile_id);
            if (defaultProfile) {
                defaultDisplay.textContent = `Default: ${defaultProfile.name}`;
            }
        }
    }

    // Root Folder dropdown
    const rootFolderSelect = document.getElementById("import-root-folder");
    if (rootFolderSelect && options.root_folders) {
        // Clear existing options (except "Use Default")
        rootFolderSelect.innerHTML = '<option value="">Use Default</option>';

        // Add options
        options.root_folders.forEach(folder => {
            const option = document.createElement("option");
            option.value = folder.path;
            option.textContent = folder.path;
            rootFolderSelect.appendChild(option);
        });

        // Show default value
        const defaultDisplay = document.getElementById("import-root-folder-default");
        if (defaultDisplay && defaults.root_folder) {
            defaultDisplay.textContent = `Default: ${defaults.root_folder}`;
        }
    }

    // Tag dropdown
    const tagSelect = document.getElementById("import-tag");
    if (tagSelect && options.tags) {
        // Clear existing options (except "None")
        tagSelect.innerHTML = '<option value="">None</option>';

        // Add options
        options.tags.forEach(tag => {
            const option = document.createElement("option");
            option.value = tag.id;
            option.textContent = tag.label;
            tagSelect.appendChild(option);
        });

        // Show default value
        const defaultDisplay = document.getElementById("import-tag-default");
        if (defaultDisplay && defaults.tag_id) {
            const defaultTag = options.tags.find(t => t.id === defaults.tag_id);
            if (defaultTag) {
                defaultDisplay.textContent = `Default: ${defaultTag.label}`;
            }
        }
    }

    // Monitored checkbox
    const monitoredCheckbox = document.getElementById("import-monitored");
    if (monitoredCheckbox) {
        // Pre-check based on defaults (or true if no defaults)
        monitoredCheckbox.checked = defaults.monitored !== false;
    }

    // Search on Add checkbox
    const searchOnAddCheckbox = document.getElementById("import-search-on-add");
    if (searchOnAddCheckbox) {
        // Pre-check based on defaults (or true if no defaults)
        searchOnAddCheckbox.checked = defaults.search_on_add !== false;
    }
}

/**
 * Handle Quality Profile selection change
 */
function handleQualityProfileChange() {
    const select = document.getElementById("import-quality-profile");
    if (!select) return;

    const value = select.value;
    const defaults = wizardState._importDefaults;

    // If value is empty or matches default, store null (use default)
    if (!value || (defaults && parseInt(value) === defaults.quality_profile_id)) {
        wizardState.importSettings.quality_profile_id = null;
    } else {
        wizardState.importSettings.quality_profile_id = parseInt(value);
    }
}

/**
 * Handle Root Folder selection change
 */
function handleRootFolderChange() {
    const select = document.getElementById("import-root-folder");
    if (!select) return;

    const value = select.value;
    const defaults = wizardState._importDefaults;

    // If value is empty or matches default, store null (use default)
    if (!value || (defaults && value === defaults.root_folder)) {
        wizardState.importSettings.root_folder = null;
    } else {
        wizardState.importSettings.root_folder = value;
    }
}

/**
 * Handle Tag selection change
 */
function handleTagChange() {
    const select = document.getElementById("import-tag");
    if (!select) return;

    const value = select.value;
    const defaults = wizardState._importDefaults;

    // If value is empty or matches default, store null (use default)
    if (!value || (defaults && parseInt(value) === defaults.tag_id)) {
        wizardState.importSettings.tag_id = null;
    } else {
        wizardState.importSettings.tag_id = parseInt(value);
    }
}

/**
 * Handle Monitored checkbox change
 */
function handleMonitoredChange() {
    const checkbox = document.getElementById("import-monitored");
    if (!checkbox) return;

    const value = checkbox.checked;
    const defaults = wizardState._importDefaults;
    const defaultValue = defaults ? defaults.monitored : true;

    // If value matches default, store null (use default)
    if (value === defaultValue) {
        wizardState.importSettings.monitored = null;
    } else {
        wizardState.importSettings.monitored = value;
    }
}

/**
 * Handle Search on Add checkbox change
 */
function handleSearchOnAddChange() {
    const checkbox = document.getElementById("import-search-on-add");
    if (!checkbox) return;

    const value = checkbox.checked;
    const defaults = wizardState._importDefaults;
    const defaultValue = defaults ? defaults.search_on_add : true;

    // If value matches default, store null (use default)
    if (value === defaultValue) {
        wizardState.importSettings.search_on_add = null;
    } else {
        wizardState.importSettings.search_on_add = value;
    }
}

/**
 * Validate Step 3 - Import Settings
 * All fields are optional - always valid
 * @returns {boolean}
 */
function validateStep3() {
    // All import settings are optional - validation always passes
    return true;
}

// ============================================
// Form Submission
// ============================================

/**
 * Submit the wizard form (placeholder for now)
 */
function submitWizard() {
    // Placeholder - actual form submission will be implemented in 02-05
    console.log("Wizard submitted with state:", wizardState);
    alert("List creation will be implemented in a future plan. Current state logged to console.");
}

// Initialize wizard when DOM is ready
document.addEventListener("DOMContentLoaded", initWizard);
