# Dashboard Test Suite Summary

## Overview
Comprehensive test coverage for the Dashboard functionality, matching the style and thoroughness of existing Settings and Config tests.

## Test Files Created

### 1. Integration Tests: `tests/integration/test_dashboard_integration.py`
**Total Tests: 18**

#### TestDashboardEndToEndWorkflow (5 tests)
End-to-end workflows testing complete dashboard data flow:
- `test_full_dashboard_load_with_radarr_only` - Configure Radarr → load dashboard → verify stats
- `test_full_dashboard_load_with_sonarr_only` - Configure Sonarr → load dashboard → verify stats
- `test_full_dashboard_load_with_both_services` - Configure both services → verify aggregation
- `test_dashboard_load_with_no_services_configured` - Dashboard with no services
- `test_radarr_offline_shows_offline_status` - Offline service detection

#### TestRecentJobsWorkflow (5 tests)
Job history display and data handling:
- `test_recent_jobs_with_no_jobs` - Empty database scenario
- `test_recent_jobs_with_completed_jobs` - Display completed jobs
- `test_recent_jobs_with_failed_jobs` - Display failed jobs with error messages
- `test_recent_jobs_limit_to_five` - Only last 5 jobs returned
- `test_recent_jobs_with_no_list_association` - Jobs without associated lists

#### TestDashboardErrorRecovery (4 tests)
Error handling and graceful degradation:
- `test_dashboard_handles_decryption_error` - Decryption failure handling
- `test_dashboard_handles_api_timeout` - API timeout handling
- `test_dashboard_handles_partial_api_failure` - Status succeeds, count fails
- `test_dashboard_handles_database_error_for_jobs` - Database error handling

#### TestMultipleRequestsScenarios (2 tests)
Concurrent and repeated request handling:
- `test_rapid_succession_dashboard_requests` - Rapid successive requests
- `test_interleaved_dashboard_and_jobs_requests` - Interleaved API calls

#### TestDashboardTimestamps (2 tests)
Timestamp tracking and formatting:
- `test_dashboard_updates_timestamp_on_each_fetch` - Timestamp updates
- `test_not_configured_service_has_no_timestamp` - Not configured services

### 2. Route Tests: `tests/routes/test_dashboard_routes.py`
**Total Tests: 34**

#### TestDashboardPageGET (7 tests)
Dashboard page rendering and structure:
- `test_dashboard_page_renders_successfully` - Basic page load
- `test_dashboard_page_shows_radarr_card` - Radarr service card
- `test_dashboard_page_shows_sonarr_card` - Sonarr service card
- `test_dashboard_page_shows_recent_jobs_section` - Jobs section
- `test_dashboard_page_includes_refresh_button` - Manual refresh functionality
- `test_dashboard_page_includes_javascript` - JavaScript inclusion
- `test_dashboard_page_includes_csrf_token` - CSRF protection

#### TestDashboardStatsGET (10 tests)
Statistics API endpoint testing:
- `test_dashboard_stats_with_no_services_configured` - Default values
- `test_dashboard_stats_with_radarr_configured_and_online` - Radarr online
- `test_dashboard_stats_with_sonarr_configured_and_online` - Sonarr online
- `test_dashboard_stats_with_radarr_configured_but_offline` - Offline detection
- `test_dashboard_stats_when_radarr_returns_empty_status` - Empty status handling
- `test_dashboard_stats_with_zero_movies` - Zero count handling
- `test_dashboard_stats_with_only_base_url_configured` - Partial config
- `test_dashboard_stats_with_only_api_key_configured` - Partial config
- `test_dashboard_stats_with_both_services_configured` - Multi-service
- `test_dashboard_stats_with_one_service_online_one_offline` - Mixed status

#### TestRecentJobsGET (9 tests)
Recent jobs API endpoint testing:
- `test_recent_jobs_with_empty_database` - No jobs scenario
- `test_recent_jobs_with_single_completed_job` - Single job display
- `test_recent_jobs_with_failed_job` - Failed job display
- `test_recent_jobs_orders_by_finished_at_desc` - Descending order
- `test_recent_jobs_limits_to_five_jobs` - 5 job limit
- `test_recent_jobs_with_job_without_list_id` - Missing list reference
- `test_recent_jobs_with_deleted_list` - Deleted list handling
- `test_recent_jobs_only_includes_finished_jobs` - Filters running jobs
- `test_recent_jobs_summary_formatting` - Summary text formatting

#### TestDashboardErrorHandling (4 tests)
Error scenarios and edge cases:
- `test_dashboard_stats_handles_decryption_error` - Decryption failures
- `test_recent_jobs_handles_database_error` - Database errors
- `test_dashboard_stats_handles_partial_api_failure` - Partial failures
- `test_dashboard_stats_handles_timeout` - Timeout errors

#### TestDashboardDataFormats (4 tests)
Data structure and format validation:
- `test_dashboard_stats_returns_iso_timestamp` - ISO timestamp format
- `test_recent_jobs_executed_at_is_iso_format` - ISO timestamp format
- `test_dashboard_stats_response_structure` - Response structure
- `test_recent_jobs_response_structure` - Response structure

## Test Coverage Summary

