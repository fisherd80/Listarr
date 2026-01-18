# Phase 4: Import Automation Engine - Research

**Researched:** 2026-01-18
**Domain:** Python import engine using pyarr for Radarr/Sonarr integration
**Confidence:** HIGH

<research_summary>
## Summary

Researched the pyarr library and Radarr/Sonarr APIs for building a reliable import automation engine. The existing codebase already uses pyarr 5.x for read operations; this phase adds write operations (add_movie, add_series).

Key finding: pyarr provides straightforward methods for adding media, but lacks built-in duplicate handling. The recommended approach is "pre-flight check" - fetch existing library items before attempting adds, then categorize results into added/skipped/failed buckets.

TMDB-to-Sonarr requires ID translation: TMDB provides external_ids endpoint that includes tvdb_id, which Sonarr requires for series lookup. The existing tmdb_service.py already implements get_imdb_id_from_tmdb() which uses the same external_ids pattern.

**Primary recommendation:** Build import service with pre-flight duplicate detection (fetch library once, check against it) rather than catch-and-handle approach. Log skipped items as INFO not WARNING since duplicates are expected behavior.
</research_summary>

<standard_stack>
## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyarr | >=5.0.0 | Radarr/Sonarr API client | Already used in project, well-maintained |
| tmdbv3api | 1.9.0 | TMDB API client | Already used in project, provides external_ids |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cachetools | >=5.3.0 | TTL caching | Already used for TMDB caching, can cache library lists |
| logging | stdlib | Structured logging | Import results need clear logging |

### No New Dependencies Needed
The existing stack covers all import requirements. pyarr handles Radarr/Sonarr communication, tmdbv3api provides TMDB lookups and ID translation.

**Verification:** pyarr >=5.0.0 confirmed in requirements.txt, provides:
- `RadarrAPI.add_movie()` - add single movie
- `RadarrAPI.lookup_movie()` - search by term, TMDB ID, or IMDB ID
- `RadarrAPI.get_movie()` - fetch existing library
- `SonarrAPI.add_series()` - add single series
- `SonarrAPI.lookup_series()` - search by term or TVDB ID
- `SonarrAPI.get_series()` - fetch existing library
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Service Structure
```
listarr/services/
├── import_service.py      # Main import orchestration
├── radarr_service.py      # Existing - add import methods
└── sonarr_service.py      # Existing - add import methods
```

### Pattern 1: Pre-flight Duplicate Detection
**What:** Fetch library once at start of import batch, check each item against it
**When to use:** Always - more efficient than catch-and-handle for batch imports
**Example:**
```python
def import_movies_batch(list_id: int, tmdb_ids: list[int], settings: dict) -> ImportResult:
    """Import batch of movies with pre-flight duplicate detection."""
    # Pre-flight: get existing library once
    existing_tmdb_ids = {m.get('tmdbId') for m in radarr.get_movie()}

    result = ImportResult()

    for tmdb_id in tmdb_ids:
        # Skip if already in library
        if tmdb_id in existing_tmdb_ids:
            result.skipped.append({'tmdb_id': tmdb_id, 'reason': 'already_exists'})
            continue

        # Lookup and add
        try:
            movie_data = radarr.lookup_movie(f"tmdb:{tmdb_id}")
            if not movie_data:
                result.failed.append({'tmdb_id': tmdb_id, 'reason': 'not_found_in_radarr'})
                continue

            radarr.add_movie(
                movie=movie_data[0],
                root_dir=settings['root_folder'],
                quality_profile_id=settings['quality_profile_id'],
                monitored=settings['monitored'],
                search_for_movie=settings['search_on_add'],
                tags=settings.get('tags', [])
            )
            result.added.append({'tmdb_id': tmdb_id, 'title': movie_data[0].get('title')})
        except Exception as e:
            result.failed.append({'tmdb_id': tmdb_id, 'error': str(e)})

    return result
```

### Pattern 2: TMDB-to-TVDB ID Translation for Sonarr
**What:** Sonarr requires TVDB IDs, not TMDB IDs. Use TMDB external_ids endpoint.
**When to use:** All TV show imports
**Example:**
```python
def get_tvdb_id_from_tmdb(tmdb_id: int, api_key: str) -> int | None:
    """Get TVDB ID for a TMDB TV show using external_ids endpoint."""
    _init_tmdb(api_key)
    tv = TV()
    external_ids = tv.external_ids(tmdb_id)
    return external_ids.get('tvdb_id')
```

