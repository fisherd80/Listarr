# Phase 2: List Creation Wizard - Context

**Gathered:** 2026-01-16
**Status:** Ready for planning

<vision>
## How This Should Work

The lists page is the entry point. At the top, users see a row of **preset cards** (Trending Movies, Trending TV, Popular Movies, Popular TV) plus a **Create Custom List** card. Below that sits the table of existing lists.

**Preset-focused experience**: Most users (80%) will click a preset card and be done quickly. Custom discovery is there for power users, but it's not the primary path.

**Preset flow**:
1. Click preset card → wizard opens
2. See filters (read-only) — shows what the preset does, but not editable
3. Configure import settings (quality profile, root folder, tags, monitored, search on add) — pre-filled from service defaults
4. Set schedule
5. Done — list created

**Custom list flow**:
1. Click "Create Custom List" card → wizard opens
2. Choose type (Movies → Radarr, TV → Sonarr)
3. Configure filters (genre, year range, min rating) with live TMDB preview
4. Configure import settings
5. Set schedule
6. Done

The wizard has a clear **stepper/progress bar** showing "Step 1 of 4" throughout. It feels quick and guided — get through it fast with smart defaults.

</vision>

<essential>
## What Must Be Nailed

- **Preset experience** — Quick path from clicking a preset card to having a working list. This is 80% of usage and must feel effortless.
- **Card-based entry** — Presets and custom option displayed as clean cards (icon + label) above the lists table. Visual, scannable, inviting.
- **Per-list import settings with fallback** — Each list can override service defaults; if not overridden, uses service defaults dynamically at import time.

</essential>

<boundaries>
## What's Out of Scope

- **Advanced TMDB filters** — No keywords, cast/crew, certification, language, region filters. Keep it simple: genre, year range, min rating only. Can expand later.
- **Poster previews on cards** — Cards are icon + label only, no TMDB imagery on the cards themselves.
- **Complex scheduling UI** — Basic schedule configuration is fine; advanced cron builder can come later.

</boundaries>

<specifics>
## Specific Ideas

- **Card layout**: Preset cards in a row, "Create Custom List" card with same style but "+" icon
- **Stepper**: Clear visual progress — "Step 1 of 4", "Step 2 of 4", etc.
- **Preset filters read-only**: When using a preset, show what filters are applied (informational) but user can't edit them
- **Live preview**: For custom lists, show sample TMDB results as user configures filters
- **Import settings step**: Shows all *arr options (quality profile, root folder, tags, monitored, search on add) pre-filled from MediaImportSettings, all editable

</specifics>

<notes>
## Additional Context

This phase replaces the basic list creation modal from Phase 1 with a proper wizard experience. The existing lists table remains but gets the card section added above it.

The wizard needs to work for both create and edit flows — editing an existing list should open the wizard with current values populated.

4 presets to start: Trending Movies, Trending TV, Popular Movies, Popular TV. More can be added later.

</notes>

---

*Phase: 02-list-creation-wizard*
*Context gathered: 2026-01-16*
