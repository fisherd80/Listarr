# Roadmap

**Project:** Listarr
**Milestone:** v1.0 - Automated Media Discovery
**Created:** 2026-01-12

## Objective

Build automated media discovery and import that just works - fresh content flows into Radarr/Sonarr automatically based on TMDB lists, running reliably 24/7 without intervention.

## Phases

### Phase 1: List Management System

**Goal:** Create UI and backend for managing TMDB lists with full CRUD operations

**Deliverable:** Users can create, view, edit, delete, and enable/disable lists through the web interface

**Verification:**
- Create a new TMDB trending list through the UI
- Edit the list configuration
- Disable and re-enable the list
- Delete the list
- All operations persist correctly in the database

---

### Phase 2: List Creation Wizard

**Goal:** Replace basic list form with multi-step wizard featuring presets, discovery filters, per-list import settings, and live TMDB preview

**Deliverable:** Users can create lists through a guided 4-step wizard with preset templates, see live preview of TMDB results, and configure per-list import settings that override service defaults

**Wizard Steps:**
1. **Type** - Movies (→Radarr) or TV Shows (→Sonarr)
2. **Filters** - Genre, year range, min rating with live TMDB preview
3. **Import Settings** - Quality profile, root folder, tags, monitored, search on add (pre-filled from service defaults, all editable)
4. **Schedule** - Run frequency

**Presets:** Trending Movies, Trending TV, Popular Movies, Popular TV (populate wizard for review)

**Verification:**
- Create a list using "Trending Movies" preset, verify wizard pre-populates correctly
- Create a custom discovery list with genre + year filters, verify live preview shows matching TMDB results
- Override import settings on a list, verify they differ from service defaults
- Create list without overriding import settings, verify it uses service defaults
- Edit an existing list through the wizard, verify all fields load correctly

---

### Phase 3: TMDB Caching Layer (Complete)

**Goal:** Implement smart caching to respect TMDB API rate limits and improve performance

**Deliverable:** TMDB API responses are cached with appropriate TTLs, preventing rate limit violations

**Status:** Complete (2026-01-18) - 2/2 plans executed
- 03-01: TMDB cache service with TTL-based caching
- 03-02: Integrated caching into wizard preview

**Verification:**
- Fetch the same list twice within cache window and verify only one API call is made
- Wait for cache expiration and verify fresh data is fetched
- Check logs to confirm cache hit/miss behavior
- Verify rate limiting protection prevents API overuse

---

### Phase 3.1: Update Config Page Tags (Complete)

**Goal:** Add tag storage to the Config page with create-if-missing pattern for Radarr/Sonarr tags

**Deliverable:** Config page allows users to configure and persist tags for both Radarr and Sonarr services using text input (not dropdown)

**Status:** Complete (2026-01-24) - 1/1 plans executed
- 03.1-01: Tag storage with create-if-missing pattern

**Verification:**
- Tags can be configured on the Config page for Radarr
- Tags can be configured on the Config page for Sonarr
- Tag selections persist correctly in the database
- Tags are created in Radarr/Sonarr if they don't exist

---

### Phase 4: Import Automation Engine

**Goal:** Build reliable import system that sends TMDB items to Radarr/Sonarr with proper error handling

**Deliverable:** System can import movies to Radarr and TV shows to Sonarr with configured quality profiles and root folders, handling errors gracefully

**Plans:** 3 plans in 2 waves

Plans:
- [x] 04-01-PLAN.md — TVDB translation + Radarr import methods
- [x] 04-02-PLAN.md — Sonarr import methods + ImportResult dataclass
- [ ] 04-03-PLAN.md — Import orchestration service + test endpoint

**Verification:**
- Import a movie to Radarr and verify it appears with correct quality profile
- Import a TV show to Sonarr and verify it appears with correct settings
- Test import of already-existing item and verify graceful handling
- Test import with invalid settings and verify error reporting
- Check error logs for proper error capture

---

### Phase 5: Manual Trigger UI

**Goal:** Add manual trigger capability to run any list on-demand from the UI

**Deliverable:** Users can click a button to immediately execute any list import job using the existing `/lists/<id>/run` endpoint

