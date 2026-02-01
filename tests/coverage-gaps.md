# Coverage Gap Analysis - Phase 6.2

**Generated:** 2026-02-01
**Baseline Coverage:** 52% overall (2409 statements, 1068 missed)
**All Tests Passing:** 415/415

## Coverage Summary

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Overall Coverage | 52% | 85%+ | 33% |
| Critical Paths (Phase 6.2) | 28% avg | 90%+ | 62% |

## Priority Areas

### Priority 1: Lists Routes (Phase 6.2 Wizard & Preview)
**File:** `listarr/routes/lists_routes.py`
**Current Coverage:** 16% (67/385 statements covered, 318 missed)
**Missing Lines:** 25-27, 38-39, 54-76, 80-221, 232-245, 260-343, 356-373, 396-511, 533-635, 651-711, 737-738

**Critical Phase 6.2 Functions (Uncovered):**
- `list_wizard()` - Lines 80-221 (completely uncovered)
  - Top rated preset handling
  - Region-aware wizard initialization
  - Limit options (25, 50, 100, 250, 500, MAX)

- `wizard_preview()` - Lines 232-245 (completely uncovered)
  - Top rated preset preview
  - Region filtering in preview
  - Cache-backed TMDB calls

- `edit_list()` - Lines 356-373 (completely uncovered)
  - Form validation with new limit options
  - Legacy limit migration (10/20 -> 25)

**Impact:** CRITICAL - Wizard is the primary UI for Phase 6.2 features

---

### Priority 2: TMDB Cache (Phase 6.2 Top Rated & Region)
**File:** `listarr/services/tmdb_cache.py`
**Current Coverage:** 14% (30/175 statements covered, 145 missed)
**Missing Lines:** 40-46, 59-65, 80-97, 112-128, 143-160, 174-190, 205-222, 236-252, 268-286, 302-320, 334-350, 364-380, 390-391, 422-427

**Critical Phase 6.2 Functions (Uncovered):**
- `get_top_rated_movies_cached()` - Lines 236-252 (completely uncovered)
  - Region-aware cache key generation
  - 4-hour TTL using _popular_cache

- `get_top_rated_tv_cached()` - Lines 268-286 (completely uncovered)
  - Region-aware cache key generation
  - 4-hour TTL using _popular_cache

- `_get_tmdb_region()` - Lines 390-391 (completely uncovered)
  - ServiceConfig tmdb_region retrieval
  - Default to None for worldwide

- Region-aware cache key generation:
  - Popular movies with region suffix - Lines 112-128
  - Discover movies with region suffix - Lines 174-190
  - Discover TV with region suffix - Lines 205-222

**Impact:** CRITICAL - Cache layer is essential for performance and region filtering

---

### Priority 3: TMDB Service (Phase 6.2 Top Rated API)
**File:** `listarr/services/tmdb_service.py`
**Current Coverage:** 71% (118/165 statements covered, 47 missed)
**Missing Lines:** 63-73, 147, 154-156, 197, 204-206, 221-232, 246-256, 288, 318, 327, 328->331, 333-335, 381-383

**Critical Phase 6.2 Functions (Uncovered):**
- `get_top_rated_movies()` - Lines 221-232 (completely uncovered)
  - TMDB API: /movie/top_rated
  - Region parameter support
  - Pagination support

- `get_top_rated_tv()` - Lines 246-256 (completely uncovered)
  - TMDB API: /tv/top_rated
  - No region parameter (TMDB limitation)
  - Pagination support

**Impact:** HIGH - Direct API calls for top rated content

---

### Priority 4: Import Service (Phase 6.2 Top Rated List Types)
**File:** `listarr/services/import_service.py`
**Current Coverage:** 9% (29/223 statements covered, 194 missed)
**Missing Lines:** 46, 51, 56, 60, 91-130, 153-227, 250-322, 345-433, 447-517

**Critical Phase 6.2 Functions (Uncovered):**
- `_fetch_tmdb_items()` - Lines 153-227 (completely uncovered)
  - Handling for `top_rated_movies` list type
  - Handling for `top_rated_tv` list type
  - Region-aware TMDB cache calls

**Impact:** HIGH - Import execution for top rated lists

---

## Specific Missing Lines by Phase 6.2 Feature

### Feature: Top Rated Presets

**Backend Functions (0% coverage):**
- `tmdb_service.get_top_rated_movies()` - Lines 221-232
- `tmdb_service.get_top_rated_tv()` - Lines 246-256
- `tmdb_cache.get_top_rated_movies_cached()` - Lines 236-252
- `tmdb_cache.get_top_rated_tv_cached()` - Lines 268-286
- `import_service._fetch_tmdb_items()` - Lines 153-227 (includes top_rated handling)

**UI/Routes (0% coverage):**
- `lists_routes.list_wizard()` - Lines 80-221 (includes top_rated preset handling)
- `lists_routes.wizard_preview()` - Lines 232-245 (includes top_rated preview)

---

### Feature: Region Filtering

