# Phase 3: TMDB Caching Layer - Research

**Researched:** 2026-01-18
**Domain:** Flask API response caching with TMDB API integration
**Confidence:** HIGH

<research_summary>
## Summary

Researched caching strategies for TMDB API responses in a Flask application. The current codebase uses tmdbv3api which has built-in LRU caching (unlimited, no TTL) and rate limit handling. TMDB's own server-side cache is ~8 hours, with rate limits around 50 requests/second per IP.

The standard approach is to use Flask-Caching with TTLCache patterns for different data types: trending/popular lists (short TTL: 1-6 hours), discovery results (medium TTL: 6-24 hours), and movie/TV details (long TTL: 24-72 hours). The existing dashboard_cache.py pattern with in-memory dict + threading.Lock is suitable for single-instance homelab deployment.

**Primary recommendation:** Extend the existing in-memory caching pattern (dashboard_cache.py style) with TTL support using cachetools.TTLCache. This aligns with the existing codebase and avoids adding external dependencies like Redis for a single-instance homelab app.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cachetools | 5.3+ | TTL-aware caching with memoization | Simple, no external deps, TTLCache provides per-item expiration |
| Flask-Caching | 2.3+ | View-level caching (optional) | If view caching needed, but may be overkill for service-layer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| threading | stdlib | Lock for thread-safe cache access | Multi-threaded Flask (Gunicorn workers) |
| time | stdlib | monotonic() for TTL timing | Default timer for TTLCache |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cachetools | Flask-Caching | Flask-Caching adds complexity for service-layer caching; better for view-level |
| In-memory cache | Redis | Redis overkill for single-instance homelab; adds external dependency |
| Custom dict+TTL | requests-cache | requests-cache good for HTTP-level but tmdbv3api abstracts HTTP layer |

### Already Available
| Library | Status | Notes |
|---------|--------|-------|
| tmdbv3api | Installed | Has built-in LRU cache (no TTL) via TMDB_CACHE_ENABLED env var |
| threading | stdlib | Already used in dashboard_cache.py |

**Installation:**
```bash
pip install cachetools>=5.3.0
```

Or add to requirements.txt:
```
cachetools>=5.3.0
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
listarr/services/
├── tmdb_service.py          # TMDB API functions (existing)
├── tmdb_cache.py            # NEW: TMDB caching layer
├── dashboard_cache.py       # Existing: Dashboard stats cache
└── ...
```

### Pattern 1: Service-Layer Caching with TTLCache
**What:** Wrap TMDB service functions with TTL-aware cache
**When to use:** All TMDB API calls that return list data (trending, popular, discover)
**Example:**
```python
# Source: cachetools documentation + existing dashboard_cache.py pattern
from cachetools import TTLCache
from threading import Lock

# Cache instances with appropriate TTLs
_trending_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour for trending
_popular_cache = TTLCache(maxsize=100, ttl=14400)  # 4 hours for popular
_discover_cache = TTLCache(maxsize=500, ttl=21600)  # 6 hours for discover
_cache_lock = Lock()

def get_trending_movies_cached(api_key: str, time_window: str = 'week', page: int = 1) -> list:
    """Cached version of get_trending_movies."""
    cache_key = f"trending_movies_{time_window}_{page}"

    with _cache_lock:
        if cache_key in _trending_cache:
            return _trending_cache[cache_key]

    # Cache miss - fetch from API
    result = get_trending_movies(api_key, time_window, page)

    with _cache_lock:
        _trending_cache[cache_key] = result

    return result
```

### Pattern 2: Cache-Aside Pattern (Manual)
**What:** Check cache, fetch on miss, store result
**When to use:** When you need explicit control over cache behavior
**Example:**
```python
def get_or_fetch(cache, key, fetch_fn, *args, **kwargs):
    """Generic cache-aside helper."""
    with _cache_lock:
        if key in cache:
            logger.debug(f"Cache hit: {key}")
            return cache[key]

    logger.debug(f"Cache miss: {key}")
    result = fetch_fn(*args, **kwargs)

    if result:  # Only cache successful results
        with _cache_lock:
            cache[key] = result

    return result
```

