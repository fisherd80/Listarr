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
    // Debounced preview will be implemented in Task 3
    // For now, just log the state
    console.log("Filters changed:", wizardState.filters);
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
            // Import settings validation will be added in 02-04
            return true;
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
