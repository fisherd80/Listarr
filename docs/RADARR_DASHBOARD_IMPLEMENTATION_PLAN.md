# Radarr Dashboard Card Implementation Plan

## Overview
This plan outlines the step-by-step implementation of the Radarr card on the dashboard. Each phase is designed to be testable and incremental, ensuring stability at each step.

## Prerequisites
- ✅ Dashboard restored to working state
- ✅ Config and Settings pages working
- ✅ Radarr service functions available (`get_system_status`, `get_movie_count`, `get_missing_movies_count`)
- ✅ Database accessible

---

## Phase 1: Backend API Endpoint (Radarr Only)

### Goal
Create a simple API endpoint that returns Radarr statistics.

### Steps

#### Step 1.1: Add Basic API Endpoint
**File:** `listarr/routes/dashboard_routes.py`

- Add imports for Radarr service functions
- Add imports for ServiceConfig and decrypt_data
- Create `/api/dashboard/stats` endpoint
- Return JSON with Radarr data structure:
  ```json
  {
    "radarr": {
      "configured": false,
      "status": "not_configured",
      "version": null,
      "total_movies": 0,
      "missing_movies": 0
    }
  }
  ```

**Test:** 
- Access `/api/dashboard/stats` in browser
- Should return JSON with `radarr.configured: false`
- No errors in Flask logs

#### Step 1.2: Check if Radarr is Configured
**File:** `listarr/routes/dashboard_routes.py`

- Query ServiceConfig for RADARR service
- Check if `api_key_encrypted` and `base_url` exist
- Set `radarr.configured = true` if configured
- Keep `status = "not_configured"` if not configured

**Test:**
- With Radarr NOT configured: `configured: false`, `status: "not_configured"`
- With Radarr configured: `configured: true`, `status: "not_configured"` (for now)

#### Step 1.3: Fetch Radarr System Status
**File:** `listarr/routes/dashboard_routes.py`

- If Radarr is configured:
  - Decrypt API key
  - Call `get_radarr_system_status(base_url, api_key)`
  - Set `status = "online"` if successful, `"offline"` if error
  - Set `version` from response
- Wrap in try/except for error handling

**Test:**
- With valid Radarr config: `status: "online"`, `version: "x.x.x"`
- With invalid Radarr config: `status: "offline"`
- With no Radarr config: `status: "not_configured"`

#### Step 1.4: Fetch Movie Count
**File:** `listarr/routes/dashboard_routes.py`

- If Radarr is configured and online:
  - Call `get_movie_count(base_url, api_key)`
  - Set `total_movies` from response
- Handle errors gracefully (set to 0)

**Test:**
- With valid Radarr: `total_movies: <actual_count>`
- With error: `total_movies: 0`, no crash

#### Step 1.5: Fetch Missing Movies Count
**File:** `listarr/routes/dashboard_routes.py`

- If Radarr is configured and online:
  - Call `get_missing_movies_count(base_url, api_key)`
  - Set `missing_movies` from response
- Handle errors gracefully (set to 0)

**Test:**
- With valid Radarr: `missing_movies: <actual_count>`
- With error: `missing_movies: 0`, no crash

**Phase 1 Complete When:**
- ✅ API endpoint returns correct Radarr data
- ✅ All three scenarios work (not configured, offline, online)
- ✅ No errors in Flask logs
- ✅ Can test via browser/Postman

---

## Phase 2: Frontend JavaScript (Radarr Only)

### Goal
Add JavaScript to fetch and display Radarr data.

### Steps

#### Step 2.1: Create Basic JavaScript File
**File:** `listarr/static/js/dashboard.js`

- Create file with basic structure
- Add `fetchDashboardStats()` function
- Make GET request to `/api/dashboard/stats`
- Log response to console
- Add script tag to `dashboard.html`

**Test:**
- Open browser console
- Should see API response logged
- No JavaScript errors

#### Step 2.2: Add Element IDs to HTML
**File:** `listarr/templates/dashboard.html`

- Add `id="radarr-status"` to status badge
- Add `id="radarr-total-movies"` to total movies element
- Add `id="radarr-missing-movies"` to missing movies element
- Keep static "Connected" text for now (will update dynamically later)

**Test:**
- Elements have correct IDs
- Page still renders correctly

#### Step 2.3: Create updateRadarrCard Function
**File:** `listarr/static/js/dashboard.js`

- Create `updateRadarrCard(data)` function
- Extract `data.radarr` from response
- Update status badge text based on `status`:
  - "online" → "Connected"
  - "offline" → "Offline"
  - "not_configured" → "Not Configured"
- Update status badge classes (colors)
- Call function after fetching stats

**Test:**
- Status badge updates correctly
- Colors change based on status
- Works for all three statuses

#### Step 2.4: Update Total Movies Display
**File:** `listarr/static/js/dashboard.js`

- In `updateRadarrCard()`, update `radarr-total-movies` element
- If `status === "online"` and `total_movies` exists: show count
- Otherwise: show "—"
- Handle undefined/null values

**Test:**
- Shows actual count when online
- Shows "—" when not configured/offline
- No JavaScript errors

#### Step 2.5: Update Missing Movies Display
**File:** `listarr/static/js/dashboard.js`

