# Phase 12: Security Hardening - Research

**Researched:** 2026-02-16
**Domain:** Flask web application security, Docker container hardening, input validation
**Confidence:** HIGH

## Summary

Phase 12 focuses on hardening the production security posture of Listarr by addressing Flask configuration security, Docker runtime security, input validation, exception handling, and frontend error handling. The research identifies concrete, actionable changes across five key areas.

The codebase already has strong foundations: Flask-WTF CSRF protection is active, API keys are encrypted with Fernet, passwords use scrypt hashing, open redirect prevention exists, and the Dockerfile already runs as a non-root user. However, several production security foot-guns remain: SECRET_KEY uses a weak default, session cookies lack secure flags, Docker bind mounts have permission issues with non-root users, broad `except Exception` clauses mask errors, and some AJAX calls don't validate HTTP status codes consistently.

Based on user decisions from the phase assumptions conversation, this research focuses on auto-generating SECRET_KEY to `instance/.secret_key` (mirroring the Fernet key pattern), Docker bind mount permission handling with entrypoint `chown`, Flask-native security headers (no reverse proxy assumption), and specific exception handling improvements. Rate limiting is explicitly out of scope.

**Primary recommendation:** Implement SECRET_KEY auto-generation first (blocks everything else), then Docker entrypoint fixes (enables testing), then Flask security headers and session flags, then input validation and exception handling improvements, and finally frontend error handling audit.

## Standard Stack

### Core Security Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask-WTF | 1.2.1 | CSRF protection, form validation | Official Flask extension, already in use |
| cryptography | 46.0.5 | Fernet encryption for API keys | Industry standard, already in use |
| werkzeug.security | (via Flask) | Password hashing (scrypt) | Built into Flask, already in use for Phase 11 |
| secrets | (stdlib) | Cryptographic random token generation | Python standard library, recommended by Flask docs |

### Optional Security Enhancements

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| flask-talisman | 1.1.0 | Security headers (CSP, X-Frame-Options, HSTS) | If comprehensive header management desired |

**Note on Flask-Talisman:** User decision specifies "no reverse proxy" so Flask must handle security headers directly. Talisman provides batteries-included header management, but manual `@after_request` hooks are also viable for this single-user app. Recommend manual approach for transparency and minimal dependencies.

### Installation

No new dependencies required. All security improvements use existing libraries or Python stdlib.

## Architecture Patterns

### Recommended Secret Management Structure

```
instance/
├── .fernet_key          # Encryption key (existing)
├── .secret_key          # Flask SECRET_KEY (NEW)
├── listarr.db           # Database
```

**Pattern:** Auto-generate secrets on first run, persist to instance folder, load from file or environment variable.

### Flask Security Configuration Pattern

**Current state** (`listarr/__init__.py`):
```python
app.config.from_mapping(
    SECRET_KEY=os.environ.get("LISTARR_SECRET_KEY", "dev_key_change_me"),  # WEAK DEFAULT
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'listarr.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
```

**Recommended production pattern:**
```python
# Source: https://flask.palletsprojects.com/en/stable/config/
# Source: https://blog.miguelgrinberg.com/post/cookie-security-for-flask-applications

def load_secret_key(instance_path):
    """Load or generate Flask SECRET_KEY using same pattern as Fernet key."""
    import secrets
    key_path = os.path.join(instance_path, ".secret_key")

    # 1. Check environment variable first
    env_key = os.environ.get("LISTARR_SECRET_KEY")
    if env_key and env_key != "dev_key_change_me":
        return env_key

    # 2. Check file
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            return f.read().strip()

    # 3. Generate new key (32 bytes = 256 bits recommended by Flask docs)
    new_key = secrets.token_hex(32)
    with open(key_path, "w") as f:
        f.write(new_key)
    return new_key

app.config.from_mapping(
    SECRET_KEY=load_secret_key(app.instance_path),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'listarr.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,

    # Session security (production-ready)
    SESSION_COOKIE_SECURE=not app.debug,      # HTTPS only in production
    SESSION_COOKIE_HTTPONLY=True,              # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',             # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),  # 24h session timeout

    # Remember-me cookie security (already partially configured)
    REMEMBER_COOKIE_SECURE=not app.debug,      # HTTPS only in production
    # REMEMBER_COOKIE_HTTPONLY=True already set (line 105)
    # REMEMBER_COOKIE_SAMESITE='Lax' already set (line 106)
)
```

