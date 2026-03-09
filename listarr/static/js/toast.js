/**
 * Shared Toast Notification System
 * Provides consistent toast notifications across all pages
 */

/**
 * Toast notification configuration by type
 */
const TOAST_CONFIG = {
  success: {
    bgClass: "bg-success/10 border-success/30",
    iconClass: "text-success",
    textClass: "text-success",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />',
  },
  error: {
    bgClass: "bg-error/10 border-error/30",
    iconClass: "text-error",
    textClass: "text-error",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />',
  },
  warning: {
    bgClass: "bg-warning/10 border-warning/30",
    iconClass: "text-warning",
    textClass: "text-warning",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />',
  },
  info: {
    bgClass: "bg-primary/10 border-primary/30",
    iconClass: "text-primary",
    textClass: "text-primary",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />',
  },
};

/**
 * Get or create the toast container
 * @returns {HTMLElement} The toast container element
 */
function getToastContainer() {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "fixed top-4 right-4 z-50 flex flex-col gap-2";
    document.body.appendChild(container);
  }
  return container;
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Toast type: "success", "error", "warning", "info"
 * @param {number} duration - Duration in ms before auto-dismiss (default 3000)
 */
function showToast(message, type = "success", duration = 3000) {
  const config = TOAST_CONFIG[type] || TOAST_CONFIG.success;
  const container = getToastContainer();

  // Create toast element
  const toast = document.createElement("div");
  toast.className = `${config.bgClass} border rounded-lg p-4 flex items-center max-w-md transition-all duration-300`;
  toast.innerHTML = `
    <svg class="w-5 h-5 ${config.iconClass} mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      ${config.icon}
    </svg>
    <span class="text-sm font-medium ${config.textClass}">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  // Remove after duration
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
