# Phase 4: Import Automation Engine - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build reliable import system that sends TMDB items to Radarr/Sonarr with proper error handling. System imports movies to Radarr and TV shows to Sonarr with configured quality profiles, root folders, and tags. Job execution framework and scheduling are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Import behavior
- Process all items at once (no batching)
- Small delay between API calls (100-500ms) to be gentle on services
- Retry 2-3 times on failure for an item, then log and move on (no per-item retry loop)
- Block duplicate runs of the same list (prevent concurrent imports of same list)

### Duplicate handling
- Detect duplicates by TMDB ID match
- Skip and log items that already exist in Radarr/Sonarr
- Include skip reason in log (e.g., "already in Radarr")
- Track skips separately from adds: "Added: 5, Skipped: 3, Failed: 1"

### Error reporting
- Store errors in database only (no separate log files)
- Simple user-friendly error messages (not full technical details)
- Categorize errors by type (API error, already exists, invalid data, etc.)
- "Partial success" status for jobs where some items succeed and some fail
- Special "service error" status when Radarr/Sonarr is completely down (update dashboard accordingly)
- Keep job history forever (no auto-cleanup)
- No retry UI for failed items (user re-runs whole list if needed)
- No tracking of repeat failures across job runs

### Import feedback
- Jobs page shows history of executed list imports
- Summary shows three counts: Added, Skipped, Failed
- Expandable dropdown shows raw log text in scrollable text box
- Log format: simple lines like "[Added] Movie Name (2024)" (no timestamps)
- Dashboard shows recent job status summary
- Lists page only has manual "Run Now" button (no inline job feedback)

### Claude's Discretion
- Exact delay timing between API calls
- Error category definitions
- Dashboard summary format and styling
- Log text formatting details

</decisions>

<specifics>
## Specific Ideas

- Log display in Jobs page should be a scrollable text box showing raw log content
- Dashboard should surface job status, particularly service errors
- Job history is permanent storage, no cleanup needed
- The import should work reliably with the existing Radarr/Sonarr service integrations already in the codebase
- Per-list import settings (quality profile, root folder, tags, monitored, search on add) were implemented in Phase 2 and should be respected when importing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-import-automation-engine*
*Context gathered: 2026-01-24*