### Security Headers Pattern

**Manual approach (recommended for single-user app):**
```python
# Source: https://flask.palletsprojects.com/en/stable/web-security/
# Source: https://github.com/GoogleCloudPlatform/flask-talisman

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'

    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # XSS protection (legacy browsers)
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Content Security Policy (strict for self-hosted app)
    # Note: Tailwind CSS uses style attributes, so 'unsafe-inline' needed
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "  # Tailwind requires inline styles
        "script-src 'self'; "
        "img-src 'self' data: https://image.tmdb.org; "  # TMDB poster images
        "font-src 'self'; "
        "frame-ancestors 'self'"
    )

    # HSTS (only if app is behind HTTPS)
    # WARNING: Don't enable in development or without HTTPS
    if not app.debug and request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response
```

**Alternative: Flask-Talisman approach:**
```python
from flask_talisman import Talisman

# Relaxed CSP for Tailwind and TMDB images
csp = {
    'default-src': "'self'",
    'style-src': ["'self'", "'unsafe-inline'"],  # Tailwind
    'script-src': "'self'",
    'img-src': ["'self'", 'data:', 'https://image.tmdb.org'],
    'font-src': "'self'",
}

Talisman(app,
    content_security_policy=csp,
    force_https=not app.debug,
    strict_transport_security=not app.debug
)
```

### Docker Security Pattern

**Current Dockerfile** (lines 34-49):
```dockerfile
# Creates non-root user but doesn't handle bind mount permissions
RUN useradd -m -u 1000 listarr && \
    mkdir -p /app /app/instance && \
    chown -R listarr:listarr /app

USER listarr
```

**Problem:** Bind mount `./instance:/app/instance` inherits host permissions, causing "permission denied" errors when listarr user tries to write to mounted volume.

**Recommended pattern with entrypoint:**
```dockerfile
# Source: https://oneuptime.com/blog/post/2026-01-25-docker-container-user-permissions/view
# Source: https://medium.com/@haroldfinch01/cant-change-ownership-of-folders-and-files-in-docker-containers-53455eaab8c8

# Create non-root user
RUN useradd -m -u 1000 listarr && \
    mkdir -p /app /app/instance && \
    chown -R listarr:listarr /app

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Don't set USER here - entrypoint handles it
EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn_config.py", "listarr:create_app()"]
```

**Entrypoint script** (`entrypoint.sh`):
```bash
#!/bin/bash
set -e

# Fix permissions for bind-mounted instance directory
# Only needed when running as root initially
if [ "$(id -u)" = "0" ]; then
    echo "Fixing permissions for /app/instance..."
    chown -R listarr:listarr /app/instance

    # Switch to non-root user and exec CMD
    echo "Switching to user listarr..."
    exec gosu listarr "$@"
else
    # Already running as non-root (e.g., Kubernetes with securityContext)
    exec "$@"
fi
```

**Note:** Requires `gosu` package (lightweight alternative to `sudo` for Docker):
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*
```

### Exception Handling Pattern

**Current anti-pattern** (found in 20+ locations):
```python
except Exception as e:
    db.session.rollback()
    current_app.logger.error(f"Error saving config: {e}", exc_info=True)
    flash("Failed to save. Please try again.", "error")
```

**Problem:** Catches everything including `KeyboardInterrupt`, `SystemExit`, makes debugging harder, violates PEP 760 future direction.

**Recommended specific exceptions pattern:**
```python
# Source: https://peps.python.org/pep-0760/
# Source: https://realpython.com/python-exceptions/

