# UAT Issues: Phase 2 Plan 3

**Tested:** 2026-01-16
**Source:** .planning/phases/02-list-creation-wizard/02-03-SUMMARY.md
**Tester:** User via /gsd:verify-work

## Open Issues

### UAT-001: Live preview endpoint returns network error

**Discovered:** 2026-01-16
**Phase/Plan:** 02-03
**Severity:** Major
**Feature:** TMDB Live Preview
**Description:** When changing filters in custom wizard Step 2 (e.g., checking Action genre), the preview area shows "Network Error - please try again" instead of TMDB results.
**Expected:** Preview area should show loading indicator, then display up to 5 movies with title, year, and rating
**Actual:** Shows "Network Error - please try again"
**Repro:**
1. Go to Lists page
2. Click "+ Custom List"
3. Select "Movies" card
4. Click Next to go to Step 2
5. Check "Action" genre checkbox
6. Observe preview area

### UAT-002: Preset preview also fails with network error

**Discovered:** 2026-01-16
**Phase/Plan:** 02-03
**Severity:** Major
**Feature:** TMDB Live Preview (Preset mode)
**Description:** Preset wizard Step 2 also shows network error instead of trending movies preview.
**Expected:** Preview area should show trending movies from TMDB
**Actual:** Shows "Network Error - please try again"
**Repro:**
1. Go to Lists page
2. Click "Trending Movies" preset card
3. Click Next to go to Step 2
4. Observe preview area

## Resolved Issues

[None yet]

---

*Phase: 02-list-creation-wizard*
*Plan: 03*
*Tested: 2026-01-16*
