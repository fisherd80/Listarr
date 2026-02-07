# Phase 8: Architecture Concerns for Phase 9

**Created:** 2026-02-05
**Updated:** 2026-02-05 (Flask Complexity Reviewer findings added)
**Context:** Issues identified during API consolidation research + comprehensive complexity review
**Action Required:** Evaluate and address in Phase 9 (Code Quality & Refactoring)

## Summary

During Phase 8's API consolidation, several architecture concerns were identified. A subsequent complexity review validated these concerns and identified additional tactical issues. This document consolidates both sources for Phase 9 planning.

**Overall Assessment:** Good architecture, moderate technical debt, ready for deployment with optional refactoring.

---

## High Priority (Fix First)

### 1. N+1 Query in Dashboard Recent Jobs

**Source:** Complexity Reviewer (NEW)

**Observation:** Fetches 5 jobs, then queries List table up to 5 times in a loop.

**Location:** `listarr/routes/dashboard_routes.py` lines 91-114

**Impact:** Performance degradation under load.

**Fix:**
```python
from sqlalchemy.orm import joinedload

jobs = (
    Job.query
    .options(joinedload(Job.list))  # Eager load relationship
    .filter(Job.completed_at.isnot(None))
    .order_by(Job.completed_at.desc())
    .limit(5)
    .all()
)
```

**Requires:** Add relationship to Job model:
```python
class Job(db.Model):
    list = db.relationship('List', backref='jobs', lazy='select')
```

**Effort:** 1 hour | **Risk:** Low

---

### 2. JavaScript Missing HTTP Status Checks

**Source:** Complexity Reviewer (NEW)

**Observation:** Frontend fetch calls don't validate HTTP status codes before processing JSON.

**Impact:** Silent failures when API returns error status codes.

**Fix:** Add status checks to all fetch calls:
```javascript
fetch('/api/endpoint')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
```

**Files Affected:**
- `listarr/static/js/dashboard.js`
- `listarr/static/js/jobs.js`
- `listarr/static/js/lists.js`
- `listarr/static/js/wizard.js`
- `listarr/static/js/schedule.js`

**Effort:** 2 hours | **Risk:** Low

---

### 3. Dashboard Stats Duplication

**Source:** Complexity Reviewer (NEW)

**Observation:** `_calculate_radarr_stats()` and `_calculate_sonarr_stats()` are 111 lines each with 95%+ identical code.

**Location:** `listarr/services/dashboard_cache.py` lines 54-164 and 167-278

**Impact:** Bug fixes must be duplicated. If one is updated and not the other, behavior diverges silently.

**Fix:**
```python
def _calculate_service_stats(service: str) -> Dict:
    """Calculate stats for Radarr or Sonarr.

    Args:
        service: "RADARR" or "SONARR"
    """
    is_radarr = service == "RADARR"

    # Select appropriate service functions
    if is_radarr:
        get_status = get_radarr_system_status
        get_count = get_movie_count
        get_missing = get_missing_movies_count
    else:
        get_status = get_sonarr_system_status
        get_count = get_series_count
        get_missing = get_missing_episodes_count

    # ... rest of logic using selected functions
```

**Effort:** 3 hours | **Risk:** Low

---

### 4. Duplicate Code: Radarr vs Sonarr Services

**Source:** Phase 8 Research + Complexity Reviewer (CONFIRMED)

**Observation:** `radarr_service.py` (360 lines) and `sonarr_service.py` (412 lines) are 90%+ identical.

**Examples:**
- validate_*_api_key() - identical logic, different endpoint
- get_quality_profiles() - identical logic, different endpoint
- get_root_folders() - identical logic, different endpoint
- get_tags() - identical logic, different endpoint
- create_or_get_tag_id() - identical normalization logic

