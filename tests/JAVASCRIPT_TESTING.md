# JavaScript Testing Guide for Listarr

This document provides guidance for testing JavaScript functionality in the Listarr application, specifically for the Settings page (`settings.js`).

## Overview

While the current test suite focuses on Python/Flask backend testing, the JavaScript layer also requires testing to ensure:
- CSRF token retrieval from meta tags
- AJAX request formatting and headers
- DOM manipulation (timestamp display, status updates)
- Error handling and user feedback
- API key visibility toggle

## JavaScript Files to Test

### `listarr/static/js/settings.js`

Functions to test:
1. **`formatTimestamp(isoTimestamp)`** - Timestamp formatting
2. **`generateStatusHTML(success, timestamp)`** - Status indicator generation
3. **`toggleTMDBKey()`** - API key visibility toggle
4. **`test-tmdb-button` click handler** - AJAX connection test

## Recommended Testing Framework

### Option 1: Jest (Recommended)

Jest is a popular JavaScript testing framework with good DOM mocking support.

**Setup:**

```bash
npm init -y
npm install --save-dev jest jest-environment-jsdom
```

**Configuration (`jest.config.js`):**

```javascript
module.exports = {
  testEnvironment: 'jsdom',
  testMatch: ['**/tests/js/**/*.test.js'],
  collectCoverageFrom: ['listarr/static/js/**/*.js'],
  coverageDirectory: 'coverage/js',
};
```

### Option 2: Mocha + Chai + jsdom

**Setup:**

```bash
npm install --save-dev mocha chai jsdom
```

### Option 3: QUnit (Lightweight)

For simpler testing without build tools.

## Example Test Cases

### Jest Test Example

**File: `tests/js/settings.test.js`**

```javascript
/**
 * @jest-environment jsdom
 */

// Mock the settings.js functions (adjust path as needed)
// For testing, you may need to refactor settings.js to export functions

describe('Settings JavaScript Tests', () => {

  describe('formatTimestamp', () => {
    test('formats ISO timestamp to readable format', () => {
      const formatTimestamp = (isoTimestamp) => {
        const date = new Date(isoTimestamp);
        return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
      };

      const result = formatTimestamp('2023-06-15T10:30:00Z');
      expect(result).toBe('2023-06-15 10:30 UTC');
    });

    test('handles different timezone formats', () => {
      const formatTimestamp = (isoTimestamp) => {
        const date = new Date(isoTimestamp);
        return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
      };

      const result = formatTimestamp('2023-06-15T10:30:00+00:00');
      expect(result).toBe('2023-06-15 10:30 UTC');
    });
  });

  describe('generateStatusHTML', () => {
    test('generates success HTML with green indicator', () => {
      const generateStatusHTML = (success, timestamp) => {
        const statusIcon = success ? "✓" : "✗";
        const statusClass = success
          ? "text-green-600 dark:text-green-400"
          : "text-red-600 dark:text-red-400";
        const formattedTime = timestamp; // Simplified for test

        return `
          <span class="inline-flex items-center gap-1">
            <span class="${statusClass}">${statusIcon}</span>
            Last tested: <span>${formattedTime}</span>
          </span>
        `;
      };

      const result = generateStatusHTML(true, '2023-06-15 10:30 UTC');

      expect(result).toContain('✓');
      expect(result).toContain('text-green-600');
      expect(result).toContain('Last tested:');
      expect(result).toContain('2023-06-15 10:30 UTC');
    });

    test('generates failure HTML with red indicator', () => {
      const generateStatusHTML = (success, timestamp) => {
        const statusIcon = success ? "✓" : "✗";
        const statusClass = success
          ? "text-green-600 dark:text-green-400"
          : "text-red-600 dark:text-red-400";
        const formattedTime = timestamp;

        return `
          <span class="inline-flex items-center gap-1">
            <span class="${statusClass}">${statusIcon}</span>
            Last tested: <span>${formattedTime}</span>
          </span>
        `;
      };

      const result = generateStatusHTML(false, '2023-06-15 10:30 UTC');

      expect(result).toContain('✗');
      expect(result).toContain('text-red-600');
    });
  });

  describe('toggleTMDBKey', () => {
    beforeEach(() => {
      // Setup DOM
      document.body.innerHTML = `
        <input id="tmdb_api" type="password" value="secret_key" />
      `;
    });

    test('toggles input type from password to text', () => {
      const input = document.getElementById("tmdb_api");
      expect(input.type).toBe('password');

      // Toggle
      input.type = input.type === "password" ? "text" : "password";

      expect(input.type).toBe('text');
    });

    test('toggles input type from text back to password', () => {
      const input = document.getElementById("tmdb_api");
      input.type = 'text';

      // Toggle
      input.type = input.type === "password" ? "text" : "password";

      expect(input.type).toBe('password');
    });
  });

  describe('Test TMDB API AJAX Request', () => {
    beforeEach(() => {
      // Setup DOM
      document.body.innerHTML = `
        <meta name="csrf-token" content="test-csrf-token" />
        <input id="tmdb_api" type="password" value="test_api_key" />
        <button id="test-tmdb-button">Test Connection</button>
        <div id="tmdb-last-test"></div>
      `;

      // Mock fetch
      global.fetch = jest.fn();
    });

    test('retrieves CSRF token from meta tag', () => {
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

      expect(csrfToken).toBe('test-csrf-token');
    });

    test('includes CSRF token in AJAX request headers', async () => {
      const apiKey = document.getElementById("tmdb_api").value;
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

      global.fetch.mockResolvedValueOnce({
        json: async () => ({ success: true, message: 'Valid', timestamp: '2023-06-15T10:30:00Z' })
      });

      await fetch("/settings/test_tmdb_api", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ api_key: apiKey }),
      });

      expect(global.fetch).toHaveBeenCalledWith(
        "/settings/test_tmdb_api",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "X-CSRFToken": "test-csrf-token",
          }),
        })
      );
    });

    test('sends API key in request body', async () => {
      const apiKey = "test_api_key";
      const csrfToken = "test-csrf-token";

      global.fetch.mockResolvedValueOnce({
        json: async () => ({ success: true })
      });

      await fetch("/settings/test_tmdb_api", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ api_key: apiKey }),
      });

      const callArgs = global.fetch.mock.calls[0];
      const requestBody = JSON.parse(callArgs[1].body);

      expect(requestBody.api_key).toBe('test_api_key');
    });

    test('updates DOM with success status', async () => {
      global.fetch.mockResolvedValueOnce({
        json: async () => ({
          success: true,
          message: 'Valid',
          timestamp: '2023-06-15T10:30:00Z'
        })
      });

      const button = document.getElementById("test-tmdb-button");
      const lastTestDiv = document.getElementById("tmdb-last-test");

      // Simulate click handler
      button.disabled = true;
      button.textContent = "Testing...";

      const response = await fetch("/settings/test_tmdb_api", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": "token" },
        body: JSON.stringify({ api_key: "test" }),
      });

      const data = await response.json();

      // Update DOM (simplified)
      lastTestDiv.innerHTML = `<span class="text-green-600">✓</span> Last tested: ${data.timestamp}`;
      button.disabled = false;
      button.textContent = "Test Connection";

      expect(lastTestDiv.innerHTML).toContain('✓');
      expect(lastTestDiv.innerHTML).toContain('text-green-600');
      expect(button.disabled).toBe(false);
      expect(button.textContent).toBe('Test Connection');
    });

    test('handles AJAX errors gracefully', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const button = document.getElementById("test-tmdb-button");

      button.disabled = true;
      button.textContent = "Testing...";

      try {
        await fetch("/settings/test_tmdb_api", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: "test" }),
        });
      } catch (error) {
        // Re-enable button
        button.disabled = false;
        button.textContent = "Test Connection";
      }

      expect(button.disabled).toBe(false);
      expect(button.textContent).toBe('Test Connection');
    });
  });
});
```

