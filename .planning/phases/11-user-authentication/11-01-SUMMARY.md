---
phase: 11-user-authentication
plan: 01
subsystem: authentication
tags: [auth, flask-login, user-model, session-management]
dependency_graph:
  requires: []
  provides: [user-authentication, session-management, login-flow]
  affects: [all-routes]
tech_stack:
  added: [Flask-Login==0.6.3]
  patterns: [UserMixin, password-hashing, session-cookies, CSRF-protection]
key_files:
  created:
    - listarr/forms/auth_forms.py
    - listarr/routes/auth_routes.py
    - listarr/templates/auth/login.html
    - listarr/templates/auth/setup.html
  modified:
    - listarr/__init__.py
    - listarr/models/user_model.py
    - listarr/routes/__init__.py
    - requirements.txt
    - CLAUDE.md
decisions:
  - Use Flask-Login 0.6.3 (latest available version, 0.7.0 does not exist)
  - Werkzeug's scrypt password hashing (secure default, no bcrypt needed)
  - Remember me cookie 30 days with HttpOnly and SameSite=Lax
  - Generic "Invalid credentials" error prevents username enumeration
  - Setup wizard blocks after first user created
  - Auto-login after setup for frictionless first-run experience
  - Safe redirect validation to prevent open redirect attacks
  - Standalone auth templates without nav bar for clean branded experience
  - Password toggle on all password fields (matches API key pattern)
metrics:
  duration: 6 minutes
  tasks_completed: 2
  files_created: 4
  files_modified: 5
  commits: 2
  lines_added: ~450
completed: 2026-02-14
---

# Phase 11 Plan 01: Core Authentication System Summary

**Implemented Flask-Login authentication with User model, auth forms, login/setup/logout routes, and branded templates.**

## Objectives Achieved

1. User model enhanced with UserMixin and password hashing methods
2. Flask-Login initialized in app factory with user_loader and unauthorized_handler
3. Three auth forms created (Login, Setup, ChangePassword)
4. Auth routes implemented with security best practices
5. Branded login and setup templates with dark mode support

## Implementation Details

### Task 1: User Model, Flask-Login Init, Auth Forms, and Dependency

**Files:** `listarr/models/user_model.py`, `listarr/__init__.py`, `listarr/forms/auth_forms.py`, `requirements.txt`

- Added Flask-Login 0.6.3 to requirements.txt (0.7.0 does not exist in PyPI)
- Updated User model:
  - Added `UserMixin` parent class (provides is_authenticated, is_active, is_anonymous, get_id)
  - Added `set_password()` method using werkzeug.security.generate_password_hash
  - Added `check_password()` method using werkzeug.security.check_password_hash
- Initialized Flask-Login in app factory:
  - Created module-level `login_manager` instance
  - Configured `login_view = "main.login_page"` and `login_message = None`
  - Set remember me cookie duration (30 days), HttpOnly, SameSite=Lax
  - Registered `@login_manager.user_loader` with int() conversion (critical for SQLAlchemy)
  - Registered `@login_manager.unauthorized_handler` with JSON/page detection
- Created `listarr/forms/auth_forms.py`:
  - LoginForm: username, password, remember_me, submit
  - SetupForm: username, password, password_confirm (with EqualTo validator), submit
  - ChangePasswordForm: current_password, new_password, new_password_confirm, submit

**Commit:** 5b263aa

### Task 2: Auth Routes and Branded Login/Setup Templates

**Files:** `listarr/routes/auth_routes.py`, `listarr/routes/__init__.py`, `listarr/templates/auth/login.html`, `listarr/templates/auth/setup.html`

- Created `listarr/routes/auth_routes.py`:
  - `is_safe_redirect_url()` helper validates redirect targets to prevent open redirect attacks
  - `GET/POST /login` route:
    - Redirects authenticated users to dashboard
    - Generic "Invalid credentials" error (no username enumeration)
    - Safe redirect with session/query string next page support
    - Remember me checkbox support
  - `GET/POST /setup` route:
    - Blocks access if user already exists (redirects to dashboard)
    - Creates user with hashed password
    - Auto-logs user in after account creation
    - Redirects to dashboard
  - `POST /logout` route:
    - Requires @login_required decorator
    - Calls logout_user() and redirects to login
  - `@bp.before_app_request check_setup()`:
    - Skips static files, auth pages, and None endpoints
    - Redirects to setup if no users exist