### Pattern 3: Decorator-Based Memoization with TTL
**What:** Use @cached decorator from cachetools for cleaner code
**When to use:** Simple functions without complex key generation
**Example:**
```python
from cachetools import cached, TTLCache
from threading import Lock

_discover_cache = TTLCache(maxsize=500, ttl=21600)
_discover_lock = Lock()

@cached(cache=_discover_cache, lock=_discover_lock)
def discover_movies_cached(api_key: str, filters_tuple: tuple, page: int = 1) -> list:
    """Cached movie discovery. Note: filters must be hashable tuple."""
    filters = dict(filters_tuple) if filters_tuple else None
    return discover_movies(api_key, filters, page)
```

### Anti-Patterns to Avoid
- **Caching with API key in cache key:** Don't include API key in cache keys - it's constant per session
- **Caching empty results forever:** Check for empty/error responses before caching
- **No TTL on trending data:** Trending changes frequently - always use short TTL
- **Global unlimited cache:** Will cause memory growth - always set maxsize
- **Ignoring thread safety:** Flask can be multi-threaded - always use Lock
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TTL expiration tracking | Custom dict with timestamps | cachetools.TTLCache | Handles expiration, LRU eviction, thread-safety edge cases |
| Rate limiting | Custom request counter | tmdbv3api built-in (TMDB_WAIT_ON_RATE_LIMIT=True) | Already implemented and tested |
| HTTP caching | Custom response storage | requests-cache (if needed) | Handles HTTP semantics, ETags, etc. |
| Cache key generation | String concatenation | Tuple of args (hashable) | Python's hash() handles it correctly |
| Thread-safe cache access | try/finally with manual locks | with Lock(): context manager | Cleaner, exception-safe |

**Key insight:** tmdbv3api already has built-in LRU caching and rate limit handling. The problem is it lacks TTL - cache never expires. Rather than replacing the library, add a TTL-aware cache layer on top of the service functions.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Cache Stampede on Expiration
**What goes wrong:** Multiple requests hit expired cache simultaneously, all fetch from API
**Why it happens:** TTL expires, many concurrent requests before first one finishes
**How to avoid:** For homelab single-user: unlikely to be an issue. For higher traffic: use locking during fetch or probabilistic early expiration
**Warning signs:** Spikes in TMDB API calls at regular intervals matching TTL

### Pitfall 2: Stale Data Served Too Long
**What goes wrong:** Users see outdated trending/popular data
**Why it happens:** TTL set too long for data that changes frequently
**How to avoid:**
- Trending: 1-2 hours max (TMDB updates frequently)
- Popular: 4-8 hours (more stable)
- Discover results: 6-24 hours (based on filters)
- Movie/TV details: 24-72 hours (rarely changes)
**Warning signs:** Users report outdated information, TMDB shows different results

### Pitfall 3: Memory Bloat from Unbounded Cache
**What goes wrong:** Cache grows indefinitely, consumes all memory
**Why it happens:** maxsize not set or too high, especially for discover queries with many filter combinations
**How to avoid:** Set reasonable maxsize per cache type. Discover has most variance - cap at 500-1000 entries
**Warning signs:** Memory usage grows over time, OOM errors

### Pitfall 4: Caching Error Responses
**What goes wrong:** API error gets cached, stuck serving errors
**Why it happens:** Caching result without checking if it's valid
**How to avoid:** Only cache non-empty, successful results. Check for [] or None before storing
**Warning signs:** Persistent errors even after API recovers

### Pitfall 5: Cache Key Collisions
**What goes wrong:** Different requests return same cached data
**Why it happens:** Cache key doesn't include all relevant parameters
**How to avoid:** Include all function parameters in cache key (time_window, page, filters, media_type)
**Warning signs:** Wrong data returned, genre filters returning wrong genres
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns for TMDB caching in Flask:

