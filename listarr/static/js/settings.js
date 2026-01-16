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
      Last tested: <span id="tmdb-last-test-time" data-timestamp="${timestamp}">${formattedTime}</span>
    </span>
  `;
}

// ----------------------
// Toggle TMDB Key Visibility
// ----------------------
function toggleTMDBKey() {
  const input = document.getElementById("tmdb_api");
  input.type = input.type === "password" ? "text" : "password";
}

// ----------------------
// Test TMDB API Key
// ----------------------
document
  .getElementById("test-tmdb-button")
  .addEventListener("click", function () {
    const apiKey = document.getElementById("tmdb_api").value;
    const button = this;
    const lastTestDiv = document.getElementById("tmdb-last-test");

    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Disable button during test
    button.disabled = true;
    button.textContent = "Testing...";

    fetch("/settings/test_tmdb_api", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ api_key: apiKey }),
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
        alert("Error testing API key.");
        console.error(error);

        // Re-enable button
        button.disabled = false;
        button.textContent = "Test Connection";
      });
  });