# Database operations
try:
    db.session.commit()
except (sqlalchemy.exc.IntegrityError, sqlalchemy.exc.OperationalError) as e:
    db.session.rollback()
    current_app.logger.error(f"Database error: {e}", exc_info=True)
    flash("Database error. Please try again.", "error")

# External API calls
try:
    response = http_session.get(url)
except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
    current_app.logger.error(f"API request failed: {e}", exc_info=True)
    return {"success": False, "message": "Service unavailable"}

# Decryption errors
try:
    api_key = decrypt_data(encrypted_key, instance_path)
except (ValueError, cryptography.fernet.InvalidToken) as e:
    current_app.logger.error(f"Decryption failed: {e}", exc_info=True)
    flash("Stored key corrupted. Please re-enter.", "warning")
```

**Exception categories for Listarr:**
- **Database errors:** `sqlalchemy.exc.IntegrityError`, `sqlalchemy.exc.OperationalError`, `sqlalchemy.exc.DatabaseError`
- **HTTP/API errors:** `requests.exceptions.RequestException` (parent), `requests.exceptions.Timeout`, `requests.exceptions.ConnectionError`
- **Crypto errors:** `cryptography.fernet.InvalidToken`, `ValueError` (from decrypt)
- **File I/O:** `OSError`, `FileNotFoundError`, `PermissionError`
- **JSON parsing:** `json.JSONDecodeError`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Security headers | Custom middleware with header dict | Flask `@after_request` hook or flask-talisman | CSP syntax is complex, easy to misconfigure, tested libraries handle edge cases |
| CSRF protection | Custom token generation/validation | Flask-WTF (already in use) | CSRF has subtle timing attacks, Flask-WTF handles double-submit cookies and header validation |
| Password hashing | SHA256 + manual salt | werkzeug.security (already in use) | Scrypt/bcrypt are designed to be slow (prevent brute force), plain SHA256 is too fast |
| Random token generation | `random.randint()` or `uuid4()` | `secrets` module | `random` is not cryptographically secure, predictable with seed, `secrets` uses OS entropy |
| Session management | Custom cookie signing | Flask sessions (already in use) | Session replay attacks, expiry edge cases, itsdangerous handles signing correctly |

**Key insight:** Security primitives (crypto, CSRF, sessions) have decades of research behind attack vectors. Using stdlib/established libraries means benefiting from security patches and expert review. Custom implementations miss edge cases (timing attacks, replay attacks, entropy exhaustion).

## Common Pitfalls

### Pitfall 1: Weak SECRET_KEY in Production

**What goes wrong:** Using default/weak SECRET_KEY allows attackers to forge session cookies, impersonate users, bypass authentication.

**Why it happens:** Developers copy example configs with placeholder secrets, forget to change before deployment.

**How to avoid:**
- Auto-generate on first run (same pattern as Fernet key)
- Block startup if key is weak default: `if SECRET_KEY == "dev_key_change_me": raise RuntimeError("Production requires secure SECRET_KEY")`
- Document in CLAUDE.md that instance/.secret_key is auto-generated

**Warning signs:** Login sessions randomly expire, multiple users see same session data (session collision).

### Pitfall 2: Missing SECURE Flag on Cookies

**What goes wrong:** Without `SESSION_COOKIE_SECURE=True`, cookies transmit over HTTP, enabling man-in-the-middle attacks to steal sessions.

**Why it happens:** Setting `SECURE=True` breaks local development (localhost is HTTP not HTTPS), developers disable and forget to re-enable.

**How to avoid:**
- Conditional flags: `SESSION_COOKIE_SECURE = not app.debug`
- Development uses `app.debug=True` automatically disabling secure flag
- Production uses `FLASK_DEBUG=false` enabling secure flag

**Warning signs:** Browser DevTools shows session cookies sent over HTTP, security scanners flag insecure cookies.

### Pitfall 3: Docker Bind Mount Permission Errors

**What goes wrong:** Non-root container user can't write to bind-mounted `./instance` directory, app crashes on startup when trying to create database or write keys.

**Why it happens:** Host directory has root/different UID ownership, bind mounts preserve host permissions, non-root user lacks write access.

**How to avoid:**
- Use entrypoint script that runs as root initially
- `chown -R listarr:listarr /app/instance` before dropping privileges
- Then `exec gosu listarr <cmd>` to run app as non-root
- Alternative: Document that users should `chown -R 1000:1000 ./instance` on host

**Warning signs:** "Permission denied" errors on startup, SQLite "unable to open database" errors, encryption key file not created.

### Pitfall 4: Broad Exception Clauses Masking Real Errors

**What goes wrong:** `except Exception` catches `KeyboardInterrupt`, `MemoryError`, system signals, making it impossible to cleanly shut down or debug.

**Why it happens:** Developers want to "catch everything" to prevent crashes, unaware of exception hierarchy.

**How to avoid:**
- Catch specific exceptions: `except (ValueError, TypeError)`
- If truly unknown errors expected, catch `Exception` but log with full traceback (`exc_info=True`)
- Never catch bare `except:` or `except BaseException`
- Use linters (ruff E722 rule) to enforce

**Warning signs:** App hangs on Ctrl+C, debugging breakpoints ignored, "unknown error" logs with no traceback.

### Pitfall 5: Missing HTTP Status Validation in Frontend

**What goes wrong:** AJAX calls succeed with HTTP 400/500 errors, treating error responses as valid data, leading to confusing UI states.

**Why it happens:** `fetch()` only rejects on network errors, not HTTP errors. Developers forget `if (!response.ok) throw` check.

**How to avoid:**
- Always check `response.ok` before parsing JSON
- Centralize pattern in utility function if repeated
- Example: `if (!response.ok) throw new Error(`HTTP ${response.status}`)`

**Warning signs:** "Unexpected token" JSON parse errors, blank UI states, toast shows "Operation successful" when server returned 500.

### Pitfall 6: Content Security Policy Breaking Tailwind CSS

**What goes wrong:** Strict CSP blocks inline styles, Tailwind CSS stops working, app loses all styling.

**Why it happens:** Tailwind uses utility classes that compile to style attributes, CSP `style-src 'self'` blocks inline styles.

**How to avoid:**
- CSP must include `style-src 'self' 'unsafe-inline'` for Tailwind
- Alternative: Use CSP nonces (complex, requires template changes)
- Test CSP changes in browser DevTools console for violations

**Warning signs:** Styled app suddenly unstyled, browser console shows "Refused to apply inline style" CSP errors.

### Pitfall 7: Input Validation on Wrong Layer

**What goes wrong:** Validating in JavaScript only (client-side) allows attackers to bypass with direct API calls. Validating in database only gives poor UX.

**Why it happens:** Unclear separation of concerns, trusting client input.

**How to avoid:**
- **Client-side:** Quick feedback, prevent unnecessary requests (convenience)
- **Server-side:** Security boundary, WTForms validators, never trust client (required)
- **Database:** Constraints for data integrity (defense in depth)
- Validate twice: client for UX, server for security

**Warning signs:** Malformed data in database despite form validation, users complain about slow error feedback.

## Code Examples

Verified patterns from official sources and current codebase:

### SECRET_KEY Auto-Generation

```python
# Source: https://docs.python.org/3/library/secrets.html
# Source: https://blog.miguelgrinberg.com/post/the-new-way-to-generate-secure-tokens-in-python

