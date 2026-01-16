# UAT Issues: Phase 2 Plan 3

**Tested:** 2026-01-16
**Source:** .planning/phases/02-list-creation-wizard/02-03-SUMMARY.md
**Tester:** User via /gsd:verify-work

## Open Issues

[None]

## Resolved Issues

### UAT-001: Live preview endpoint returns network error

**Discovered:** 2026-01-16
**Resolved:** 2026-01-16
**Phase/Plan:** 02-03
**Severity:** Major
**Feature:** TMDB Live Preview
**Description:** When changing filters in custom wizard Step 2 (e.g., checking Action genre), the preview area shows "Network Error - please try again" instead of TMDB results.
**Root Cause:** Multiple issues with tmdbv3api AsObj handling:
1. Missing CSRF token in fetch request
2. AsObj doesn't support Python slice notation
3. AsObj items require dict-style access, not getattr
4. Both response and `.results` attribute are AsObj, need list() conversion
**Fix:** Commits 0231a1a, 5268e9f, ad2d543, 1588fa0, 6620152

### UAT-002: Preset preview also fails with network error

**Discovered:** 2026-01-16
**Resolved:** 2026-01-16
**Phase/Plan:** 02-03
**Severity:** Major
**Feature:** TMDB Live Preview (Preset mode)
**Description:** Preset wizard Step 2 also shows network error instead of trending movies preview.
**Root Cause:** Same as UAT-001, plus missing preview UI container in preset mode template
**Fix:** Same commits as UAT-001, plus 9cd6146 (added preview to preset mode)

---

*Phase: 02-list-creation-wizard*
*Plan: 03*
*Tested: 2026-01-16*
*All issues resolved: 2026-01-16*