**Recommendation:** Create shared helper module:
```python
# arr_service.py
def _arr_api_get(base_url: str, api_key: str, endpoint: str) -> dict:
    url = f"{normalize_url(base_url)}/api/v3/{endpoint}"
    headers = {"X-Api-Key": api_key}
    response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

def get_quality_profiles(base_url: str, api_key: str) -> list:
    try:
        profiles = _arr_api_get(base_url, api_key, "qualityprofile")
        return [{"id": p["id"], "name": p["name"]} for p in profiles]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching quality profiles: {e}")
        return []
```

**Effort:** 4-6 hours | **Risk:** Medium (must test both services thoroughly)

---

## Medium Priority (Fix When Touching Area)

### 5. Oversized Route Files

**Source:** Phase 8 Research + Complexity Reviewer (EXPANDED)

**Observation:** Route files have grown beyond single-responsibility.

**Current Sizes:**
- `listarr/routes/lists_routes.py` - **1007 lines** (largest)
- `listarr/routes/config_routes.py` - **913 lines**

**Suggested Split for lists_routes.py:**

| New File | Contains | Est. Lines |
|----------|----------|------------|
| `lists_routes.py` | Page routes (`lists_page`, `edit_list`) | ~200 |
| `lists_api_routes.py` | API routes (`get_lists_api`, `run_list_import`, `get_list_status`) | ~150 |
| `wizard_routes.py` | Wizard routes (`list_wizard`, `wizard_preview`, `wizard_submit`) | ~500 |

**Suggested Split for config_routes.py:**

| New File | Contains | Est. Lines |
|----------|----------|------------|
| `config_routes.py` | Main config page, shared logic | ~300 |
| `radarr_config_routes.py` | Radarr-specific routes | ~300 |
| `sonarr_config_routes.py` | Sonarr-specific routes | ~300 |

**Effort:** 3-4 hours per file | **Risk:** Medium (must update imports carefully)

---

### 6. Inconsistent Error Handling

**Source:** Phase 8 Research

**Observation:** Functions return different types on error:
- `get_quality_profiles()` returns `[]` on error
- `get_system_status()` returns `{}` on error
- `lookup_movie()` returns `None` on error
- `add_movie()` raises exception on error

**Impact:** Callers must know which pattern each function uses. Silent failures possible when returning empty collections.

**Recommendation:** Standardize in Phase 9:
- **Option A:** Always return Result[T, Error] type
- **Option B:** Always raise exceptions, let callers handle
- **Option C:** Return None for single-item, [] for collections, raise for mutations (current implicit pattern)

**Effort:** 4 hours | **Risk:** Medium

---

### 7. Duplicate Test/Update Status Functions

**Source:** Complexity Reviewer (NEW)

**Observation:** `_test_and_update_radarr_status` and `_test_and_update_sonarr_status` are nearly identical.

**Location:** `listarr/routes/config_routes.py` lines 59-114

**Fix:**
```python
def _test_and_update_service_status(service: str, base_url: str, api_key: str):
    """Test API connection and update database status."""
    validate_fn = validate_radarr_api_key if service == "RADARR" else validate_sonarr_api_key
    test_result = validate_fn(base_url, api_key)
    # ... rest identical
```

**Effort:** 1 hour | **Risk:** Low

---

## Low Priority (Quick Wins)

### 8. Duplicate Helper Function

**Source:** Complexity Reviewer (NEW)

**Observation:** `format_relative_time()` defined in both files:
- `listarr/routes/lists_routes.py` line 63
- `listarr/routes/dashboard_routes.py` line 174

**Fix:** Move to `listarr/utils/time_utils.py` or `listarr/helpers.py`.

**Effort:** 30 minutes | **Risk:** Very low

---

### 9. Unused List Model Columns

**Source:** Complexity Reviewer (NEW)

**Observation:** These columns appear unused:
- `cache_enabled`
- `cache_ttl_hours`
- `last_tmdb_fetch_at`
- `cache_valid_until`

**Location:** `listarr/models/lists_model.py` lines 26-34