import os
import secrets

def load_or_generate_secret_key(instance_path):
    """
    Load Flask SECRET_KEY from file or environment, generate if missing.
    Mirrors crypto_utils.py pattern for consistency.
    """
    key_path = os.path.join(instance_path, ".secret_key")

    # 1. Check environment variable (allow override)
    env_key = os.environ.get("LISTARR_SECRET_KEY")
    if env_key and env_key != "dev_key_change_me":
        return env_key

    # 2. Load from file if exists
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            key = f.read().strip()
            if key and key != "dev_key_change_me":
                return key

    # 3. Generate new key (32 bytes = 64 hex chars)
    # Flask docs recommend at least 32 bytes for security
    new_key = secrets.token_hex(32)

    # Ensure instance directory exists
    os.makedirs(instance_path, exist_ok=True)

    # Write to file for persistence
    with open(key_path, "w") as f:
        f.write(new_key)

    print(f"[INFO] Generated new SECRET_KEY and saved to {key_path}")
    return new_key
```

### WTForms Validation Example

```python
# Source: https://wtforms.readthedocs.io/en/3.0.x/validators/
# Source: https://flask.palletsprojects.com/en/stable/patterns/wtforms/

from wtforms import StringField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, URL, Optional, Regexp

class ListForm(FlaskForm):
    name = StringField(
        'List Name',
        validators=[
            DataRequired(message="List name is required"),
            Length(min=1, max=100, message="Name must be 1-100 characters")
        ]
    )

    # URL validation with protocol requirement
    radarr_url = StringField(
        'Radarr URL',
        validators=[
            DataRequired(),
            URL(require_tld=False, message="Invalid URL format")  # allow localhost
        ]
    )

    # Optional integer with range
    limit = IntegerField(
        'Item Limit',
        validators=[
            Optional(),
            NumberRange(min=1, max=500, message="Limit must be 1-500")
        ]
    )

    # Enum validation with choices
    service = SelectField(
        'Target Service',
        choices=[('radarr', 'Radarr'), ('sonarr', 'Sonarr')],
        validators=[DataRequired()]
    )

    # Custom regex validation
    cron_expression = StringField(
        'Schedule',
        validators=[
            Optional(),
            Regexp(r'^(\*|[0-9,\-\*/]+)\s+(\*|[0-9,\-\*/]+)\s+(\*|[0-9,\-\*/]+)\s+(\*|[0-9,\-\*/]+)\s+(\*|[0-9,\-\*/]+)$',
                   message="Invalid cron expression")
        ]
    )