**Backend Functions (0% coverage):**
- `tmdb_cache._get_tmdb_region()` - Lines 390-391
- `tmdb_cache.get_popular_movies_cached()` - Lines 112-128 (region-aware cache keys)
- `tmdb_cache.get_top_rated_movies_cached()` - Lines 236-252 (region-aware cache keys)
- `tmdb_cache.discover_movies_cached()` - Lines 174-190 (region-aware cache keys)
- `tmdb_cache.discover_tv_cached()` - Lines 205-222 (region-aware cache keys)

**UI/Routes (0% coverage):**
- `lists_routes.list_wizard()` - Lines 80-221 (region parameter handling)
- `lists_routes.wizard_preview()` - Lines 232-245 (region-aware preview)

---

### Feature: Limit Options (25, 50, 100, 250, 500, MAX)

**UI/Routes (0% coverage):**
- `lists_routes.list_wizard()` - Lines 80-221 (new limit dropdown)
- `lists_routes.edit_list()` - Lines 356-373 (limit validation, legacy migration)
- `lists_routes.wizard_preview()` - Lines 232-245 (limit in preview)

---

## Branch Coverage Gaps

### Uncovered Branches (Phase 6.2 Related)

**lists_routes.py:**
- All conditional branches in wizard, preview, edit (118 branches total, 0 covered)

**tmdb_cache.py:**
- Region suffix logic (region != None vs None)
- Cache hit/miss branches
- 42 branches total, 0 covered

**tmdb_service.py:**
- Region parameter handling (6 branch misses)
- Error handling for top_rated endpoints
- Lines: 328->331

**import_service.py:**
- List type conditionals for top_rated_movies/top_rated_tv
- 90 branches total, 0 covered

---

## Test Generation Priorities

### Group 1: TMDB Service Functions (Plan 02)
Target: 90%+ coverage of Phase 6.2 functions

**Tests to Generate:**
1. `test_get_top_rated_movies()`
   - Default call (no region)
   - With region parameter (US, GB)
   - With pagination (page 2, 3)
   - Error handling (API failure)
   - Empty API key handling

2. `test_get_top_rated_tv()`
   - Default call
   - Pagination support
   - Error handling
   - Empty API key handling

**Lines to Cover:** 221-256 (35 statements)

---

### Group 2: TMDB Cache Functions (Plan 03)
Target: 90%+ coverage of Phase 6.2 functions

**Tests to Generate:**
1. `test_get_top_rated_movies_cached()`
   - Cache miss -> fetch from TMDB
   - Cache hit -> return cached
   - Region US -> cache key suffix `:US`
   - Region None -> cache key suffix `:WW`
   - TTL verification (4 hours)

2. `test_get_top_rated_tv_cached()`
   - Cache miss -> fetch from TMDB
   - Cache hit -> return cached
   - Cache key suffix `:WW` (no region for TV top_rated)
   - TTL verification (4 hours)

3. `test__get_tmdb_region()`
   - ServiceConfig.tmdb_region exists -> return value
   - ServiceConfig.tmdb_region is None -> return None
   - No ServiceConfig -> return None

4. `test_region_aware_cache_keys()`
   - `get_popular_movies_cached()` with region
   - `discover_movies_cached()` with region
   - `discover_tv_cached()` with region
   - Cache key format: `{base_key}:{region_code}` or `{base_key}:WW`

**Lines to Cover:** 112-128, 174-190, 205-222, 236-286, 390-391 (145+ statements)

---

### Group 3: Import Service Top Rated Handling (Plan 04 - Future)
Target: 85%+ coverage of import execution

**Tests to Generate:**
1. `test__fetch_tmdb_items_top_rated_movies()`
   - List type `top_rated_movies`
   - Calls `tmdb_cache.get_top_rated_movies_cached()`
   - Respects limit parameter
   - Handles pagination

2. `test__fetch_tmdb_items_top_rated_tv()`
   - List type `top_rated_tv`
   - Calls `tmdb_cache.get_top_rated_tv_cached()`
   - Respects limit parameter
   - Handles pagination

**Lines to Cover:** 153-227 (75 statements)

---

### Group 4: Wizard Routes (Plan 05 - Future)
Target: 85%+ coverage of wizard flows

**Tests to Generate:**
1. `test_list_wizard_top_rated_presets()`
   - Preset selection for top_rated_movies
   - Preset selection for top_rated_tv
   - Default name generation
   - Default limit (100)

2. `test_wizard_preview_top_rated()`
   - Preview for top_rated_movies
   - Preview for top_rated_tv
   - Region parameter in preview
   - Cache-backed preview calls

3. `test_edit_list_limit_options()`
   - New limit dropdown (25, 50, 100, 250, 500, MAX)
   - Legacy limit migration (10 -> 25, 20 -> 25)
   - Validation with new limits

**Lines to Cover:** 80-245, 356-373 (200+ statements)

---

## Summary

**Immediate Focus (Plans 02-03):**
- TMDB service top_rated functions: 35 statements
- TMDB cache top_rated + region functions: 145 statements
- Total Phase 6.2 backend: ~180 statements

**Expected Coverage Improvement:**
- Current: 52% overall
- After Plans 02-03: ~60% overall
- After all Phase 6.2 test generation: ~70% overall

**Critical Success Metrics:**
- Phase 6.2 module coverage: 90%+ (target)
- Overall coverage: 85%+ (target)
- Zero Phase 6.2 regressions
