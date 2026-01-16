# Dashboard Historical Jobs Implementation Plan

## Overview
Implement the "Recent Jobs" section on the dashboard to display the last 5 executed list jobs with their status, execution details, and summary information.

## Current State
- ✅ HTML table structure exists in `dashboard.html` (lines 120-192)
- ✅ Database models exist: `Job` and `List` models
- ✅ Tests exist for `/api/dashboard/recent-jobs` endpoint
- ❌ Backend API endpoint not implemented
- ❌ Frontend JavaScript not implemented
- ❌ Jobs table currently shows placeholder rows

## Database Schema

### Job Model (`listarr/models/jobs_model.py`)
```python
- id: Integer (primary key)
- list_id: Integer (foreign key to lists.id)
- status: String (pending/running/failed/completed)
- started_at: TZDateTime
- finished_at: TZDateTime
- items_found: Integer
- items_added: Integer
- items_skipped: Integer
- error_message: Text
```

### List Model (`listarr/models/lists_model.py`)
```python
- id: Integer (primary key)
- name: String (job name)
- target_service: String (RADARR/SONARR)
```

## Implementation Plan

---

## Phase 1: Backend API Endpoint

### Goal
Create API endpoint to fetch recent jobs data.

### Step 1.1: Create Recent Jobs API Endpoint
**File:** `listarr/routes/dashboard_routes.py`

**Implementation:**
- Add route: `GET /api/dashboard/recent-jobs`
- Query last 5 completed/failed jobs (ordered by `finished_at` DESC, or `started_at` DESC if no `finished_at`)
- Join with `List` table to get job name and service
- Return JSON structure matching test expectations:
  ```json
  {
    "jobs": [
      {
        "id": int,
        "job_name": str,  // from List.name
        "service": str,   // from List.target_service
        "status": str,    // pending/running/failed/completed
        "started_at": str, // ISO format datetime
        "finished_at": str | null, // ISO format datetime
        "summary": str,   // e.g., "45 added, 5 skipped (50 found)"
        "error_message": str | null
      }
    ]
  }
  ```

**Query Logic:**
```python
jobs = Job.query.join(List).order_by(
    Job.finished_at.desc().nullslast(),
    Job.started_at.desc()
).limit(5).all()
```

**Summary Format:**
- If completed: `"{items_added} added, {items_skipped} skipped ({items_found} found)"`
- If failed: `"Failed: {error_message}"` (truncate if too long)
- If running: `"Running..."`
- If pending: `"Pending..."`

**Test:**
- Empty database returns `{"jobs": []}`
- With jobs: returns last 5 jobs with correct structure
- Jobs ordered by most recent first

---

## Phase 2: Frontend JavaScript

### Goal
Fetch and display jobs data in the dashboard table.

### Step 2.1: Create Fetch Jobs Function
**File:** `listarr/static/js/dashboard.js`

**Implementation:**
- Add `fetchRecentJobs()` function
- Make GET request to `/api/dashboard/recent-jobs`
- Return promise with jobs data
- Handle errors gracefully (return empty array)

**Test:**
- Function exists and makes correct API call
- Error handling works

### Step 2.2: Create Update Jobs Table Function
**File:** `listarr/static/js/dashboard.js`

**Implementation:**
- Add `updateJobsTable(jobs)` function
- Find table body element (or create container)
- Clear existing rows
- For each job:
  - Create table row (`<tr>`)
  - Add cells: Job Name, Service, Executed At, Summary
  - Format dates (relative time or formatted date)
  - Add status-based styling (colors for completed/failed/running)
  - Handle empty state (show message if no jobs)
- Append rows to table

**Date Formatting:**
- Use relative time: "2 hours ago", "3 days ago"
- Or formatted: "Jan 15, 2024 10:00 AM"
- Fallback to ISO string if date parsing fails

**Status Styling:**
- Completed: Green text/icon
- Failed: Red text/icon
- Running: Yellow/blue text/icon
- Pending: Gray text/icon

**Test:**
- Table updates with job data
- Empty state shows correctly
- Date formatting works
- Status colors applied

### Step 2.3: Add Table Container ID
**File:** `listarr/templates/dashboard.html`

**Implementation:**
- Add `id="recent-jobs-table-body"` to `<tbody>` element
- Or wrap table body in container with ID for easier targeting

**Test:**
- Element has correct ID
- JavaScript can find element

### Step 2.4: Integrate with Dashboard Initialization
**File:** `listarr/static/js/dashboard.js`

**Implementation:**
- Call `fetchRecentJobs()` in `initDashboard()`
- Update table after fetching
- Show loading state (optional)
- Include in refresh functionality (manual and auto-refresh)

**Test:**
- Jobs load on page load
- Jobs refresh with dashboard refresh
- Loading states work

---

## Phase 3: Error Handling & Edge Cases

### Goal
Ensure robust error handling for all scenarios.

### Step 3.1: Handle API Errors
**File:** `listarr/static/js/dashboard.js`

**Implementation:**
- Try/catch in `fetchRecentJobs()`
- On error, show empty state or error message
- Log errors to console
- Don't crash dashboard if jobs fail to load