- In `updateRadarrCard()`, update `radarr-missing-movies` element
- If `status === "online"` and `missing_movies` exists: show count
- Otherwise: show "—"
- Handle undefined/null values

**Test:**
- Shows actual count when online
- Shows "—" when not configured/offline
- No JavaScript errors

#### Step 2.6: Add Loading State
**File:** `listarr/static/js/dashboard.js`

- Create `showRadarrLoadingState()` function
- Set status badge to "Loading..."
- Set metrics to "Loading..."
- Call on page load before fetching data

**Test:**
- Shows "Loading..." initially
- Updates to real data after fetch
- Handles errors gracefully

**Phase 2 Complete When:**
- ✅ Radarr card updates with real data
- ✅ Status badge shows correct status and colors
- ✅ Metrics show correct values or "—"
- ✅ Loading state works
- ✅ No JavaScript errors

---

## Phase 3: Error Handling & Edge Cases

### Goal
Ensure robust error handling for all scenarios.

### Steps

#### Step 3.1: Handle API Errors
**File:** `listarr/static/js/dashboard.js`

- Add try/catch in `fetchDashboardStats()`
- On error, call `updateRadarrCard()` with error state
- Show "Error" or "—" in UI
- Log errors to console

**Test:**
- Disconnect Radarr API
- Should show "Offline" status
- Should show "—" for metrics
- No JavaScript errors

#### Step 3.2: Handle Missing Data Fields
**File:** `listarr/static/js/dashboard.js`

- Check if `data.radarr` exists
- Check if fields exist before accessing
- Use fallback values (0, "—", "not_configured")
- Defensive coding throughout

**Test:**
- Malformed API response
- Missing fields
- Null values
- All handled gracefully

#### Step 3.3: Handle Decryption Errors
**File:** `listarr/routes/dashboard_routes.py`

- Wrap decrypt_data in try/except
- If decryption fails, set status to "offline"
- Log error but don't crash
- Return valid JSON response

**Test:**
- Corrupted encrypted key
- Should show "offline" status
- No server errors
- API still returns valid JSON

**Phase 3 Complete When:**
- ✅ All error scenarios handled
- ✅ No crashes on errors
- ✅ User-friendly error states
- ✅ Proper logging

---

## Phase 4: Polish & Optimization

### Goal
Add final touches and optimize performance.

### Steps

#### Step 4.1: Add Refresh Button Functionality
**File:** `listarr/static/js/dashboard.js`

- Add click handler to refresh button (if exists in HTML)
- Re-fetch stats on click
- Show loading state during refresh
- Disable button during refresh

**Test:**
- Click refresh button
- Data updates
- Button disabled during refresh
- Loading state shows

#### Step 4.2: Add Auto-Refresh (Optional)
**File:** `listarr/static/js/dashboard.js`

- Set interval to refresh every 5 minutes
- Clear interval on page unload
- Only refresh if page is visible (optional optimization)

**Test:**
- Data auto-updates after 5 minutes
- No memory leaks
- Works correctly

#### Step 4.3: Optimize API Calls
**File:** `listarr/routes/dashboard_routes.py`

- Use ThreadPoolExecutor for parallel API calls (status, count, missing)
- Add timeouts to prevent hanging
- Cache results if needed (future optimization)

**Test:**
- Faster response times
- No timeouts on slow connections
- Handles API delays gracefully

**Phase 4 Complete When:**
- ✅ Refresh functionality works
- ✅ Auto-refresh works (if implemented)
- ✅ Performance is acceptable
- ✅ No memory leaks

---

## Testing Checklist

After each phase, verify:

- [ ] Dashboard page loads without errors
- [ ] Config page still works
- [ ] Settings page still works
- [ ] API endpoint returns correct data
- [ ] JavaScript updates UI correctly
- [ ] Error scenarios handled gracefully
- [ ] No console errors
- [ ] No Flask server errors
- [ ] Works with Radarr configured
- [ ] Works with Radarr not configured
- [ ] Works with Radarr offline

---

## Rollback Plan

If any step causes issues:

1. **Immediate:** Revert the specific file to previous working state
2. **Test:** Verify config/settings pages still work
3. **Debug:** Check Flask logs and browser console
4. **Fix:** Address the specific issue before proceeding

---

## Notes

- **Sonarr card:** Leave as static placeholder until Radarr is fully working
- **Recent Jobs:** Already working, don't modify
- **Incremental:** Test after each step before moving to next
- **Documentation:** Update this plan as you progress

---

## Success Criteria

Radarr card implementation is complete when:

1. ✅ API endpoint returns accurate Radarr data
2. ✅ Status badge shows correct status (online/offline/not_configured)
3. ✅ Total Movies displays correct count or "—"
4. ✅ Missing Movies displays correct count or "—"
5. ✅ Loading states work correctly
6. ✅ Error handling is robust
7. ✅ No regressions in config/settings pages
8. ✅ Code is clean and maintainable

---

## Estimated Time

- Phase 1: 30-45 minutes
- Phase 2: 30-45 minutes
- Phase 3: 20-30 minutes
- Phase 4: 20-30 minutes

**Total:** ~2-3 hours for complete implementation
