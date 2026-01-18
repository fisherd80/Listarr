# Phase 4: Import Automation Engine - Context

**Gathered:** 2026-01-18
**Status:** Ready for planning

<vision>
## How This Should Work

Background processing that runs jobs and imports items automatically based on list configuration. When a list is triggered (manually for now, scheduled later), it fetches TMDB results and imports them to the appropriate service (Radarr for movies, Sonarr for TV).

Duplicates (items already in library) should be logged but not cause alerts or errors - just track them for history and move on quietly. The system should be invisible when working correctly.

</vision>

<essential>
## What Must Be Nailed

All three of these are equally critical:

- **Reliability** - Rock-solid imports that never fail silently or corrupt data
- **Correct settings** - Items imported with the right quality profile, root folder, and tags every time (using list overrides or service defaults)
- **Visibility** - Clear logging of what was imported, what was skipped (already exists), and what failed

</essential>

<boundaries>
## What's Out of Scope

- **No scheduling** - Manual trigger only for this phase. Automated cron-based scheduling comes in Phase 6
- Job execution UI comes in Phase 5/7
- This phase focuses on the import engine/service layer

</boundaries>

<specifics>
## Specific Ideas

No specific requirements - open to standard approaches.

The import should work reliably with the existing Radarr/Sonarr service integrations already in the codebase.

</specifics>

<notes>
## Additional Context

This phase connects the TMDB list results (from Phase 2 wizard, cached in Phase 3) to actual imports into Radarr/Sonarr. It's the core automation that makes Listarr useful.

Per-list import settings (quality profile, root folder, tags, monitored, search on add) were implemented in Phase 2 and should be respected when importing.

</notes>

---

*Phase: 04-import-automation-engine*
*Context gathered: 2026-01-18*
