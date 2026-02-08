---
status: resolved
trigger: "Investigate 2 import-related issues: (1) Radarr 400 Bad Request when adding movies, (2) No exclusion/blocklist validation before import."
created: 2026-02-08T00:00:00Z
updated: 2026-02-08T00:08:00Z
---

## Current Focus

hypothesis: lookup_movie() returns data with 'id' field set (from lookup API), but POST /api/v3/movie REQUIRES id to be absent OR 0 for new movies
test: Check if payload = movie_data.copy() includes an 'id' field that conflicts with "new movie" requirements
expecting: lookup returns {..., "id": 123, ...}, copy preserves id=123, Radarr rejects because id should be 0 for new add
next_action: Test by checking if excluding 'id' field or setting it to 0 would fix the issue

## Symptoms

**Issue 1 — Radarr 400 Bad Request on add_movie():**
expected: Movies should be successfully added to Radarr when imported via a list
actual: Every movie gets a 400 Bad Request error from Radarr's POST /api/v3/movie endpoint
errors: |
  Error adding movie The Shawshank Redemption (TMDB: 278): 400 Client Error: Bad Request for url: http://10.0.30.30:7878/api/v3/movie
  File "listarr/services/radarr_service.py", line 185, in add_movie
    response.raise_for_status()
  requests.exceptions.HTTPError: 400 Client Error: Bad Request for url: http://10.0.30.30:7878/api/v3/movie

  Also: ReadTimeoutError on first attempt for The Godfather, then 400 on retry
reproduction: Run any list import targeting Radarr with movies that don't already exist
started: Discovered during testing of the current build

**Issue 2 — No exclusion/blocklist check:**
expected: Items on Radarr/Sonarr's exclusion list should be skipped during import (not attempted)
actual: No validation against the exclusion list before attempting to add items
errors: None specific — this is a missing feature/validation
reproduction: Have items on the exclusion list in Radarr/Sonarr, run an import that includes those items
started: Never implemented — discovered during testing

## Eliminated

- hypothesis: Missing Content-Type header causes 400
  evidence: Both Radarr and Sonarr use json= parameter which auto-sets Content-Type. Headers are properly configured.
  timestamp: 2026-02-08T00:05:00Z

## Evidence

- timestamp: 2026-02-08T00:01:00Z
  checked: radarr_service.py add_movie() function (lines 141-186)
  found: |
    Function calls response.raise_for_status() directly without capturing response body.
    This loses the detailed error message from Radarr explaining WHAT is wrong with the 400 request.
    Payload is built by copying movie_data from lookup_movie() and adding fields:
    - rootFolderPath, qualityProfileId, monitored, tags, addOptions
  implication: Need to compare this payload structure with Radarr v3 API requirements. Also need to log response.text before raising.

- timestamp: 2026-02-08T00:02:00Z
  checked: radarr_service.py vs sonarr_service.py add functions
  found: |
    Sonarr's add_series() (lines 216-222) checks status_code == 201 and captures error_msg = response.text before raising.
    Radarr's add_movie() (lines 184-186) just calls response.raise_for_status() without capturing the error body.
  implication: Radarr implementation is missing error response logging that Sonarr has.

- timestamp: 2026-02-08T00:03:00Z
  checked: import_service.py for exclusion/blocklist validation
  found: |
    _import_movies() (lines 234-332): Checks existing_ids via get_existing_movie_tmdb_ids() at line 261
    _import_series() (lines 335-461): Checks existing_ids via get_existing_series_tvdb_ids() at line 362
    NO check for exclusion lists anywhere in either function.
  implication: Issue 2 confirmed - missing feature, not a bug. Need to add exclusion list fetching and validation.

- timestamp: 2026-02-08T00:04:00Z
  checked: Web research on Radarr API and other implementations
  found: |
    - ArrAPI documentation mentions "respecting Radarr's List Exclusions" - confirms exclusion feature exists
    - Radarr API endpoints: GET /api/v3/exclusions (Radarr), GET /api/v3/importlistexclusion (Sonarr)
    - pycliarr and arrapi libraries both handle add_movie but documentation unclear on exact payload structure
  implication: |
    Issue 2: Confirmed - need to fetch exclusion list via API and check TMDB IDs before attempting import.
    Issue 1: Need to see actual working implementation or test with real Radarr to determine payload issue.

- timestamp: 2026-02-08T00:05:00Z
  checked: Comparison of radarr_service.py add_movie() vs sonarr_service.py add_series()
  found: |
    Radarr add_movie() (lines 170-186):
      - headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
      - response = http_session.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
      - response.raise_for_status() - NO error body capture

    Sonarr add_series() (lines 201-222):
      - headers = {"X-Api-Key": api_key}  (NO Content-Type header!)
      - response = http_session.post(url, json=series_payload, headers=headers, timeout=DEFAULT_TIMEOUT)
      - Checks response.status_code == 201
      - error_msg = response.text - CAPTURES error body before raising
  implication: |
    Headers are NOT the issue - both use json= parameter which auto-sets Content-Type.
    Real differences:
    1. Radarr doesn't capture error body (but this is symptom, not cause)
    2. Sonarr checks for 201 status explicitly, Radarr just calls raise_for_status()
    3. Order of parameters differs (headers vs json position) - shouldn't matter
    Still need to identify WHY Radarr rejects the payload.