## Running JavaScript Tests

### With Jest

```bash
# Run all JS tests
npm test

# Run with coverage
npm test -- --coverage

# Watch mode (re-run on changes)
npm test -- --watch
```

### With Mocha

```bash
# Run tests
npx mocha tests/js/**/*.test.js

# With coverage (using nyc)
npx nyc mocha tests/js/**/*.test.js
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Install Node.js dependencies
  run: npm install

- name: Run JavaScript tests
  run: npm test

- name: Upload JS coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage/js/coverage-final.json
    flags: javascript
```

## Best Practices

1. **Mock External Dependencies**: Always mock `fetch()` calls
2. **Test DOM Manipulation**: Verify elements are updated correctly
3. **Test Error Paths**: Ensure errors don't crash the UI
4. **Test CSRF Token Handling**: Critical for security
5. **Test User Interactions**: Click events, input changes
6. **Keep Tests Fast**: Mock network calls, use minimal DOM setup
7. **Test Browser Compatibility**: Use polyfills for older browsers

## Refactoring for Testability

To make JavaScript more testable, consider refactoring `settings.js`:

**Before:**
```javascript
document.getElementById("test-tmdb-button").addEventListener("click", function () {
  // Inline logic
});
```

**After:**
```javascript
// Export for testing
function testTMDBConnection(apiKey, csrfToken) {
  return fetch("/settings/test_tmdb_api", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({ api_key: apiKey }),
  });
}

// Export functions for testing (if using modules)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    formatTimestamp,
    generateStatusHTML,
    toggleTMDBKey,
    testTMDBConnection,
  };
}

// Event listener setup
document.getElementById("test-tmdb-button").addEventListener("click", async function () {
  const apiKey = document.getElementById("tmdb_api").value;
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  try {
    const response = await testTMDBConnection(apiKey, csrfToken);
    const data = await response.json();
    // Handle response
  } catch (error) {
    console.error(error);
  }
});
```

## Future Enhancements

1. **Visual Regression Testing**: Use tools like Percy or Chromatic
2. **E2E Testing**: Use Playwright or Cypress for full browser tests
3. **Accessibility Testing**: Use jest-axe for a11y checks
4. **Performance Testing**: Monitor bundle size and load times

## Resources

- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Testing Library](https://testing-library.com/docs/)
- [Mocha Documentation](https://mochajs.org/)
- [Fetch API Mocking](https://www.npmjs.com/package/jest-fetch-mock)
- [jsdom Documentation](https://github.com/jsdom/jsdom)