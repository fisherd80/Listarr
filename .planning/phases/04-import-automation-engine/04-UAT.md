---
status: complete
phase: 04-import-automation-engine
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03 in progress]
started: 2026-01-24T12:00:00Z
updated: 2026-01-24T14:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Import Endpoint Returns JSON
expected: POST /lists/1/run returns JSON with success, list_id, list_name, and result fields. If list doesn't exist, returns 404 with error message.
result: pass

### 2. Inactive List Rejected
expected: POST /lists/<inactive_list_id>/run returns 400 error with message "List 'X' is not active"
result: pass

### 3. Import Movies to Radarr
expected: Triggering import on a Radarr list fetches TMDB items and adds new movies to Radarr. Response shows added count > 0 (if new movies exist) or skipped count > 0 (if all already exist).
result: issue
reported: "partially works, The list is set to get 100 entries, yet only 20 was sent add request"
severity: major

### 4. Duplicate Movies Skipped
expected: When importing a list where all movies already exist in Radarr, response shows skipped array with reason "already_exists" for each movie. No errors, no duplicates added.
result: issue
reported: "the 2 movies missing were not added, error returned saying bad request - Invalid Path: '5' (root folder passed as ID instead of path)"
severity: blocker

### 5. Import Settings Applied
expected: Movies are added to Radarr with the correct quality profile, root folder, and tags as configured in list overrides or service defaults.
result: skipped
reason: cannot test until have successful import into radarr to check the imported entries

### 6. Import TV Shows to Sonarr
expected: Triggering import on a Sonarr list translates TMDB IDs to TVDB IDs and adds new series to Sonarr. Response shows added/skipped counts.
result: skipped
reason: need to fix Radarr path issue first, likely same issue affects Sonarr (same API pattern)

### 7. Result Summary Accurate
expected: Response result.summary contains accurate counts: total = added_count + skipped_count + failed_count
result: pass

## Summary

total: 7
passed: 3
issues: 2
pending: 0
skipped: 2

## Gaps

- truth: "List limit setting controls how many TMDB items are fetched and imported"
  status: failed
  reason: "User reported: partially works, The list is set to get 100 entries, yet only 20 was sent add request"
  severity: major
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Movies are added to Radarr with correct root folder path"
  status: failed
  reason: "User reported: 2 movies failed with Bad Request - Invalid Path: '5' (root folder passed as ID instead of path string)"
  severity: blocker
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