### Basic TTLCache Setup
```python
# Source: cachetools documentation + existing dashboard_cache.py pattern
from cachetools import TTLCache
from threading import Lock
import logging

logger = logging.getLogger(__name__)

# TTL values in seconds
TTL_TRENDING = 3600      # 1 hour
TTL_POPULAR = 14400      # 4 hours
TTL_DISCOVER = 21600     # 6 hours
TTL_DETAILS = 86400      # 24 hours

# Cache instances
_trending_cache = TTLCache(maxsize=100, ttl=TTL_TRENDING)
_popular_cache = TTLCache(maxsize=100, ttl=TTL_POPULAR)
_discover_cache = TTLCache(maxsize=500, ttl=TTL_DISCOVER)
_details_cache = TTLCache(maxsize=1000, ttl=TTL_DETAILS)

# Single lock for all caches (simpler for homelab)
_cache_lock = Lock()
```

### Cached Trending Movies
```python
def get_trending_movies_cached(api_key: str, time_window: str = 'week', page: int = 1) -> list:
    """
    Fetch trending movies with caching.

    Args:
        api_key: TMDB API key
        time_window: 'day' or 'week'
        page: Page number

    Returns:
        List of movie dicts, from cache if available
    """
    cache_key = f"trending_movies_{time_window}_{page}"

    # Check cache
    with _cache_lock:
        if cache_key in _trending_cache:
            logger.debug(f"Cache hit: {cache_key}")
            return _trending_cache[cache_key]

    # Cache miss - fetch from API
    logger.debug(f"Cache miss: {cache_key}")
    from listarr.services.tmdb_service import get_trending_movies
    result = get_trending_movies(api_key, time_window, page)

    # Only cache non-empty results
    if result:
        with _cache_lock:
            _trending_cache[cache_key] = result

    return result
```

### Cached Discovery with Filter Hashing
```python
import hashlib
import json

def _hash_filters(filters: dict) -> str:
    """Create stable hash from filter dict for cache key."""
    if not filters:
        return "none"
    # Sort keys for consistent hashing
    sorted_json = json.dumps(filters, sort_keys=True)
    return hashlib.md5(sorted_json.encode()).hexdigest()[:8]

def discover_movies_cached(api_key: str, filters: dict = None, page: int = 1) -> list:
    """
    Discover movies with optional filters, with caching.
    """
    filter_hash = _hash_filters(filters)
    cache_key = f"discover_movies_{filter_hash}_{page}"

    with _cache_lock:
        if cache_key in _discover_cache:
            logger.debug(f"Cache hit: {cache_key}")
            return _discover_cache[cache_key]

    logger.debug(f"Cache miss: {cache_key}")
    from listarr.services.tmdb_service import discover_movies
    result = discover_movies(api_key, filters, page)

    if result:
        with _cache_lock:
            _discover_cache[cache_key] = result

    return result
```

### Cache Statistics and Management
```python
def get_cache_stats() -> dict:
    """Get current cache statistics for monitoring."""
    with _cache_lock:
        return {
            "trending": {
                "size": len(_trending_cache),
                "maxsize": _trending_cache.maxsize,
                "ttl": _trending_cache.ttl
            },
            "popular": {
                "size": len(_popular_cache),
                "maxsize": _popular_cache.maxsize,
                "ttl": _popular_cache.ttl
            },
            "discover": {
                "size": len(_discover_cache),
                "maxsize": _discover_cache.maxsize,
                "ttl": _discover_cache.ttl
            },
            "details": {
                "size": len(_details_cache),
                "maxsize": _details_cache.maxsize,
                "ttl": _details_cache.ttl
            }
        }

def clear_all_caches():
    """Clear all TMDB caches. Useful for manual refresh."""
    with _cache_lock:
        _trending_cache.clear()
        _popular_cache.clear()
        _discover_cache.clear()
        _details_cache.clear()
    logger.info("All TMDB caches cleared")
```

### Integration with Existing Routes
```python
# In lists_routes.py - replace direct tmdb_service calls with cached versions
from listarr.services.tmdb_cache import (
    get_trending_movies_cached,
    get_trending_tv_cached,
    discover_movies_cached,
    discover_tv_cached
)

@lists_bp.route('/wizard/preview')
def wizard_preview():
    # Use cached versions instead of direct API calls
    if media_type == 'movie':
        if list_type == 'trending':
            results = get_trending_movies_cached(api_key, 'week', page=1)
        elif list_type == 'popular':
            results = get_popular_movies_cached(api_key, page=1)
        else:
            results = discover_movies_cached(api_key, filters, page=1)
    # ... etc
```
</code_examples>