**Action:** Verify with grep, then remove with migration.

**Effort:** 30 minutes | **Risk:** Very low

---

### 10. Dashboard Cache: Synchronous Startup

**Source:** Phase 8 Research

**Observation:** `initialize_dashboard_cache()` blocks app startup while fetching stats from Radarr/Sonarr.

**Impact:** If services are slow/down, Flask app startup hangs. Poor user experience in Docker when services aren't ready.

**Recommendation:** Move to background thread or defer until first dashboard load:
```python
# Option A: Background refresh
threading.Thread(target=initialize_dashboard_cache, daemon=True).start()

# Option B: Lazy load
def get_dashboard_stats():
    if not _cache_initialized:
        initialize_dashboard_cache()
    return _cached_stats
```

**Effort:** 2 hours | **Risk:** Low

---

### 11. API Delay: Fixed 200ms Sleep

**Source:** Phase 8 Research

**Observation:** `API_CALL_DELAY = 0.2` with `time.sleep()` after each TMDB call.

**Impact:** Batch imports of 100 items = 20 seconds of just waiting. May be too conservative (wasting time) or too aggressive (still triggers rate limits).

**Recommendation:** Implement adaptive rate limiting:
- Track 429 responses
- Increase delay when rate limited
- Decrease delay when successful
- Or: Use TMDB's rate limit headers if available

**Effort:** 4 hours | **Risk:** Low

---

## What NOT to Refactor (Good Patterns)

The complexity review confirmed these patterns are appropriate:

1. **Service Layer Design** - Plain functions instead of classes is correct for stateless API wrappers
2. **ImportResult Dataclass** - Appropriately simple, don't expand
3. **http_client.py Shared Session** - Module-level singleton is correct pattern
4. **In-Memory Caching** - TTLCache and dicts are appropriate for single-process deployment
5. **Scheduler Singleton** - Module-level globals in scheduler.py are appropriate for APScheduler

---

## Priority Summary for Phase 9

| Priority | Issue | Effort | Risk |
|----------|-------|--------|------|
| **HIGH** | N+1 query in dashboard_routes.py | 1 hour | Low |
| **HIGH** | JS missing HTTP status checks | 2 hours | Low |
| **HIGH** | Dashboard stats duplication | 3 hours | Low |
| **HIGH** | Radarr/Sonarr service duplication | 4-6 hours | Medium |
| **MEDIUM** | lists_routes.py split (1007 lines) | 4 hours | Medium |
| **MEDIUM** | config_routes.py split (913 lines) | 4 hours | Medium |
| **MEDIUM** | Error handling standardization | 4 hours | Medium |
| **MEDIUM** | Test/update status duplication | 1 hour | Low |
| **LOW** | format_relative_time() duplicate | 30 min | Very Low |
| **LOW** | Unused List model columns | 30 min | Very Low |
| **LOW** | Dashboard cache async startup | 2 hours | Low |
| **LOW** | Adaptive TMDB rate limiting | 4 hours | Low |

**Total Immediate Work (HIGH):** ~10-12 hours
**Total Recommended Cleanup:** ~25-30 hours (incremental)

---

## Files Affected

- `listarr/routes/dashboard_routes.py` - N+1 query fix
- `listarr/routes/lists_routes.py` - Split, helper extraction
- `listarr/routes/config_routes.py` - Split, status function consolidation
- `listarr/services/radarr_service.py` - Consolidation with Sonarr
- `listarr/services/sonarr_service.py` - Consolidation with Radarr
- `listarr/services/dashboard_cache.py` - Stats consolidation, async startup
- `listarr/services/tmdb_cache.py` - Adaptive rate limiting
- `listarr/models/lists_model.py` - Remove unused columns
- `listarr/models/jobs_model.py` - Add List relationship
- `listarr/static/js/*.js` - HTTP status checks

---

*Phase 8 Research: 2026-02-05*
*Complexity Review: 2026-02-05*
