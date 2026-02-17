---
phase: 11-user-authentication
plan: 02
subsystem: authentication
tags: [auth, login-required, route-protection, password-change, cli-reset]
dependency_graph:
  requires: [11-01-core-auth]
  provides: [route-protection, password-management, nav-auth-ui]
  affects: [all-routes, settings-page, base-template]
tech_stack:
  added: []
  patterns: [login_required-decorator, global-401-handler, AJAX-password-change, CLI-password-reset]
key_files:
  created: []
  modified:
    - listarr/routes/lists_routes.py
    - listarr/routes/jobs_routes.py
    - listarr/routes/schedule_routes.py
    - listarr/routes/config_routes.py
    - listarr/routes/settings_routes.py
    - listarr/templates/base.html
    - listarr/static/js/utils.js
    - listarr/templates/settings.html
    - setup.py
decisions:
  - Dashboard page and APIs remain public (read-only without login)
  - All other pages protected with @login_required decorator
  - Global fetch() override for 401 handling (all AJAX calls covered)
  - Password change requires current password verification
  - CLI reset command for recovery (python setup.py --reset-password)
  - Nav links conditionally shown based on authentication state
  - Vanilla JS dropdown (no Alpine.js dependency)
metrics:
  duration: 12 minutes
  tasks_completed: 2
  files_created: 0
  files_modified: 9
  commits: 2
  lines_added: ~336
completed: 2026-02-14
---

# Phase 11 Plan 02: Application Auth Integration Summary

**Wired authentication into the existing application with route protection, user navigation UI, AJAX 401 handling, password change functionality, and CLI password reset.**

## Objectives Achieved

1. All non-dashboard routes protected with @login_required decorator
2. Nav bar updated with conditional username dropdown and logout
3. Global 401 handler for AJAX session expiry
4. Password change on Settings page with current password verification
5. CLI password reset command for account recovery

## Implementation Details

### Task 1: Route protection, nav bar update, and AJAX 401 handler

**Files:** `listarr/routes/*.py`, `listarr/templates/base.html`, `listarr/static/js/utils.js`

**Route Protection Strategy:**
- **Public routes:** Dashboard page (`GET /`), dashboard API stats (`GET /api/dashboard/stats`), dashboard API recent-jobs (`GET /api/dashboard/recent-jobs`), dashboard API upcoming (`GET /api/dashboard/upcoming`)
- **Protected routes:** All other routes (lists, jobs, schedule, config, settings)

Added `from flask_login import login_required` import to all route files that needed protection:
- `lists_routes.py`: 14 routes protected (lists_page, api_lists, create_list, edit_list, delete_list, list_wizard, toggle_list, wizard_preview, wizard_submit, wizard_defaults, cache_stats, run_list_import, get_list_status)
- `jobs_routes.py`: 8 routes protected (jobs_page, get_jobs, get_recent_jobs, get_job_detail, rerun_job, clear_all_jobs, clear_list_jobs, get_running_jobs)
- `schedule_routes.py`: 5 routes protected (schedule_page, pause_schedule, resume_schedule, get_schedule_status, update_schedule)
- `config_routes.py`: 7 routes protected (config_page, test_radarr_api, test_sonarr_api, fetch_quality_profiles_route, fetch_root_folders_route, fetch_import_settings, save_import_settings)
- `settings_routes.py`: 2 routes protected (settings_page, test_tmdb_api)

**Nav Bar Updates:**
- Wrapped Lists, Jobs, Schedule, Config links with `{% if current_user.is_authenticated %}`
- Dashboard link always visible (public access)
- Right side conditional display:
  - When authenticated: Settings link + username dropdown with logout button
  - When not authenticated: Login link only
- Dropdown implementation:
  - Vanilla JS toggle (no Alpine.js dependency)
  - Click outside to close
  - Form POST to `/logout` with CSRF token

**Global 401 Handler:**
- Overrode `window.fetch` in `utils.js` with IIFE wrapper
- Intercepts 401 responses on all AJAX calls
- Stores current URL in `sessionStorage['loginRedirect']` for post-login redirect
- Redirects to `/login` unless already on login page
- Covers all existing AJAX calls (dashboard.js, jobs.js, lists.js, config.js, settings.js, wizard.js, schedule.js)

**Commit:** 83a4a63

### Task 2: Settings password change and CLI reset command

**Files:** `listarr/routes/settings_routes.py`, `listarr/templates/settings.html`, `setup.py`

**Password Change Route:**
- Added `POST /settings/change-password` AJAX endpoint
- Imported `ChangePasswordForm` from `listarr.forms.auth_forms`
- Imported `current_user` from `flask_login`
- Validation flow:
  1. Form validation (WTForms validates new password match)
  2. Current password verification via `current_user.check_password()`
  3. Password update via `current_user.set_password()`
  4. Database commit