**Plans:** 2 plans in 2 waves

Plans:
- [ ] 05-01-PLAN.md — Run button UI + synchronous handler with toast feedback
- [ ] 05-02-PLAN.md — Status endpoint + localStorage tracking + polling for async state

**Verification:**
- Click "Run Now" button on a list and verify job executes immediately
- Verify UI shows job status feedback (running -> completed)
- Check that results are displayed to the user
- Verify UI prevents duplicate triggers while job is running

---

### Phase 6: Job Execution Framework

**Goal:** Create background job processing system with execution tracking and history

**Deliverable:** Jobs can be queued, executed, tracked, and their history (success/failure) is recorded and displayed

**Verification:**
- Queue a list import job and verify it executes
- View job execution history in the dashboard
- Verify failed jobs are logged with error details
- Check that job status updates correctly (pending -> running -> completed/failed)
- Confirm job history persists across application restarts

---

### Phase 7: Scheduler System

**Goal:** Implement cron-based scheduler for automated list refresh on schedule

**Deliverable:** Lists can be configured with cron schedules and execute automatically without manual intervention

**Verification:**
- Configure a list to run every 5 minutes
- Wait and verify the job executes automatically at the scheduled time
- Check job history shows scheduled executions
- Disable the list and verify scheduled jobs stop
- Re-enable and verify scheduling resumes

---

### Phase 8: Service Settings Caching & Background Refresh

**Goal:** Refactor caching from Radarr/Sonarr to collect settings and figures on launch, with background refresh to prevent data rot

**Deliverable:** Service settings (quality profiles, root folders, tags) are cached on application startup and refreshed periodically in the background, reducing API calls and improving responsiveness

**Verification:**
- Start the application and verify Radarr/Sonarr settings are fetched on launch
- Check that cached settings are used for list creation wizard without additional API calls
- Wait for background refresh interval and verify settings are updated
- Modify settings in Radarr/Sonarr and verify they appear after next refresh
- Verify application remains responsive even if services are temporarily unavailable

---

### Phase 9: User Authentication

**Goal:** Implement user login system to secure the web interface

**Deliverable:** Users must authenticate to access the application, with session management and logout capability

**Research Required:**
- Existing users table structure in database
- Settings page placeholder for user management
- Flask-Login or similar authentication approach

**Verification:**
- Unauthenticated users are redirected to login page
- Valid credentials allow access to application
- Invalid credentials show appropriate error
- Session persists across page navigation
- Logout clears session and redirects to login
- Protected routes reject unauthenticated requests

---

### Phase 10: Migrate from pyarr to Direct API

**Goal:** Replace pyarr library with direct Radarr/Sonarr API calls for full control and feature support

**Deliverable:** All Radarr and Sonarr API interactions use direct HTTP requests instead of pyarr, enabling access to all API features including tags on series add

**Research Required:**
- Radarr API documentation: https://radarr.video/docs/api/
- Sonarr API documentation: https://sonarr.tv/docs/api/

**Verification:**
- All existing Radarr functionality works (test connection, fetch profiles/folders/tags, add movie)
- All existing Sonarr functionality works (test connection, fetch profiles/folders/tags, add series with tags)
- Tags are properly applied when adding series to Sonarr
- Error handling matches or improves upon pyarr behavior
- All existing tests pass with new implementation

---

## Milestone Complete When

All phases delivered and verified:
- List management UI fully functional
- List creation wizard with presets, filters, import settings, and live preview
- TMDB caching respects rate limits
- Import automation reliably sends items to Radarr/Sonarr
- Manual triggers allow on-demand execution from UI
- Job execution framework tracks all operations
- Scheduler runs lists automatically on cron schedules
- Service settings cached on launch with background refresh
- User authentication secures web interface
- Direct API calls replace pyarr for full feature support

**Success criteria:** User can configure a trending movies list, schedule it to run daily, and verify that new movies automatically appear in Radarr without any manual intervention.

---

*Roadmap created: 2026-01-12*
*Last updated: 2026-01-25*
*Phases: 10 (4 complete, 6 remaining)*
*Depth: Standard (3-5 plans per phase)*
