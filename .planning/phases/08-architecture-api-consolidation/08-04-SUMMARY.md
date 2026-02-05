---
phase: 08-architecture-api-consolidation
plan: 04
subsystem: api

provides:
  - Direct TMDB API integration via http_session
  - No external library dependency for TMDB calls
  - All 14 TMDB functions using shared HTTP client

requires:
  - 08-01 (http_client.py with http_session, DEFAULT_TIMEOUT, API_BASE_TMDB)

affects:
  - Phase 9 (Code Quality) - tmdbv3api can be removed from requirements.txt
  - Any future TMDB endpoint additions

tech-stack:
  removed:
    - tmdbv3api (can now be uninstalled, dependency removed from tmdb_service.py)
  patterns:
    - "Direct HTTP calls with http_session.get() for all TMDB endpoints"
    - "Query parameter authentication: api_key={key}"

key-files:
  modified:
    - listarr/services/tmdb_service.py
    - tests/unit/test_tmdb_service.py

decisions:
  - "Query param auth: api_key passed as query parameter (TMDB standard)"
  - "Unified error handling: requests.exceptions.RequestException for all errors"
  - "Language default: 'en' for all requests (matches previous tmdbv3api behavior)"

metrics:
  duration: ~15 minutes
  completed: 2026-02-05
---

# Phase 08 Plan 04: TMDB Direct API Migration Summary

**Direct TMDB API calls using shared http_session - tmdbv3api library eliminated from service layer**

## What Changed

### tmdb_service.py

Before: Used `tmdbv3api` library classes (TMDb, Movie, TV, Discover, Trending)
After: Direct HTTP calls using `http_session.get()` from http_client.py

**Imports replaced:**
```python
# Before
from tmdbv3api import TV, Discover, Movie, TMDb, Trending

# After
from listarr.services.http_client import API_BASE_TMDB, DEFAULT_TIMEOUT, http_session
import requests
```

**Function `_init_tmdb()` removed** - No longer needed with direct calls

### Functions Migrated (14 total)

| Function | Endpoint | Notes |
|----------|----------|-------|
| validate_tmdb_api_key | /3/movie/popular | Test call to validate key |
| get_tvdb_id_from_tmdb | /3/tv/{id}/external_ids | Returns tvdb_id |
| get_imdb_id_from_tmdb | /3/{movie|tv}/{id}/external_ids | Returns imdb_id |
| get_trending_movies | /3/trending/movie/{week|day} | time_window in URL |
| get_trending_tv | /3/trending/tv/{week|day} | time_window in URL |
| get_popular_movies | /3/movie/popular | region param optional |
| get_popular_tv | /3/tv/popular | No region support |
| get_top_rated_movies | /3/movie/top_rated | region param optional |
| get_top_rated_tv | /3/tv/top_rated | No region support |
| discover_movies | /3/discover/movie | filters + region |
| discover_tv | /3/discover/tv | filters + region |
| get_movie_details | /3/movie/{id} | Returns full JSON |
| get_tv_details | /3/tv/{id} | Returns full JSON |

### Test Changes

Updated from mocking tmdbv3api classes to mocking `http_session.get`:

```python
# Before
@patch("listarr.services.tmdb_service.Movie")
@patch("listarr.services.tmdb_service._init_tmdb")
def test_get_popular_movies(self, mock_init, mock_movie_class):
    mock_movie = MagicMock()
    mock_movie.popular.return_value = [...]
    mock_movie_class.return_value = mock_movie

# After
@patch("listarr.services.tmdb_service.http_session")
def test_get_popular_movies(self, mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [...]}
    mock_session.get.return_value = mock_response
```

## Benefits

1. **Full control over HTTP behavior** - Retry strategy, timeouts, connection pooling via http_client.py
2. **No external library dependency** - One less package to maintain/update
3. **Consistent error handling** - All requests use `requests.exceptions.RequestException`
4. **Transparent API calls** - Easier to debug, monitor, and extend
5. **Unified session** - Shares connection pool with Radarr/Sonarr services

## Backward Compatibility

All function signatures remain unchanged. Cache layer (tmdb_cache.py) continues to work without modification.

## Commits

| Hash | Description |
|------|-------------|
| c35b275 | feat(08-04): replace tmdbv3api with direct HTTP calls |

## Deviations from Plan

None - plan executed exactly as written.

## Test Results

- 87/87 TMDB-related tests passed
- 52 tests in test_tmdb_service.py (updated to mock http_session)
- 15 tests in test_tmdb_cache.py (unchanged, still pass)
- 20 integration tests involving TMDB (unchanged, still pass)

## Next Steps

1. **Can remove tmdbv3api from requirements.txt** - Should be done during Phase 9 or dedicated cleanup
2. **Monitor for any edge cases** - Watch for rate limiting or retry behavior differences
3. **Continue with 08-05** - Radarr/Sonarr service migration if planned

## Verification Checklist

- [x] No `from tmdbv3api import` in tmdb_service.py
- [x] All 14 functions use http_session from http_client.py
- [x] Function signatures unchanged (backward compatible)
- [x] tmdb_cache.py still works with updated tmdb_service.py
- [x] All tmdb-related tests pass (87/87)
- [x] Ruff/black formatting passes
