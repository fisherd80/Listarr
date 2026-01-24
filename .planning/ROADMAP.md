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

### Phase 5: Job Execution Framework

**Goal:** Create background job processing system with execution tracking and history

**Deliverable:** Jobs can be queued, executed, tracked, and their history (success/failure) is recorded and displayed

**Verification:**
- Queue a list import job and verify it executes
- View job execution history in the dashboard
- Verify failed jobs are logged with error details
- Check that job status updates correctly (pending -> running -> completed/failed)
- Confirm job history persists across application restarts

---

### Phase 6: Scheduler System

**Goal:** Implement cron-based scheduler for automated list refresh on schedule

**Deliverable:** Lists can be configured with cron schedules and execute automatically without manual intervention

**Verification:**
- Configure a list to run every 5 minutes
- Wait and verify the job executes automatically at the scheduled time
- Check job history shows scheduled executions
- Disable the list and verify scheduled jobs stop
- Re-enable and verify scheduling resumes

---

### Phase 7: Manual Trigger UI

**Goal:** Add manual trigger capability to run any list on-demand from the UI

**Deliverable:** Users can click a button to immediately execute any list import job

**Verification:**
- Click "Run Now" button on a list and verify job executes immediately
- Verify UI shows job status (running -> completed)
- Check that manually triggered jobs appear in job history
- Test triggering multiple lists simultaneously
- Verify UI prevents duplicate triggers while job is running

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

## Milestone Complete When

All phases delivered and verified:
- List management UI fully functional
- List creation wizard with presets, filters, import settings, and live preview
- TMDB caching respects rate limits
- Import automation reliably sends items to Radarr/Sonarr
- Job execution framework tracks all operations
- Scheduler runs lists automatically on cron schedules
- Manual triggers allow on-demand execution
- Service settings cached on launch with background refresh

**Success criteria:** User can configure a trending movies list, schedule it to run daily, and verify that new movies automatically appear in Radarr without any manual intervention.

---

*Roadmap created: 2026-01-12*
*Phases: 8*
*Depth: Standard (3-5 plans per phase)*