<sota_updates>
## State of the Art (2025-2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TMDB 40 req/10s limit | ~50 req/s limit (effectively unlimited) | Dec 2019 | Rate limiting rarely an issue now |
| Flask-Cache | Flask-Caching | 2018+ | Flask-Cache deprecated, use Flask-Caching |
| functools.lru_cache | cachetools.TTLCache | Ongoing | lru_cache has no TTL; TTLCache does |
| Manual dict+timestamp | cachetools library | 2015+ | cachetools is battle-tested and maintained |

**New tools/patterns to consider:**
- **cachetools 5.x:** Stable, well-maintained, perfect for service-layer caching
- **tmdbv3api built-in caching:** Already available via TMDB_CACHE_ENABLED, but no TTL

**Deprecated/outdated:**
- **Flask-Cache:** Deprecated, use Flask-Caching instead
- **python-memcached:** Use pylibmc or pymemcache for Memcached (if needed)
- **Rolling your own TTL cache:** cachetools handles all edge cases

**TMDB API Notes:**
- Rate limiting effectively disabled (50 req/s is very high)
- Server-side cache is ~8 hours
- Recommended local cache: 24 hours is acceptable per ToS
- Trending updates more frequently than popularity
</sota_updates>

<open_questions>
## Open Questions

Things that couldn't be fully resolved:

1. **Should we use tmdbv3api's built-in cache or bypass it?**
   - What we know: tmdbv3api has LRU cache via TMDB_CACHE_ENABLED env var
   - What's unclear: Whether to use it AND add TTL layer, or disable it and use only TTL cache
   - Recommendation: Enable both - tmdbv3api caches raw HTTP, TTL cache handles expiration

2. **Exact TTL values for different endpoints**
   - What we know: TMDB server cache is ~8 hours, trending changes often
   - What's unclear: Optimal TTL for homelab use case balance (freshness vs API calls)
   - Recommendation: Start with 1h trending, 4h popular, 6h discover, 24h details. Tune based on usage.

3. **Should cache persist across restarts?**
   - What we know: Current dashboard_cache.py rebuilds on startup
   - What's unclear: Whether TMDB cache should persist (could use FileSystemCache or sqlite)
   - Recommendation: Start with in-memory only (like dashboard_cache). Persistence adds complexity for minimal gain in homelab.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [TMDB Rate Limiting Documentation](https://developer.themoviedb.org/docs/rate-limiting) - Official rate limit info
- [Flask-Caching Documentation](https://flask-caching.readthedocs.io/) - Flask caching patterns
- [cachetools Documentation](https://cachetools.readthedocs.io/) - TTLCache API reference
- [tmdbv3api GitHub](https://github.com/AnthonyBloomer/tmdbv3api) - Library source showing built-in LRU cache

### Secondary (MEDIUM confidence)
- [TMDB Cache Discussion](https://www.themoviedb.org/talk/5bd3a0fd0e0a2622da00b695) - Server-side ~8 hour cache info
- [TMDB Popularity & Trending](https://developer.themoviedb.org/docs/popularity-and-trending) - How trending vs popularity differs
- Existing dashboard_cache.py in codebase - Established pattern for Listarr

### Tertiary (LOW confidence - needs validation)
- None - all findings verified against official sources
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Flask + Python caching for TMDB API
- Ecosystem: cachetools, Flask-Caching, tmdbv3api built-ins
- Patterns: Cache-aside, TTL expiration, thread-safe access
- Pitfalls: Stampede, stale data, memory bloat, key collisions

**Confidence breakdown:**
- Standard stack: HIGH - cachetools is well-documented, widely used
- Architecture: HIGH - patterns follow existing dashboard_cache.py
- Pitfalls: HIGH - common issues documented in caching literature
- Code examples: HIGH - based on official cachetools docs and existing codebase

**Research date:** 2026-01-18
**Valid until:** 2026-02-18 (30 days - caching patterns stable)
</metadata>

---

*Phase: 03-tmdb-caching-layer*
*Research completed: 2026-01-18*
*Ready for planning: yes*
