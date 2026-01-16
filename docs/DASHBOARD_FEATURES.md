# Dashboard Features Documentation

## Overview

The Listarr dashboard provides a comprehensive overview of Radarr and Sonarr service status, statistics, and recent job activity. The dashboard uses an in-memory caching system for fast page loads and includes real-time refresh capabilities.

## Features

### 1. Service Status Cards

#### Radarr Card
- **Status Badge**: Shows connection status (Connected/Offline/Not Configured)
- **Total Movies**: Count of all movies in Radarr library
- **Missing Movies**: Count of monitored movies without files
- **Added by Listarr**: Total items added by Listarr from completed jobs

#### Sonarr Card
- **Status Badge**: Shows connection status (Connected/Offline/Not Configured)
- **Total Series**: Count of all series in Sonarr library
- **Missing Episodes**: Count of missing episodes (from `get_wanted()` totalRecords)
- **Added by Listarr**: Total items added by Listarr from completed jobs

### 2. Recent Jobs Table

Displays the last 5 executed jobs with:
- **Job Name**: Name of the list that was executed
- **Service**: Target service (RADARR or SONARR)
- **Executed At**: Formatted date (relative time for recent, formatted date for older)
- **Summary**: Job status summary with conditional formatting
  - Completed: "X added, Y skipped" (only shows non-zero values)
  - Failed: "Failed: [error message]"
  - Running: "Running..."
  - Pending: "Pending..."

### 3. Refresh Functionality

#### Manual Refresh
- **Refresh Button**: Located in page header
- **Loading States**: Shows "Refreshing..." with spinning icon
- **Button Disabled**: Prevents multiple simultaneous refreshes
- **Force Cache Refresh**: Uses `?refresh=true` parameter

