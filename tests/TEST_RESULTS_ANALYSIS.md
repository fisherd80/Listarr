# Dashboard Routes Test Results Analysis

## Test Summary
- **Total Tests**: 38
- **Passed**: 28 (73.7%)
- **Failed**: 10 (26.3%)

## Failed Tests Analysis

### 1. HTML Content Test Failures

#### `test_dashboard_page_shows_sonarr_card` - FAILED
**Issue**: Test expects "Missing Series" but HTML contains "Missing Episodes"
- **Expected**: `b'Missing Series'`
- **Actual**: HTML shows "Missing Episodes" (line 115 in dashboard.html)
- **Root Cause**: Test expectation is outdated - we changed the label to "Missing Episodes" during Sonarr implementation
- **Fix**: Update test to expect "Missing Episodes"

#### `test_dashboard_page_includes_refresh_button` - FAILED
**Issue**: Test expects "dashboard-refresh-button" but HTML uses "refresh-dashboard-btn"
- **Expected**: `b'dashboard-refresh-button'`
- **Actual**: HTML has `id="refresh-dashboard-btn"` (line 14 in dashboard.html)
- **Root Cause**: Test expectation doesn't match actual HTML ID
- **Fix**: Update test to expect "refresh-dashboard-btn"

### 2. Database Initialization Issues

#### `test_dashboard_stats_with_no_services_configured` - FAILED
**Issue**: Status is "offline" instead of "not_configured"
- **Expected**: `status == 'not_configured'`
- **Actual**: `status == 'offline'`
- **Root Cause**: Cache initialization at app startup tries to query `service_config` table before it exists in test environment, causing an error that sets status to "offline"
- **Error**: `sqlite3.OperationalError: no such table: service_config`
- **Fix**: Handle missing tables gracefully in cache initialization, or ensure database is initialized before cache refresh

#### `test_dashboard_stats_with_only_base_url_configured` - FAILED
**Issue**: Same as above - status is "offline" instead of "not_configured"
- **Root Cause**: Same database initialization issue

#### `test_dashboard_stats_with_only_api_key_configured` - FAILED
**Issue**: Same as above - status is "offline" instead of "not_configured"
- **Root Cause**: Same database initialization issue

### 3. Recent Jobs Query Issues

#### `test_recent_jobs_with_job_without_list_id` - FAILED
**Issue**: Returns 0 jobs instead of 1
- **Expected**: 1 job with fallback name "Job #{job_id}"
- **Actual**: Empty array `[]`
- **Root Cause**: Query uses `.join(List)` which excludes jobs without a valid `list_id` (inner join behavior)
- **Fix**: Use `.outerjoin(List)` or handle jobs without list_id separately

#### `test_recent_jobs_with_deleted_list` - FAILED
**Issue**: Returns 0 jobs instead of 1
- **Expected**: 1 job with fallback name when list is deleted
- **Actual**: Empty array `[]`
- **Root Cause**: Same as above - inner join excludes jobs whose lists don't exist

#### `test_recent_jobs_only_includes_finished_jobs` - FAILED
**Issue**: Returns 0 jobs instead of 1
- **Expected**: 1 finished job (excludes running job without finished_at)
- **Actual**: Empty array `[]`
- **Root Cause**: Query uses `.join(List)` which may fail if the list doesn't exist, or the join condition is too strict

#### `test_recent_jobs_summary_formatting` - FAILED
**Issue**: Returns 0 jobs instead of 4
- **Expected**: 4 jobs with different summary formats
- **Actual**: Empty array `[]`
- **Root Cause**: Same join issue - jobs may not have associated lists in test setup

#### `test_recent_jobs_handles_database_error` - FAILED
**Issue**: Test expects 500 status but gets 200
- **Expected**: `status_code == 500` with empty jobs array
- **Actual**: `status_code == 200` with empty jobs array
- **Root Cause**: Error handling catches exceptions and returns 200 with empty array instead of 500
- **Fix**: Either update test expectation or change error handling to return 500

## Code Issues Identified

### 1. Cache Initialization Error Handling
**Location**: `listarr/services/dashboard_cache.py`
- Cache initialization at app startup doesn't handle missing database tables gracefully
- Should check if tables exist before querying, or catch OperationalError and set status to "not_configured"

### 2. Recent Jobs Query Logic
**Location**: `listarr/routes/dashboard_routes.py` line 82
- Uses `.join(List)` which is an inner join - excludes jobs without valid list_id
- Should use `.outerjoin(List)` to include all jobs, even without lists
- Or handle missing lists in the loop instead of relying on join

### 3. Error Response Status
**Location**: `listarr/routes/dashboard_routes.py` line 135
- Returns 200 with empty array on error
- Test expects 500 status code
- Need to align error handling with test expectations

## Recommended Fixes

### Priority 1: Fix Recent Jobs Query
1. Change `.join(List)` to `.outerjoin(List)` to include jobs without lists
2. Update job_name and service logic to handle None list_obj

### Priority 2: Fix Test Expectations
1. Update HTML content tests to match actual HTML
2. Update error handling test to match actual behavior (or vice versa)

### Priority 3: Fix Cache Initialization
1. Add try/except around database queries in cache initialization
2. Set status to "not_configured" when tables don't exist
3. Or ensure database is initialized before cache refresh in tests

## Test Coverage Status

✅ **Working Tests (28)**:
- Dashboard page rendering
- Radarr card display
- Recent jobs section
- JavaScript inclusion
- CSRF token
- Added by Listarr display
- Cache refresh parameter
- Added by Listarr calculations
- Service configuration (when properly set up)
- Recent jobs (when lists exist)
- Error handling (decryption, timeouts, API failures)
- Response structure validation

❌ **Failing Tests (10)**:
- Sonarr card text (outdated expectation)
- Refresh button ID (outdated expectation)
- Stats with no services (database init issue)
- Stats with partial config (database init issue)
- Recent jobs without lists (join issue)
- Recent jobs with deleted lists (join issue)
- Recent jobs filtering (join issue)
- Recent jobs summary (join issue)
- Database error handling (status code mismatch)