```

### Specific Exception Handling

```python
# Source: https://realpython.com/python-exceptions/
# Source: https://docs.sqlalchemy.org/en/20/core/exceptions.html

import requests
from sqlalchemy.exc import IntegrityError, OperationalError
from cryptography.fernet import InvalidToken

# Database operations
@bp.route("/config", methods=["POST"])
def save_config():
    try:
        service_config.base_url = form.url.data
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity constraint violated: {e}", exc_info=True)
        flash("Configuration already exists", "error")
    except OperationalError as e:
        db.session.rollback()
        current_app.logger.error(f"Database operation failed: {e}", exc_info=True)
        flash("Database error. Please try again.", "error")

# External API calls
def fetch_from_radarr(base_url, api_key):
    try:
        response = http_session.get(
            f"{base_url}/api/v3/system/status",
            headers={"X-Api-Key": api_key},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        current_app.logger.error("Radarr request timed out")
        return None
    except requests.exceptions.ConnectionError:
        current_app.logger.error("Cannot connect to Radarr")
        return None
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(f"Radarr returned error: {e.response.status_code}")
        return None
    except requests.exceptions.RequestException as e:
        # Catch remaining request exceptions (rare)
        current_app.logger.error(f"Unexpected request error: {e}", exc_info=True)
        return None

# Decryption with error handling
try:
    api_key = decrypt_data(encrypted_key, instance_path)
except (ValueError, InvalidToken) as e:
    current_app.logger.error(f"Failed to decrypt API key: {e}", exc_info=True)
    flash("Stored API key is corrupted. Please re-enter your API key.", "warning")
    api_key = ""
```

### Frontend AJAX Error Handling

```javascript
// Source: utils.js (existing pattern)
// Enhanced with comprehensive HTTP status checking

async function saveSettings(service) {
  const csrfToken = getCsrfToken();

  try {
    const response = await fetchWithTimeout(
      `/config/${service}/import-settings`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(formData)
      },
      10000  // 10s timeout
    );

    // CRITICAL: Check HTTP status before parsing
    if (!response.ok) {
      // Handle specific status codes
      if (response.status === 401) {
        // Global handler in utils.js already redirects to login
        return;
      }
      if (response.status === 403) {
        showToast("CSRF token expired. Please refresh the page.", "error");
        return;
      }
      if (response.status === 404) {
        showToast("API endpoint not found.", "error");
        return;
      }
      if (response.status >= 500) {
        showToast("Server error. Please try again later.", "error");
        return;
      }
      // Generic 4xx error
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      showToast(data.message || "Settings saved successfully", "success");
    } else {
      showToast(data.message || "Failed to save settings", "error");
    }

  } catch (err) {
    if (err.name === 'TimeoutError') {
      showToast(`${service} is not responding. Please check connection.`, "error");
    } else if (err.name === 'AbortError') {
      showToast("Request was cancelled.", "warning");
    } else {
      showToast("Network error. Please try again.", "error");
      console.error("Save settings error:", err);
    }
  }
}
```

### Docker Entrypoint with Permission Fixing

```bash
#!/bin/bash
# Source: https://oneuptime.com/blog/post/2026-01-25-docker-container-user-permissions/view