- Registered auth routes in `listarr/routes/__init__.py`
- Created branded templates:
  - Standalone HTML structure (no base.html extension)
  - Includes Tailwind CDN and config (dark mode: "media")
  - Login page:
    - Username and password fields
    - Password visibility toggle (eye icon)
    - Remember me checkbox
    - Error message display area
    - Dark mode support (bg-gray-900, bg-gray-800 card)
  - Setup page:
    - Username, password, confirm password fields
    - Password visibility toggles on both password fields
    - WTForms error display for validation failures
    - Same visual style as login page

**Commit:** b8082c3

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Flask-Login version correction**
- **Found during:** Task 1 dependency installation
- **Issue:** Plan specified Flask-Login==0.7.0, but this version does not exist in PyPI (latest is 0.6.3)
- **Fix:** Changed requirements.txt to Flask-Login==0.6.3
- **Files modified:** requirements.txt
- **Commit:** 5b263aa

**2. [Rule 3 - Blocking] CLAUDE.md sync script update**
- **Found during:** Task 1 commit (pre-commit hook failure)
- **Issue:** sync_claude_md.py DEP_PURPOSES map missing Flask-Login entry
- **Fix:** Added `"Flask-Login": "Session and user authentication"` to DEP_PURPOSES
- **Files modified:** _ai/scripts/sync_claude_md.py (gitignored)
- **Commit:** 5b263aa

## Security Features

1. **Password hashing:** Werkzeug's scrypt algorithm (secure default)
2. **Generic error messages:** "Invalid credentials" prevents username enumeration
3. **Safe redirect validation:** `is_safe_redirect_url()` prevents open redirect attacks
4. **CSRF protection:** All forms include hidden_tag(), all routes use Flask-WTF CSRF
5. **Remember me security:** HttpOnly + SameSite=Lax cookies (30-day duration)
6. **Session management:** Flask-Login handles session cookies, logout clears session
7. **Setup wizard security:** Blocked after first user exists, prevents unauthorized account creation

## Testing & Verification

Verified via manual test script:
- Database initialization works
- No users exist initially (fresh install)
- User creation with password hashing
- Password verification (correct and incorrect passwords)
- UserMixin methods available (is_authenticated, is_active, get_id)
- Setup blocking check (user exists)

All tests passed successfully.

## Architecture Notes

- **User loader converts to int:** SQLAlchemy requires int ID, Flask-Login passes string
- **Unauthorized handler detects AJAX:** Returns JSON 401 for AJAX, redirects for pages
- **Setup check runs before all requests:** Ensures first-run experience
- **Auth routes registered first:** Ensures setup check runs before other blueprints
- **Standalone auth templates:** Clean branded experience without app navigation

## Next Steps

1. Protect existing routes with @login_required decorator
2. Add logout button to navigation bar
3. Add change password route and settings page integration
4. Test session persistence and remember me functionality
5. Add user profile display in navigation

## Dependencies Added

- Flask-Login==0.6.3: Session and user authentication

## Self-Check

**Checking created files exist:**
- listarr/forms/auth_forms.py: FOUND
- listarr/routes/auth_routes.py: FOUND
- listarr/templates/auth/login.html: FOUND
- listarr/templates/auth/setup.html: FOUND

**Checking modified files exist:**
- listarr/__init__.py: FOUND
- listarr/models/user_model.py: FOUND
- listarr/routes/__init__.py: FOUND
- requirements.txt: FOUND
- CLAUDE.md: FOUND

**Checking commits exist:**
- 5b263aa (Task 1): FOUND
- b8082c3 (Task 2): FOUND

## Self-Check: PASSED

All files created, all files modified, all commits exist.