#### Auto-Refresh
- **Interval**: 5 minutes (300,000 milliseconds)
- **Page Visibility**: Only refreshes when page is visible
- **Background**: Continues running when page is hidden (but doesn't refresh)
- **Cleanup**: Automatically stops on page unload

### 4. Caching System

#### Architecture
- **In-Memory Cache**: Global dictionary with thread-safe locking
- **Startup Initialization**: Cache populated at application startup
- **On-Demand Refresh**: Cache can be refreshed via query parameter
- **Thread Safety**: Uses `threading.Lock` for concurrent access

#### Cache Structure
```python
{
    "radarr": {
        "configured": bool,
        "status": "online" | "offline" | "not_configured",
        "version": str | None,
        "total_movies": int,
        "missing_movies": int,
        "added_by_listarr": int
    },
    "sonarr": {
        "configured": bool,
        "status": "online" | "offline" | "not_configured",
        "version": str | None,
        "total_series": int,
        "missing_episodes": int,
        "added_by_listarr": int
    }
}
```

#### Cache Lifecycle
1. **Application Startup**: `initialize_dashboard_cache(app)` called in `__init__.py`
2. **Page Load**: Dashboard fetches cached data (fast, no API calls)
3. **Manual Refresh**: User clicks refresh → cache refreshed → data updated
4. **Auto-Refresh**: Every 5 minutes → cache refreshed → data updated

### 5. "Added by Listarr" Calculation

#### Logic
- Queries all `List` records for the target service (RADARR or SONARR)
- Sums `items_added` from all `Job` records where:
  - `list_id` matches a list for the target service
  - `status == "completed"`
- Only counts completed jobs (failed/running/pending jobs excluded)

#### Implementation
```python
# Example for Radarr
radarr_lists = List.query.filter_by(target_service="RADARR").all()
if radarr_lists:
    list_ids = [lst.id for lst in radarr_lists]
    total_added = db.session.query(
        db.func.sum(Job.items_added)
    ).filter(
        Job.list_id.in_(list_ids),
        Job.status == "completed"
    ).scalar() or 0
    result["added_by_listarr"] = int(total_added)
```

## API Endpoints

### GET /api/dashboard/stats

Returns cached dashboard statistics.

**Query Parameters:**
- `refresh` (optional): If `true`, forces cache refresh before returning

**Response:**
```json
{
    "radarr": {
        "configured": true,
        "status": "online",
        "version": "4.5.2.7388",
        "total_movies": 4971,
        "missing_movies": 2804,
        "added_by_listarr": 170
    },
    "sonarr": {
        "configured": true,
        "status": "online",
        "version": "3.0.10.1567",
        "total_series": 250,
        "missing_episodes": 45,
        "added_by_listarr": 290
    }
}
```

### GET /api/dashboard/recent-jobs

Returns the last 5 executed jobs.

**Response:**
```json
{
    "jobs": [
        {
            "id": 1,
            "job_name": "Trending Movies",
            "service": "RADARR",
            "status": "completed",
            "started_at": "2024-01-15T10:00:00+00:00",
            "finished_at": "2024-01-15T10:05:00+00:00",
            "executed_at": "2024-01-15T10:05:00+00:00",
            "summary": "45 added, 5 skipped",
            "error_message": null
        }
    ]
}
```

## Error Handling

### Service Offline
- Status set to "offline"
- Counts set to 0 or "—"
- Version set to null
- "Added by Listarr" still calculated (from database)

### Decryption Errors
- Status set to "offline"
- Error logged
- Cache returns default values

### Missing Database Tables
- Status set to "not_configured" (not "offline")
- Graceful handling during test initialization
- Cache returns default values

### API Failures
- Partial failures handled gracefully
- Status may be "online" but counts may be 0
- Error logged for debugging

## Performance Considerations

### Caching Benefits
- **Fast Page Loads**: No API calls on initial page load
- **Reduced API Load**: Services only queried on refresh
- **Better UX**: Instant dashboard display

### Cache Refresh Strategy
- **Startup**: Cache populated once at application start
- **Manual**: User-triggered refresh (with loading states)
- **Auto**: Background refresh every 5 minutes
- **On-Demand**: Via `?refresh=true` query parameter

### Thread Safety
- All cache updates use `threading.Lock`
- Prevents race conditions in multi-threaded environments
- Safe for concurrent requests

## Frontend Implementation

### JavaScript Functions

#### Core Functions
- `fetchDashboardStats(refresh)` - Fetches stats from API
- `fetchRecentJobs()` - Fetches recent jobs
- `updateRadarrCard(data)` - Updates Radarr card UI
- `updateSonarrCard(data)` - Updates Sonarr card UI
- `updateJobsTable(jobs)` - Updates jobs table

#### Refresh Functions
- `refreshDashboard(isManual)` - Handles manual/auto refresh
- `startAutoRefresh()` - Starts 5-minute interval
- `stopAutoRefresh()` - Stops interval

#### Utility Functions
- `formatJobDate(dateStr)` - Formats dates (relative or absolute)
- `getStatusColorClass(status)` - Returns Tailwind CSS classes
- `updateStatusBadge(element, status)` - Updates status badge

### Event Listeners
- `DOMContentLoaded` - Initializes dashboard on page load
- `beforeunload` - Cleans up auto-refresh interval
- `visibilitychange` - Manages auto-refresh based on page visibility
- `click` on refresh button - Triggers manual refresh

## Testing

### Test Coverage
- **Route Tests**: 38 tests covering all dashboard endpoints
- **Integration Tests**: 18 tests covering end-to-end workflows
- **Total**: 56 dashboard-specific tests

### Key Test Areas
- Dashboard page rendering
- Service configuration and status
- Cache-based stats retrieval
- Cache refresh functionality
- "Added by Listarr" calculation
- Recent jobs display and formatting
- Error handling and graceful degradation
- HTML element presence and content

## Future Enhancements

### Potential Improvements
- Configurable auto-refresh interval
- Real-time updates via WebSockets
- Historical job statistics
- Service health monitoring
- Performance metrics display
- Export dashboard data

### Considerations
- Cache invalidation strategies
- Cache size limits
- Cache persistence across restarts
- More granular refresh options