set -e  # Exit on error

# Function to fix permissions for bind mounts
fix_permissions() {
    echo "[INFO] Fixing permissions for /app/instance..."

    # Only chown if directory exists and we're running as root
    if [ -d "/app/instance" ] && [ "$(id -u)" = "0" ]; then
        chown -R listarr:listarr /app/instance
        echo "[INFO] Permissions fixed"
    else
        echo "[INFO] Skipping permission fix (not root or directory missing)"
    fi
}

# Main execution
if [ "$(id -u)" = "0" ]; then
    # Running as root - fix permissions then drop privileges
    fix_permissions

    # Run setup.py as listarr user (creates keys if missing)
    echo "[INFO] Running setup as listarr user..."
    gosu listarr python setup.py

    # Switch to non-root user and exec main command
    echo "[INFO] Switching to user listarr (UID 1000)..."
    exec gosu listarr "$@"
else
    # Already running as non-root (e.g., Kubernetes with securityContext)
    echo "[INFO] Running as UID $(id -u)"
    python setup.py
    exec "$@"
fi
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `random` module for tokens | `secrets` module | Python 3.6 (2016) | Cryptographically secure random, eliminates predictability attacks |
| Manual CSRF protection | Flask-WTF double-submit cookies | Flask-WTF 0.9 (2013) | Automatic CSRF validation, timing attack resistant |
| SHA256 password hashing | scrypt/bcrypt/argon2 | OWASP 2020 update | Work factor makes brute force impractical (scrypt already in Listarr Phase 11) |
| Bare `except:` allowed | PEP 760 proposes disallowing | PEP 760 (2024, draft) | Forces specific exception handling, prevents masking system errors |
| `SESSION_COOKIE_SAMESITE` defaults to `None` | Defaults to `Lax` | Flask 2.0 (2021) | CSRF protection by default, breaks some cross-site workflows |
| Docker runs as root | Non-root by default | Industry shift 2020-2022 | Reduces container breakout impact, requires permission handling |

**Deprecated/outdated:**
- **`PREFERRED_URL_SCHEME='https'`**: Deprecated in Flask 2.3+, use reverse proxy or `SESSION_COOKIE_SECURE` instead
- **`flask-talisman` force_https redirect**: Unnecessary if behind reverse proxy with HTTPS termination (but Listarr runs standalone per user decision)
- **Manual cookie signing**: itsdangerous library handles this internally in Flask sessions
- **Custom CSRF token generation**: Flask-WTF is standard, no need for custom implementation