**Test:**
- API errors handled gracefully
- Dashboard still works if jobs endpoint fails

### Step 3.2: Handle Missing Data Fields
**File:** `listarr/static/js/dashboard.js`

**Implementation:**
- Validate job data structure
- Handle missing/null fields:
  - `finished_at` can be null (running jobs)
  - `error_message` can be null
  - `job_name` fallback to "Unknown Job"
  - `service` fallback to "Unknown"
- Defensive coding throughout

**Test:**
- Missing fields handled
- Null values don't crash
- Fallback values used

### Step 3.3: Handle Empty State
**File:** `listarr/static/js/dashboard.js`

**Implementation:**
- Show message when no jobs: "No jobs executed yet"
- Or show placeholder row with message
- Style appropriately

**Test:**
- Empty state displays correctly
- Message is user-friendly

---

## Phase 4: Polish & Optimization

### Goal
Add final touches and optimize display.

### Step 4.1: Date Formatting Enhancement
**File:** `listarr/static/js/dashboard.js`

**Implementation:**
- Use relative time for recent jobs (< 24 hours): "2 hours ago"
- Use formatted date for older jobs: "Jan 15, 2024"
- Consider timezone handling
- Add tooltip with full timestamp

**Test:**
- Dates display correctly
- Relative time updates appropriately

### Step 4.2: Status Badge Styling
**File:** `listarr/static/js/dashboard.js` or `dashboard.html`

**Implementation:**
- Add status badges/indicators in Summary column
- Use Tailwind classes for colors:
  - Completed: `text-green-600`
  - Failed: `text-red-600`
  - Running: `text-yellow-600` or `text-blue-600`
  - Pending: `text-gray-600`

**Test:**
- Status colors are clear
- Badges are readable

### Step 4.3: Summary Formatting
**File:** `listarr/static/js/dashboard.js`

**Implementation:**
- Format summary text clearly
- Truncate long error messages (e.g., first 100 chars + "...")
- Add icons for status (optional)

**Test:**
- Summary is readable
- Long messages truncated
- Formatting is consistent

### Step 4.4: Include in Cache (Optional)
**File:** `listarr/services/dashboard_cache.py`

**Implementation:**
- Consider caching recent jobs (but they change frequently)
- Or keep as separate endpoint (recommended - jobs change often)
- Jobs should be fetched fresh on each dashboard load

**Decision:**
- **Recommendation:** Keep jobs endpoint separate (not cached)
- Jobs change frequently and should be real-time
- Cache is for service stats that change less frequently

---

## Testing Checklist

### Backend Tests
- [ ] Empty database returns empty array
- [ ] Returns last 5 jobs ordered correctly
- [ ] Includes job name from List
- [ ] Includes service from List
- [ ] Summary formatted correctly for each status
- [ ] Handles null finished_at (running jobs)
- [ ] Handles null error_message
- [ ] Date formatting in ISO format

### Frontend Tests
- [ ] Jobs table updates on page load
- [ ] Jobs table updates on refresh
- [ ] Empty state displays correctly
- [ ] Date formatting works
- [ ] Status colors applied
- [ ] Error handling works
- [ ] Missing fields handled
- [ ] Table responsive on mobile

### Integration Tests
- [ ] End-to-end: Page load → Jobs display
- [ ] Refresh button updates jobs
- [ ] Auto-refresh includes jobs (optional)
- [ ] Multiple jobs display correctly
- [ ] Jobs with different statuses display correctly

---

## File Changes Summary

### New Code
- `listarr/routes/dashboard_routes.py`: Add `/api/dashboard/recent-jobs` endpoint
- `listarr/static/js/dashboard.js`: Add jobs fetching and table update functions

### Modified Files
- `listarr/templates/dashboard.html`: Add ID to table body (if needed)

### No Changes Needed
- `listarr/models/jobs_model.py`: Already has required fields
- `listarr/models/lists_model.py`: Already has required fields

---

## Implementation Order

1. **Phase 1**: Backend API Endpoint
   - Implement `/api/dashboard/recent-jobs`
   - Test with existing test suite
   - Validate response structure

2. **Phase 2**: Frontend JavaScript
   - Add fetch function
   - Add table update function
   - Integrate with dashboard initialization

3. **Phase 3**: Error Handling
   - Add error handling
   - Handle edge cases
   - Test error scenarios

4. **Phase 4**: Polish
   - Date formatting
   - Status styling
   - Summary formatting

---

## Success Criteria

✅ Jobs display in dashboard table  
✅ Last 5 jobs shown (most recent first)  
✅ Job name, service, date, and summary displayed  
✅ Status colors/indicators clear  
✅ Empty state handled gracefully  
✅ Error handling robust  
✅ Dates formatted appropriately  
✅ Works with refresh button  
✅ Responsive on mobile devices  

---

## Notes

- Jobs endpoint should NOT be cached (jobs change frequently)
- Consider pagination if more than 5 jobs needed in future
- Consider adding "View All Jobs" link to `/jobs` page
- Date formatting can be enhanced with libraries like `date-fns` or `moment.js` (optional)
- Status icons can be added using SVG or icon library (optional)
