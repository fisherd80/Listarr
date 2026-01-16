/**
 * List Creation Wizard - Step Navigation
 *
 * Handles multi-step wizard navigation, stepper UI updates,
 * and state management for the list creation flow.
 */

// Wizard state management
const wizardState = {
    currentStep: 1,
    totalSteps: 4,
    preset: null,      // from URL or null for custom
    service: null,     // radarr or sonarr
    isPreset: false,   // true if using a preset template
    listId: null,      // for edit mode (future use)
    // Form data will be added in later plans
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

    // Initialize UI to step 1
    goToStep(1);
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
    // Placeholder - actual validation will be added in later plans
    // For now, always allow navigation
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