## Open Questions

### Question 1: Should HSTS be enabled by default?

**What we know:** HSTS (`Strict-Transport-Security` header) forces HTTPS for all future requests, prevents protocol downgrade attacks.

**What's unclear:**
- Listarr is self-hosted, some users may run HTTP-only (homelab, localhost)
- Enabling HSTS without HTTPS breaks the app permanently (requires clearing browser HSTS cache)
- HSTS max-age persists even if app is uninstalled

**Recommendation:**
- **Don't enable HSTS by default** (too risky for self-hosted)
- Document in CLAUDE.md how to enable if behind HTTPS reverse proxy
- Add `if request.is_secure: response.headers['Strict-Transport-Security'] = 'max-age=31536000'` pattern for those who need it
- Add warning comment: "Only enable HSTS if app is accessible via HTTPS"

### Question 2: Should CSP be report-only mode initially?

**What we know:** CSP can break functionality if misconfigured. CSP `report-only` mode logs violations without blocking.

**What's unclear:**
- Does Tailwind CSS + TMDB images cover all CSP needs?
- Could future features (embed videos, third-party scripts) break CSP?
- Report-only requires endpoint to receive violation reports

**Recommendation:**
- **Start with enforcing CSP** (not report-only) since stack is known: Tailwind + TMDB images + no third-party scripts
- CSP policy: `default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://image.tmdb.org; script-src 'self'; frame-ancestors 'self'`
- Test locally before Phase 12 completion to verify no violations
- Document CSP policy in CLAUDE.md for future maintainers

### Question 3: Minimum supported Python version for `secrets` module?

**What we know:** `secrets` module added in Python 3.6 (2016). Flask 3.1.x requires Python 3.8+.

**What's unclear:** Is Listarr's minimum Python version documented?

**Recommendation:**
- Verify `requirements.txt` or `setup.py` specifies `python_requires='>=3.8'`
- `secrets` module safe to use (available since 3.6, Listarr requires 3.8+)
- No compatibility concerns

## Sources

### Primary (HIGH confidence)