### Routes Tested
1. **GET /** - Dashboard home page
2. **GET /api/dashboard/stats** - Service statistics aggregation
3. **GET /api/dashboard/recent-jobs** - Recent job history

### Functionality Covered

#### Service Status Detection
- ✅ Not configured (no API key or base URL)
- ✅ Online (service reachable and responding)
- ✅ Offline (service configured but unreachable)

#### Data Aggregation
- ✅ Single service (Radarr only)
- ✅ Single service (Sonarr only)
- ✅ Multiple services (both configured)
- ✅ Mixed statuses (one online, one offline)
- ✅ Parallel API calls with ThreadPoolExecutor

#### Statistics Tested
- ✅ Total movies/series count
- ✅ Missing movies/series count
- ✅ Service version display
- ✅ Last updated timestamp
- ✅ Zero count handling

#### Job History
- ✅ Empty state (no jobs)
- ✅ Completed jobs with summary
- ✅ Failed jobs with error messages
- ✅ Job ordering (descending by finished_at)
- ✅ Limit to 5 most recent jobs
- ✅ Jobs without list association
- ✅ Jobs with deleted lists
- ✅ Running jobs excluded (only finished)

#### Error Handling
- ✅ Decryption errors (corrupted API keys)
- ✅ API timeouts (service unreachable)
- ✅ Partial API failures (status succeeds, count fails)
- ✅ Database errors (query failures)
- ✅ Empty/null responses from services
- ✅ Missing or invalid configuration

#### Data Formats
- ✅ ISO timestamp format validation
- ✅ JSON response structure validation
- ✅ Summary text formatting
- ✅ Service name and status enums

### Edge Cases Tested
1. **Configuration edge cases**:
   - Base URL without API key
   - API key without base URL
   - Empty strings for credentials

2. **API response edge cases**:
   - Null/empty status from service
   - Zero counts
   - Missing version information

3. **Job history edge cases**:
   - Jobs without list_id
   - Jobs with deleted lists
   - Jobs with no items processed
   - Jobs with only added items
   - Jobs with only skipped items

4. **Concurrent operations**:
   - Rapid succession requests
   - Interleaved stats and jobs requests

## Test Patterns Used

### Mocking Strategy
All external API calls are mocked using `unittest.mock.patch`:
```python
@patch('listarr.routes.dashboard_routes.get_radarr_system_status')
@patch('listarr.routes.dashboard_routes.get_movie_count')
@patch('listarr.routes.dashboard_routes.get_missing_movies_count')
```

### Database Setup
Tests use in-memory SQLite with proper fixtures:
```python
with app.app_context():
    encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
    config = ServiceConfig(...)
    db.session.add(config)
    db.session.commit()
```

### Response Validation
Comprehensive assertions on response structure:
```python
assert response.status_code == 200
data = response.get_json()
assert data['radarr']['configured'] is True
assert data['radarr']['status'] == 'online'
assert data['radarr']['total_movies'] == 150
```

## Running the Tests

### Run all dashboard tests:
```bash
pytest tests/integration/test_dashboard_integration.py tests/routes/test_dashboard_routes.py -v
```

### Run with coverage:
```bash
pytest tests/integration/test_dashboard_integration.py tests/routes/test_dashboard_routes.py --cov=listarr.routes.dashboard_routes --cov-report=term-missing
```

### Run specific test class:
```bash
pytest tests/integration/test_dashboard_integration.py::TestDashboardEndToEndWorkflow -v
```

### Run specific test:
```bash
pytest tests/routes/test_dashboard_routes.py::TestDashboardStatsGET::test_dashboard_stats_with_radarr_configured_and_online -v
```

## Test Results

All 52 tests pass successfully:
- **Integration Tests**: 18/18 passing
- **Route Tests**: 34/34 passing
- **Total**: 52/52 passing

## Comparison to Settings/Config Tests

These dashboard tests follow the same comprehensive patterns as the existing tests:

### Similarities:
1. **Test Organization**: Clear class-based grouping by functionality
2. **Naming Convention**: Descriptive test names following `test_<action>_<condition>_<expected_result>` pattern
3. **Docstrings**: Every test has a clear docstring explaining its purpose
4. **Fixtures**: Consistent use of `app`, `client`, and `temp_instance_path` fixtures
5. **Mocking**: Proper mocking of external dependencies (API calls)
6. **Database Testing**: Create/read/update scenarios with proper cleanup
7. **Error Scenarios**: Comprehensive error handling and edge case testing
8. **Assertions**: Multiple assertions per test to verify complete behavior

### Dashboard-Specific Features:
1. **Multi-service aggregation** - Tests for handling multiple services simultaneously
2. **Parallel API calls** - Tests ThreadPoolExecutor behavior
3. **Job history display** - Tests for list association and summary formatting
4. **Status determination** - Tests three-state system (configured/online/offline)
5. **Timestamp tracking** - Tests ISO format and real-time updates

## Code Quality

- ✅ No code duplication
- ✅ Clear test names and documentation
- ✅ Proper use of fixtures
- ✅ Comprehensive edge case coverage
- ✅ Follows existing project patterns
- ✅ All imports properly organized
- ✅ Consistent with Settings/Config test style

## Notes for Developers

1. **List Model Requirement**: When creating `List` objects in tests, always include `filters_json={}` as it's a NOT NULL field.

2. **ServiceConfig Model**: The `api_key_encrypted` field is NOT NULL, use empty string `""` instead of `None` for partial configs.

3. **Job Status**: Only jobs with `finished_at` timestamp are included in recent jobs (filters out running jobs).

4. **Service Detection**: A service is considered "configured" only if both `base_url` AND `api_key_encrypted` are present and non-empty.

5. **Parallel Execution**: Dashboard uses ThreadPoolExecutor for parallel API calls - tests mock individual functions rather than the executor itself.

6. **Timestamp Format**: All timestamps are ISO format with timezone (UTC) and should end with 'Z' or include '+' for offset.