### Pattern 3: Result Categorization
**What:** Every import returns structured result with added/skipped/failed categories
**When to use:** All batch imports - enables clear logging and UI feedback
**Example:**
```python
@dataclass
class ImportResult:
    """Structured result from import operation."""
    added: list[dict] = field(default_factory=list)      # Successfully added items
    skipped: list[dict] = field(default_factory=list)    # Already existed, intentionally skipped
    failed: list[dict] = field(default_factory=list)     # Errors during import

    @property
    def total(self) -> int:
        return len(self.added) + len(self.skipped) + len(self.failed)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return (len(self.added) + len(self.skipped)) / self.total
```

### Pattern 4: Settings Resolution
**What:** Resolve import settings from list overrides or service defaults
**When to use:** Before import - each list can override service defaults
**Example:**
```python
def resolve_import_settings(list_obj: List, service_config: ServiceConfig) -> dict:
    """Resolve import settings, preferring list overrides over service defaults."""
    return {
        'quality_profile_id': list_obj.override_quality_profile or service_config.default_quality_profile_id,
        'root_folder': list_obj.override_root_folder or service_config.default_root_folder,
        'monitored': list_obj.override_monitored if list_obj.override_monitored is not None else service_config.default_monitored,
        'search_on_add': list_obj.override_search_on_add if list_obj.override_search_on_add is not None else service_config.default_search_on_add,
        'tags': [list_obj.override_tag_id] if list_obj.override_tag_id else [],
    }
```

### Anti-Patterns to Avoid
- **Catch-and-ignore for duplicates:** Don't rely on API errors for duplicate detection - pre-check is more efficient and gives better logging
- **No result tracking:** Always return structured results, never void functions for imports
- **Mixing concerns:** Keep TMDB fetching separate from Radarr/Sonarr import logic
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Radarr/Sonarr API calls | Custom requests code | pyarr library | Already handles auth, error codes, versioning |
| TMDB ID lookup | Direct API calls | tmdbv3api + existing tmdb_service.py | Already implemented, handles initialization |
| TVDB ID translation | Manual API calls | tmdbv3api external_ids() | One line: `tv.external_ids(tmdb_id).get('tvdb_id')` |
| Retry logic | Custom retry wrapper | pyarr handles connection errors | Library already manages timeouts |

**Key insight:** The heavy lifting is already done by pyarr and tmdbv3api. The import service is orchestration logic that connects existing pieces - TMDB results to Radarr/Sonarr adds with proper settings resolution.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Sonarr Requires TVDB ID, Not TMDB ID
**What goes wrong:** Import fails because Sonarr lookup_series() expects TVDB ID
**Why it happens:** TMDB lists return TMDB IDs, but Sonarr uses TVDB internally
**How to avoid:** Always translate TMDB ID to TVDB ID before Sonarr operations
**Warning signs:** "Series not found" errors despite series existing on TMDB

### Pitfall 2: API Rate Limiting During Large Imports
**What goes wrong:** Radarr/Sonarr API returns 429 errors during bulk imports
**Why it happens:** Rapid-fire add requests overwhelm local service
**How to avoid:** Consider small delays between requests or batch lookup first
**Warning signs:** Intermittent failures on large list imports

### Pitfall 3: Missing External IDs
**What goes wrong:** Some TMDB items don't have TVDB/IMDB IDs
**Why it happens:** TMDB doesn't always have mappings to other databases
**How to avoid:** Handle None gracefully, log as "failed - no TVDB ID available"
**Warning signs:** Silent failures where items simply don't import

### Pitfall 4: Settings ID vs Path Confusion
**What goes wrong:** Import uses wrong quality profile or root folder
**Why it happens:** List stores override as ID but API might need path (root_folder)
**How to avoid:** Check pyarr method signatures - root_dir is PATH string, quality_profile_id is INT
**Warning signs:** "Quality profile not found" or "Root folder not found" errors

### Pitfall 5: Boolean vs Integer in Database
**What goes wrong:** monitored/search_on_add values not applied correctly
**Why it happens:** List model stores some booleans as Integer (0/1) for NULL support
**How to avoid:** Convert explicitly: `bool(override_monitored)` when override is not None
**Warning signs:** All imports use defaults despite overrides being set
</common_pitfalls>

<code_examples>
## Code Examples

### pyarr add_movie Method Signature
```python
# Source: pyarr documentation
def add_movie(
    self,
    movie: dict,                          # From lookup_movie() result
    root_dir: str,                         # Path like "/movies"
    quality_profile_id: int,               # Integer ID
    monitored: bool = True,
    search_for_movie: bool = True,
    monitor: str = "movieOnly",            # "movieOnly", "movieAndCollections", "none"
    minimum_availability: str = "announced",  # "announced", "inCinemas", "released"
    tags: list[int] = [],
) -> dict
```