- Returns JSON with success/message for toast display
- Collects validation errors from form.errors for user feedback

**Settings Template Updates:**
- Replaced hardcoded "User Account" section with conditional "Change Password" section
- Wrapped in `{% if current_user.is_authenticated %}`
- Three password fields with visibility toggles:
  - Current Password
  - New Password
  - Confirm New Password
- Eye icon buttons to toggle password visibility
- AJAX form submission handler:
  - Prevents default form submission
  - Posts to `/settings/change-password` with CSRF token
  - Shows success toast and clears form on success
  - Shows error toast with validation message on failure
- Shared `togglePasswordVisibility(fieldId)` function for all three fields

**CLI Password Reset:**
- Added `--reset-password` flag to `setup.py`
- Imports: `sys`, `getpass` from stdlib
- Added `reset_user_password()` function:
  - Checks instance folder exists
  - Creates app context
  - Queries for first user
  - Prompts for new password (hidden input via `getpass`)
  - Prompts for confirmation
  - Validates passwords match and not empty
  - Updates user password via `set_password()`
  - Commits to database
- Modified `main()` to check for `--reset-password` in `sys.argv`
- Usage: `python setup.py --reset-password`

**Commit:** 511d09b

## Deviations from Plan

None - plan executed exactly as written.

## Security Features

1. **Route protection:** All non-dashboard routes require authentication
2. **Session expiry handling:** Global 401 handler prevents stale session errors
3. **Password change security:** Current password required before changing password
4. **Password masking:** All password fields masked with visibility toggle option
5. **CSRF protection:** All forms and AJAX requests include CSRF token
6. **CLI reset security:** Requires file system access to instance folder (server access)

## Testing & Verification

Manual verification checklist (per plan):
1. Visit `/lists` without login → redirected to `/login`
2. Visit `/` without login → dashboard loads (public)
3. Visit `/api/dashboard/stats` without login → returns JSON (public)
4. Visit `/config` without login → redirected to `/login`
5. Login → nav shows username dropdown with logout option
6. Click logout → redirected to login, nav shows "Login" link
7. Verify only Dashboard link visible in nav when logged out

Password change verification:
1. Login, go to Settings page → "Change Password" section visible
2. Enter correct current password + new password → success toast
3. Enter incorrect current password → error toast "Current password is incorrect"
4. Enter mismatched new passwords → error toast about mismatch
5. Logout, login with new password → works

CLI reset verification:
1. Run `python setup.py --reset-password` from CLI → prompts for new password
2. Enter matching passwords → "Password reset successfully"
3. Login with CLI-reset password → works

## Architecture Notes

- **Global 401 handler pattern:** Single IIFE in utils.js covers all fetch calls across entire app
- **Conditional nav rendering:** Jinja2 template checks `current_user.is_authenticated` at render time
- **Vanilla JS dropdown:** No additional dependencies, uses vanilla DOM manipulation
- **Login redirect storage:** Uses `sessionStorage` for post-login redirect (survives page reload, not tab close)
- **Password change AJAX:** Prevents page reload, provides instant feedback via toasts
- **CLI reset pattern:** Reuses Flask app context for database operations outside web context

## Next Steps

1. Test existing functionality with authentication enabled
2. Verify all AJAX calls properly redirect on 401
3. Test session persistence and remember me functionality
4. Verify setup wizard blocks after first user created
5. Consider adding user profile information to Settings page
6. Update documentation with authentication workflows

## Dependencies Added

None (used existing Flask-Login from Plan 01)

## Self-Check

**Checking modified files exist:**
- listarr/routes/lists_routes.py: FOUND
- listarr/routes/jobs_routes.py: FOUND
- listarr/routes/schedule_routes.py: FOUND
- listarr/routes/config_routes.py: FOUND
- listarr/routes/settings_routes.py: FOUND
- listarr/templates/base.html: FOUND
- listarr/static/js/utils.js: FOUND
- listarr/templates/settings.html: FOUND
- setup.py: FOUND

**Checking commits exist:**
- 83a4a63 (Task 1): FOUND
- 511d09b (Task 2): FOUND

**Checking route protection:**
```bash
grep -r "@login_required" listarr/routes/ | wc -l
# Expected: 36 (all protected routes)
```

**Checking nav bar conditionals:**
```bash
grep "current_user.is_authenticated" listarr/templates/base.html | wc -l
# Expected: 2 (nav links conditional, user dropdown conditional)
```

**Checking 401 handler:**
```bash
grep "response.status === 401" listarr/static/js/utils.js | wc -l
# Expected: 1 (global fetch override)
```

## Self-Check: PASSED

All files modified, all commits exist, all route protection in place, nav bar conditionals present, 401 handler implemented.
