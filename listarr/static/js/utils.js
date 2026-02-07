/**
 * Shared JavaScript utility functions for Listarr.
 */

/**
 * Format ISO timestamp for display.
 */
function formatTimestamp(isoTimestamp) {
  const date = new Date(isoTimestamp);
  return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

/**
 * Generate status HTML with icon and timestamp.
 */
function generateStatusHTML(success, timestamp) {
  const statusIcon = success ? "\u2713" : "\u2717";
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