### pyarr add_series Method Signature
```python
# Source: pyarr documentation
def add_series(
    self,
    series: dict,                          # From lookup_series() result
    quality_profile_id: int,
    language_profile_id: int,              # Sonarr-specific, required
    root_dir: str,                         # Path like "/tv"
    season_folder: bool = True,
    monitored: bool = True,
    ignore_episodes_with_files: bool = False,
    ignore_episodes_without_files: bool = False,
    search_for_missing_episodes: bool = False,
) -> dict
```

### Lookup by TMDB ID (Radarr)
```python
# Source: pyarr documentation
# Radarr accepts tmdb: prefix for direct TMDB ID lookup
radarr = RadarrAPI(host_url=base_url, api_key=api_key)
movie_results = radarr.lookup_movie(term=f"tmdb:{tmdb_id}")
# Returns list of matching movies (usually 1 for ID lookup)
```

### Lookup by TVDB ID (Sonarr)
```python
# Source: pyarr documentation
sonarr = SonarrAPI(host_url=base_url, api_key=api_key)
series_results = sonarr.lookup_series(id_=tvdb_id)
# Returns list of matching series
```

### pyarr Exceptions to Handle
```python
# Source: pyarr/exceptions.py
from pyarr.exceptions import (
    PyarrBadRequest,       # 400 - Invalid request body
    PyarrResourceNotFound, # 404 - Movie/series not found
    PyarrConnectionError,  # Connection failed
    PyarrUnauthorizedError, # 401 - Bad API key
)
```
</code_examples>

<sota_updates>
## State of the Art (2025-2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual API requests | pyarr library | 2021+ | Simplified API interaction, proper error handling |
| Catch exceptions for duplicates | Pre-flight check existing library | Best practice | More efficient, better logging, fewer API calls |
| arrapi for batch operations | pyarr single operations | pyarr is simpler | arrapi returns (added, exists, invalid) but pyarr is already in project |

**Current best practices:**
- Use pyarr 5.x for all Radarr/Sonarr API interactions
- Pre-fetch existing library before batch imports
- Return structured results (added/skipped/failed)
- Log skipped items as INFO, failed as ERROR

**Not needed:**
- arrapi library - provides batch handling but project already uses pyarr
- Custom retry logic - pyarr handles basic connection errors
- Background task queues (Celery) - simple synchronous import is sufficient for this phase
</sota_updates>

<open_questions>
## Open Questions

1. **Language Profile for Sonarr**
   - What we know: add_series() requires language_profile_id parameter
   - What's unclear: Is this stored in service config? Need to check Sonarr v4 compatibility
   - Recommendation: Fetch language profiles same as quality profiles, store default in service config

2. **Rate Limiting Strategy**
   - What we know: Large imports could overwhelm local Radarr/Sonarr
   - What's unclear: What's the practical limit before issues occur?
   - Recommendation: Start without throttling, add if needed based on real-world testing

3. **Partial Success Handling**
   - What we know: Batch imports can have mixed results (some added, some failed)
   - What's unclear: How should partial success be reported to user?
   - Recommendation: Return full ImportResult, let UI decide how to present
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [pyarr documentation](https://docs.totaldebug.uk/pyarr/) - add_movie, add_series, lookup methods
- [pyarr source code](https://github.com/totaldebug/pyarr) - verified method signatures and error handling
- Existing project code - radarr_service.py, sonarr_service.py, tmdb_service.py

### Secondary (MEDIUM confidence)
- [Radarr API docs](https://radarr.video/docs/api/) - POST /movie endpoint patterns
- [Servarr Wiki](https://wiki.servarr.com/) - troubleshooting and error codes
- [TMDB API](https://developer.themoviedb.org/) - external_ids endpoint for TVDB translation

### Tertiary (LOW confidence - needs validation)
- GitHub issues for pyarr/Radarr - error handling edge cases (verify during implementation)
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: pyarr library for Radarr/Sonarr API
- Ecosystem: tmdbv3api (already in project), pyarr exceptions
- Patterns: Pre-flight duplicate detection, result categorization, settings resolution
- Pitfalls: TVDB ID translation, boolean storage, API rate limiting

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project and working
- Architecture: HIGH - patterns derived from official pyarr documentation
- Pitfalls: HIGH - documented in library issues and Servarr wiki
- Code examples: HIGH - from official pyarr documentation

**Research date:** 2026-01-18
**Valid until:** 2026-02-18 (30 days - pyarr stable, Radarr/Sonarr APIs versioned)
</metadata>

---

*Phase: 04-import-automation-engine*
*Research completed: 2026-01-18*
*Ready for planning: yes*