**Flask Official Documentation:**
- [Flask Configuration Handling](https://flask.palletsprojects.com/en/stable/config/) - SECRET_KEY, session config
- [Flask Security Considerations](https://flask.palletsprojects.com/en/stable/web-security/) - CSRF, XSS, CSP
- [Flask WTForms Pattern](https://flask.palletsprojects.com/en/stable/patterns/wtforms/) - Form validation

**Python Official Documentation:**
- [secrets module](https://docs.python.org/3/library/secrets.html) - Cryptographic random generation
- [Built-in Exceptions](https://docs.python.org/3/library/exceptions.html) - Exception hierarchy

**WTForms Documentation:**
- [Validators](https://wtforms.readthedocs.io/en/3.0.x/validators/) - DataRequired, Length, NumberRange, URL, Regexp

**Docker Official Documentation:**
- [tmpfs mounts](https://docs.docker.com/engine/storage/tmpfs/) - Temporary in-memory filesystems
- [Docker Security](https://docs.docker.com/engine/security/) - General security best practices

**SQLAlchemy Documentation:**
- [SQLAlchemy Exceptions](https://docs.sqlalchemy.org/en/20/core/exceptions.html) - IntegrityError, OperationalError

### Secondary (MEDIUM confidence)

**Miguel Grinberg (Flask maintainer):**
- [Cookie Security for Flask Applications](https://blog.miguelgrinberg.com/post/cookie-security-for-flask-applications) - SESSION_COOKIE_SECURE, SAMESITE
- [How Secure Is The Flask User Session?](https://blog.miguelgrinberg.com/post/how-secure-is-the-flask-user-session) - Session signing, replay attacks
- [The New Way To Generate Secure Tokens in Python](https://blog.miguelgrinberg.com/post/the-new-way-to-generate-secure-tokens-in-python) - secrets module

**Flask-WTF Documentation:**
- [CSRF Protection](https://flask-wtf.readthedocs.io/en/latest/csrf/) - csrf.exempt decorator, configuration

**Flask-Talisman:**
- [GoogleCloudPlatform/flask-talisman](https://github.com/GoogleCloudPlatform/flask-talisman) - Security headers reference implementation
- [flask-talisman PyPI](https://pypi.org/project/flask-talisman/) - Installation and basic usage

**Real Python:**
- [Python Exceptions: An Introduction](https://realpython.com/python-exceptions/) - Exception handling best practices
- [secrets module reference](https://realpython.com/ref/stdlib/secrets/) - Practical examples

**2026 Docker Security Best Practices:**
- [How to Handle Docker Security Best Practices](https://oneuptime.com/blog/post/2026-02-02-docker-security-best-practices/view) - Non-root users, read-only filesystems
- [Docker Security Best Practices (2026): Hardening Host, Images, Runtime](https://thelinuxcode.com/docker-security-best-practices-2026-hardening-the-host-images-and-runtime-without-slowing-teams-down/) - Comprehensive 2026 guide
- [How to Set Up Docker Container User Permissions](https://oneuptime.com/blog/post/2026-01-25-docker-container-user-permissions/view) - Bind mount permissions, entrypoint patterns
- [How to Run Docker Containers as Non-Root Users](https://oneuptime.com/blog/post/2026-01-16-docker-run-non-root-user/view) - USER instruction, security context

**OWASP:**
- [SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) - Parameterized queries
- [Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html) - Container hardening

**Additional Technical Resources:**
- [PEP 760 – No More Bare Excepts](https://peps.python.org/pep-0760/) - Future Python direction
- [BinaryScripts: Session Management and Security in Flask for Production](https://binaryscripts.com/flask/2025/01/20/session-management-and-security-in-flask-for-production.html) - SESSION_COOKIE_SECURE, PERMANENT_SESSION_LIFETIME
- [Medium: Best Practices for Secure Docker Containerization](https://medium.com/@maheshwar.ramkrushna/best-practices-for-secure-docker-containerization-non-root-user-read-only-volumes-and-resource-d34ed09b1bd3) - Non-root user, read-only volumes
- [Medium: Can't change ownership of folders and files in Docker containers](https://medium.com/@haroldfinch01/cant-change-ownership-of-folders-and-files-in-docker-containers-53455eaab8c8) - Bind mount chown patterns
- [DevToolbox: SQL Injection Prevention Guide 2026](https://devtoolbox.dedyn.io/blog/sql-injection-prevention-guide) - Parameterized queries, ORM safety

### Tertiary (LOW confidence - marked for validation)

None. All key findings verified with official documentation or authoritative sources.

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH - All libraries already in use or Python stdlib
- **Flask security config:** HIGH - Verified with official Flask docs and Miguel Grinberg (Flask maintainer)
- **Docker patterns:** HIGH - Verified with 2026-dated Docker security best practices and official Docker docs
- **Exception handling:** HIGH - Official Python docs + PEP 760 proposal
- **WTForms validation:** HIGH - Official WTForms documentation
- **Frontend error handling:** MEDIUM - Current codebase patterns verified, best practices from general web dev (not Flask-specific)

**Research date:** 2026-02-16
**Valid until:** 2026-05-16 (90 days - Flask and Docker security practices are relatively stable)

**Research scope notes:**
- Rate limiting explicitly excluded per user decision
- No reverse proxy assumption per user decision (Flask handles security headers directly)
- Focused on production security foot-guns, not advanced attack vectors (no WAF, DDoS protection, etc.)
- Single-user app context (no multi-tenancy, RBAC, OAuth concerns)
