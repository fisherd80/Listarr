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
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        showToast(data.message, data.success ? "success" : "error");

        // Update last test status display using helper function
        lastTestDiv.innerHTML = generateStatusHTML(data.success, data.timestamp);

        // Re-enable button
        button.disabled = false;
        button.textContent = "Test Connection";
      })
      .catch((error) => {
        showToast("Error testing API key.", "error");
        console.error(error);

        // Re-enable button
        button.disabled = false;
        button.textContent = "Test Connection";
      });
  });