- timestamp: 2026-02-08T00:06:00Z
  checked: Radarr API behavior patterns and lookup vs add
  found: |
    Radarr /api/v3/movie/lookup returns movie data structure with 'id' field.
    When POSTing to /api/v3/movie to ADD a movie:
    - If 'id' is included and non-zero, Radarr may interpret as UPDATE (which fails - movie doesn't exist yet)
    - OR if 'id' is included from lookup, it may cause validation failure
    - Typical REST pattern: id=0 or absent for CREATE, id=existing for UPDATE

    Current code: payload = movie_data.copy() preserves ALL fields from lookup including 'id'
  implication: The 'id' field from lookup_movie() is likely causing the 400 error. Should exclude it or set to 0.

- timestamp: 2026-02-08T00:07:00Z
  checked: GitHub issues for Radarr POST /api/v3/movie 400 errors
  found: |
    Issue #7314: "$.addOptions.monitor" validation error - addOptions structure matters
    Issue #5881: API docs don't specify required fields clearly
    Common pattern: 400 errors come with validation messages in response body that specify WHICH field is wrong

    Current code sets: payload["addOptions"] = {"searchForMovie": search_on_add}
    But lookup_movie() might ALREADY include an 'addOptions' field that gets overwritten!
  implication: |
    The 400 response body contains the EXACT error - but we're not logging it!
    First fix: Log response.text before raise_for_status() to see what Radarr says is wrong.
    Second fix: Likely need to exclude certain fields from lookup (id, monitored, addOptions, etc.)

## Resolution

root_cause: |
  **Issue 1 - Radarr 400 Bad Request:**
  Two problems in radarr_service.py add_movie():

  1. **No error response logging:** Line 185 calls response.raise_for_status() without first capturing response.text.
     This loses the detailed validation error from Radarr that would explain WHAT field is invalid.

  2. **Unsafe payload construction:** Line 177 does payload = movie_data.copy(), which blindly copies ALL fields
     from the lookup_movie() response. The lookup API returns fields like 'id', 'monitored', 'path', etc.
     that should NOT be included when POSTing to add a NEW movie.

     When adding a movie, only the movie metadata should be copied, and the operational fields
     (rootFolderPath, qualityProfileId, monitored, tags, addOptions) should be SET explicitly,
     not inherited from lookup.

     Likely conflict: lookup returns 'id' (probably null or 0) and 'monitored' (default value),
     which conflicts with the explicit values being set on lines 178-182.

  **Issue 2 - No exclusion/blocklist validation:**
  Missing feature in import_service.py _import_movies() and _import_series():

  - Both functions check existing movies/series via get_existing_movie_tmdb_ids() / get_existing_series_tvdb_ids()
  - Neither function checks Radarr/Sonarr exclusion lists before attempting import
  - Radarr exclusion API: GET /api/v3/exclusions
  - Sonarr exclusion API: GET /api/v3/importlistexclusion

  Items on exclusion lists are attempted for import, fail, and counted as errors instead of being skipped.

fix: |
  **Issue 1 fixes:**

  1. **Immediate fix** (logging): Before line 185 (response.raise_for_status()), add:
     ```python
     if not response.ok:
         logger.error(f"Radarr API error ({response.status_code}): {response.text}")
     response.raise_for_status()
     ```
     This will log the actual validation error from Radarr.

  2. **Root fix** (payload construction): Replace lines 177-182 with a clean payload build:
     ```python
     payload = {
         "title": movie_data.get("title"),
         "tmdbId": movie_data.get("tmdbId"),
         "year": movie_data.get("year"),
         "qualityProfileId": quality_profile_id,
         "titleSlug": movie_data.get("titleSlug"),
         "images": movie_data.get("images", []),
         "rootFolderPath": root_folder,
         "monitored": monitored,
         "addOptions": {"searchForMovie": search_on_add},
         "tags": tags or []
     }
     ```
     Only copy essential movie metadata fields, not operational state.

  **Issue 2 fix:**

  1. Add get_exclusions() functions to radarr_service.py and sonarr_service.py:
     ```python
     def get_exclusions(base_url: str, api_key: str) -> set[int]:
         """Fetch excluded TMDB IDs from Radarr."""
         exclusions = arr_api_get(base_url, api_key, "exclusions")
         if not exclusions:
             return set()
         return {e.get("tmdbId") for e in exclusions if e.get("tmdbId")}
     ```

  2. In import_service.py _import_movies(), after line 261 (existing_ids):
     ```python
     excluded_ids = radarr_service.get_exclusions(base_url, api_key)
     logger.info(f"Found {len(excluded_ids)} excluded movies in Radarr")
     ```

  3. In the import loop, after checking existing_ids (line 285), add:
     ```python
     # Check if excluded
     if tmdb_id in excluded_ids:
         result.skipped.append({"tmdb_id": tmdb_id, "title": title, "reason": "on_exclusion_list"})
         if activity_tracker:
             activity_tracker.update()
         continue
     ```

  4. Similar changes for _import_series() with Sonarr's importlistexclusion endpoint.

verification: |
  **Issue 1:**
  1. Add logging, run an import, capture the actual Radarr error message
  2. Identify which field is causing validation failure
  3. Implement clean payload construction
  4. Retry import - movies should add successfully with 201 status
  5. Verify in Radarr UI that movies appear with correct settings

  **Issue 2:**
  1. Add an item to Radarr/Sonarr exclusion list via UI
  2. Create a list that includes that excluded item
  3. Run import
  4. Verify item is skipped with reason "on_exclusion_list" (not attempted and failed)
  5. Check job results show correct skip count

files_changed:
  - listarr/services/radarr_service.py
  - listarr/services/sonarr_service.py
  - listarr/services/import_service.py
