# Phase 8: Architecture & API Consolidation - Research

**Researched:** 2026-02-05
**Domain:** HTTP API consolidation, dependency reduction, Python service layer architecture
**Confidence:** HIGH

## Summary

This phase removes third-party API wrapper libraries (pyarr, tmdbv3api) and consolidates to direct HTTP calls using Python's `requests` library with shared session management. The research reveals that while API wrappers provide convenience, they add dependency overhead and abstract away control that's beneficial when you need consistent error handling and connection pooling.

The standard approach for API consolidation in Python Flask applications is to:
1. Use `requests.Session()` with custom `HTTPAdapter` for retry logic and connection pooling
2. Implement a base HTTP client class that all service modules use
3. Apply consistent timeout, retry, and error handling patterns across all external API calls
4. Store session instances at the application level (not per-request) for connection reuse

The current codebase uses pyarr (last updated July 2023, maintenance inactive) and tmdbv3api (v1.9.0) which abstract Radarr/Sonarr/TMDB APIs. Both libraries use `requests` internally but don't expose session management or advanced retry configuration. Replacing them reduces dependencies from 25+ to 23 packages while gaining control over HTTP behavior.

**Primary recommendation:** Create a shared `http_client.py` module with a configured `requests.Session` instance that all service modules import. This provides connection pooling, consistent timeouts, exponential backoff retries, and unified error handling across Radarr, Sonarr, and TMDB integrations.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.32.4+ | HTTP client library | Industry standard, mature (14+ years), excellent session management, universally documented |
| urllib3 | 1.26.0+ (included with requests) | HTTP connection pooling and retry logic | Powers requests library, provides Retry class for backoff strategies |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cachetools | 5.3.0+ | In-memory caching | Already in use for TMDB caching, can extend to cache service settings |
| cryptography | 44.0.1+ | API key encryption | Already in use for credentials, no change needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| requests | httpx | httpx offers async/HTTP2 support but adds complexity; requests is simpler and sufficient for this use case |
| requests | urllib (stdlib) | urllib is lower-level and requires more boilerplate; requests provides better API and is already a dependency |
| Direct APIs | Keep pyarr/tmdbv3api | Keeping wrappers is easier short-term but adds maintenance risk (pyarr inactive), abstracts away session control, and increases dependency count |

**Installation:**
```bash
# No new dependencies needed - requests already in requirements.txt
# Just remove:
pip uninstall pyarr tmdbv3api
```

## Architecture Patterns

### Recommended Project Structure
```
listarr/services/
├── http_client.py          # Shared HTTP session with retry logic
├── radarr_service.py       # Direct Radarr API calls
├── sonarr_service.py       # Direct Sonarr API calls
├── tmdb_service.py         # Direct TMDB API calls
└── tmdb_cache.py           # TMDB caching layer (existing)
```

### Pattern 1: Shared Session with Retry Logic
**What:** Create a module-level session instance with configured retry adapter
**When to use:** All external API calls should use this session
**Example:**
```python
# Source: https://requests.readthedocs.io/en/latest/user/advanced/
# and https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Configure retry strategy
retry_strategy = Retry(
    total=3,  # Maximum retry attempts
    backoff_factor=1,  # Wait 1s, 2s, 4s between retries
    status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP codes
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]  # Methods to retry
)

# Create adapter with retry strategy
adapter = HTTPAdapter(max_retries=retry_strategy)

# Create session and mount adapter
http_session = requests.Session()
http_session.mount("http://", adapter)
http_session.mount("https://", adapter)

# Set default timeout (prevents hanging)
DEFAULT_TIMEOUT = 30  # seconds
```

### Pattern 2: API Service Module Structure
**What:** Each service module provides focused, stateless functions
**When to use:** For all Radarr/Sonarr/TMDB service implementations
**Example:**
```python
# Source: Based on https://www.cosmicpython.com/book/chapter_04_service_layer.html
# Service layer pattern for Flask applications

from listarr.services.http_client import http_session, DEFAULT_TIMEOUT

def get_quality_profiles(base_url: str, api_key: str) -> list:
    """
    Fetches quality profiles from Radarr.

    Args:
        base_url: Radarr base URL (e.g., "http://localhost:7878/")
        api_key: Radarr API key

    Returns:
        list: Quality profile dicts or empty list on error
    """
    url = f"{base_url.rstrip('/')}/api/v3/qualityprofile"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        profiles = response.json()
        return [{"id": p["id"], "name": p["name"]} for p in profiles]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching quality profiles: {e}", exc_info=True)
        return []
```

### Pattern 3: Consistent Error Handling
**What:** Catch specific exception types and provide meaningful logging
**When to use:** All API service functions
**Example:**
```python
# Source: https://requests.readthedocs.io/en/latest/user/quickstart/#errors-and-exceptions

import requests
import logging

logger = logging.getLogger(__name__)

try:
    response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()  # Raises HTTPError for 4xx/5xx
    return response.json()
except requests.exceptions.Timeout:
    logger.error(f"Request timeout for {url}")
    return None
except requests.exceptions.ConnectionError:
    logger.error(f"Connection error for {url}")
    return None
except requests.exceptions.HTTPError as e:
    logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
    return None
except requests.exceptions.RequestException as e:
    logger.error(f"Request error for {url}: {e}", exc_info=True)
    return None
```

### Pattern 4: API Authentication Patterns
**What:** Pass API keys via headers (Radarr/Sonarr) or query params (TMDB)
**When to use:** All authenticated requests
**Example:**
```python
# Radarr/Sonarr: X-Api-Key header
headers = {"X-Api-Key": api_key}
response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)

# TMDB: api_key query parameter
params = {"api_key": api_key, "language": "en"}
response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
```

### Anti-Patterns to Avoid
- **Creating new Session per request:** Sessions are meant to be reused across requests for connection pooling. Create once, use many times.
- **Missing timeouts:** Always set timeout parameter. Without it, requests can hang indefinitely.
- **Catching generic Exception:** Catch specific `requests.exceptions.*` exceptions for better error handling and logging.
- **Rebuilding URLs manually:** Use `f-string` for base URL + endpoint. Avoid string concatenation bugs by stripping/adding slashes consistently.
- **Not using raise_for_status():** This method raises exceptions for 4xx/5xx responses, making error handling consistent.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP connection pooling | Custom socket management | `requests.Session()` | Connection pooling is complex (SSL, keep-alive, connection limits). Session handles it automatically. |
| Retry logic with backoff | Custom retry loops | `urllib3.util.Retry` + `HTTPAdapter` | Exponential backoff has edge cases (jitter, max delay). Retry class is battle-tested. |
| JSON parsing errors | Try/except per endpoint | `response.json()` with exception handling | requests handles JSON decode errors elegantly. Don't wrap every call individually. |
| API pagination | Manual page tracking | Iterator pattern with yield | For multi-page TMDB fetches, use generator functions to abstract pagination. |
| Service configuration caching | Database query per call | In-memory cache with TTL | Service settings rarely change. Cache them to avoid repeated DB/API calls. |

**Key insight:** HTTP clients have decades of edge cases solved (SSL verification, redirects, chunked encoding, compression, keep-alive, connection limits). Don't rebuild these. Focus on business logic.

## Common Pitfalls

### Pitfall 1: Session Lifetime Management
**What goes wrong:** Creating session per request loses connection pooling benefit. Storing session as global without cleanup can leak connections.
**Why it happens:** Unclear documentation about when sessions should be created/destroyed.
**How to avoid:** Create session at module level (imports happen once). For Flask, sessions live for app lifetime. No explicit cleanup needed - Python GC handles it.
**Warning signs:** High number of TIME_WAIT connections. Slow API calls despite same endpoint. "Connection pool full" errors.

### Pitfall 2: Missing Timeout on All Requests
**What goes wrong:** One slow/hanging external API call blocks the entire import job. Dashboard loads hang indefinitely.
**Why it happens:** requests doesn't timeout by default. Easy to forget timeout parameter on every call.
**How to avoid:** Set DEFAULT_TIMEOUT constant and use it everywhere. Consider implementing a custom session wrapper that enforces timeout.
**Warning signs:** Import jobs that never complete. Gunicorn workers timing out. "App not responding" errors.

### Pitfall 3: Over-Retrying on Client Errors (4xx)
**What goes wrong:** Retry logic attempts 4xx errors (Bad Request, Unauthorized, Not Found) which will never succeed.
**Why it happens:** Retry configuration includes 4xx in status_forcelist.
**How to avoid:** Only retry 5xx (server errors) and 429 (rate limit). Never retry 4xx (client errors) - these indicate bugs in our code.
**Warning signs:** Import jobs taking 3x longer than necessary. Logs showing repeated 404/400 errors for same item.

### Pitfall 4: Not Normalizing Base URLs
**What goes wrong:** Service configured as "http://localhost:7878" (no trailing slash) but code expects "http://localhost:7878/". Results in URLs like "http://localhost:7878/api/v3/movie" (missing slash) or "http://localhost:7878//api/v3/movie" (double slash).
**Why it happens:** Inconsistent URL joining logic across codebase.
**How to avoid:** Always `base_url.rstrip('/')` before joining with `/api/v3/...`. Be consistent about where slashes live.
**Warning signs:** API calls returning 404 for valid endpoints. Intermittent failures based on how user enters URL.

### Pitfall 5: Ignoring Response Status Codes
**What goes wrong:** API returns 200 OK but body contains error message (some APIs use 200 for all responses). Code assumes success.
**Why it happens:** Only checking `response.ok` or `response.status_code == 200` without validating response body.
**How to avoid:** Use `response.raise_for_status()` first, then validate response structure. For APIs that return 200 with error bodies, check for error keys in JSON.
**Warning signs:** "Added" movies not appearing in Radarr. Import showing success but nothing happens. Silent failures.

## Code Examples

Verified patterns from official sources:

### Radarr: Get System Status
```python
# Source: https://radarr.video/docs/api/ (OpenAPI spec)
# Endpoint: GET /api/v3/system/status
# Auth: X-Api-Key header

def get_system_status(base_url: str, api_key: str) -> dict:
    """
    Fetches system status from Radarr.

    Returns:
        dict: {"version": "5.3.6.8612", "instanceName": "Radarr",
               "isProduction": True, "isDebug": False}
    """
    url = f"{base_url.rstrip('/')}/api/v3/system/status"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        status = response.json()
        return {
            "version": status.get("version"),
            "instance_name": status.get("instanceName"),
            "is_production": status.get("isProduction", False),
            "is_debug": status.get("isDebug", False),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching system status: {e}", exc_info=True)
        return {}
```

### Radarr: Add Movie
```python
# Source: https://radarr.video/docs/api/ (OpenAPI spec)
# Endpoint: POST /api/v3/movie
# Auth: X-Api-Key header

def add_movie(
    base_url: str,
    api_key: str,
    movie_data: dict,
    root_folder: str,
    quality_profile_id: int,
    monitored: bool = True,
    search_on_add: bool = True,
    tags: list[int] = None,
) -> dict:
    """
    Add a movie to Radarr.

    Args:
        movie_data: Movie dict from lookup_movie()
        root_folder: Path string (e.g., "/movies")
        quality_profile_id: Integer ID of quality profile
        monitored: Whether to monitor the movie
        search_on_add: Whether to search immediately after adding
        tags: List of tag IDs

    Returns:
        dict: Added movie data from Radarr

    Raises:
        requests.exceptions.RequestException: On API error
    """
    url = f"{base_url.rstrip('/')}/api/v3/movie"
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    # Build payload
    payload = movie_data.copy()
    payload.update({
        "rootFolderPath": root_folder,
        "qualityProfileId": quality_profile_id,
        "monitored": monitored,
        "addOptions": {"searchForMovie": search_on_add},
        "tags": tags or [],
    })

    response = http_session.post(
        url,
        json=payload,
        headers=headers,
        timeout=DEFAULT_TIMEOUT
    )
    response.raise_for_status()
    return response.json()
```

### TMDB: Get Trending Movies
```python
# Source: https://developer.themoviedb.org/reference/trending-movies
# Endpoint: GET /3/trending/movie/{time_window}
# Auth: api_key query parameter

def get_trending_movies(api_key: str, time_window: str = "week", page: int = 1) -> list:
    """
    Fetch trending movies from TMDB.

    Args:
        api_key: TMDB API key
        time_window: 'day' or 'week'
        page: Page number (default: 1)

    Returns:
        list: List of movie dicts with id, title, release_date, overview, etc.
    """
    url = f"https://api.themoviedb.org/3/trending/movie/{time_window}"
    params = {
        "api_key": api_key,
        "page": page,
        "language": "en",
    }

    try:
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching trending movies: {e}", exc_info=True)
        return []
```

### TMDB: Get External IDs (TVDB Translation)
```python
# Source: https://developer.themoviedb.org/reference/tv-series-external-ids
# Endpoint: GET /3/tv/{series_id}/external_ids
# Auth: api_key query parameter

def get_tvdb_id_from_tmdb(tmdb_id: int, api_key: str) -> int | None:
    """
    Get TVDB ID for a TMDB TV show.

    Args:
        tmdb_id: TMDB TV show ID
        api_key: TMDB API key

    Returns:
        int: TVDB ID or None if not found
    """
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids"
    params = {"api_key": api_key}

    try:
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        external_ids = response.json()
        return external_ids.get("tvdb_id")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching TVDB ID for TMDB TV show {tmdb_id}: {e}", exc_info=True)
        return None
```

### Shared HTTP Client Module
```python
# Source: https://requests.readthedocs.io/en/latest/user/advanced/
# File: listarr/services/http_client.py

"""
Shared HTTP client for all external API calls.
Provides connection pooling, retry logic, and consistent timeout handling.
"""

import logging
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

# Default timeout for all requests (connection, read)
DEFAULT_TIMEOUT = 30  # seconds

# Configure retry strategy
# Only retry on server errors (5xx) and rate limits (429)
# Don't retry on client errors (4xx) - those indicate bugs in our code
retry_strategy = Retry(
    total=3,  # Maximum retry attempts
    backoff_factor=1,  # Wait 1s, 2s, 4s between retries (exponential backoff)
    status_forcelist=[429, 500, 502, 503, 504],  # HTTP codes to retry
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],  # Methods to retry
    raise_on_status=False,  # Don't raise MaxRetryError - let caller handle
)

# Create HTTP adapter with retry strategy
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,  # Number of connection pools to cache
    pool_maxsize=10,  # Max connections per pool
)

# Create shared session
http_session = requests.Session()
http_session.mount("http://", adapter)
http_session.mount("https://", adapter)

# Set default headers (can be overridden per request)
http_session.headers.update({
    "User-Agent": "Listarr/1.0",
})

logger.info("HTTP client initialized with retry strategy")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pyarr library for Radarr/Sonarr | Direct requests with OpenAPI spec | 2023-2026 | pyarr maintenance went inactive July 2023. Direct API calls provide more control and reduce dependencies. |
| tmdbv3api wrapper | Direct requests to TMDB v3 API | Ongoing | TMDB API is stable. Direct calls avoid wrapper abstraction and allow custom caching strategies. |
| Per-request sessions | Shared session with connection pooling | Modern Python best practice | Connection reuse reduces latency by 50-200ms per request. Critical for batch imports. |
| Fixed retry delays | Exponential backoff with urllib3.Retry | urllib3 1.26+ (2020) | Prevents thundering herd problem. Respects rate limits better. |
| Global timeout or no timeout | Per-request timeout with fallback default | requests 2.4.0+ (2014) | Prevents hanging requests. Modern APIs expect clients to timeout. |

**Deprecated/outdated:**
- **pyarr 5.2.0 (July 2023):** No updates in 18+ months. Project appears abandoned. GitHub issues show API compatibility problems with newer Radarr/Sonarr versions.
- **Session-less requests:** Old tutorials show `requests.get()` instead of `session.get()`. This misses connection pooling benefits.
- **Manual retry loops:** Code like `for attempt in range(3): try: ... except: sleep(1)` is now replaced by urllib3.Retry.

## Open Questions

Things that couldn't be fully resolved:

1. **Service Settings Caching Strategy**
   - What we know: Quality profiles, root folders, and tags are fetched from Radarr/Sonarr on every dropdown render. These rarely change.
   - What's unclear: Should we cache them in-memory like dashboard stats? Or is the DB query fast enough that caching adds unnecessary complexity?
   - Recommendation: Implement in-memory cache with 5-minute TTL. Measure impact during Phase 9. If <100ms improvement, remove cache (YAGNI principle).

2. **OpenAPI Spec Validation**
   - What we know: Radarr/Sonarr use OpenAPI specs at /api/v3/openapi.json. Could validate requests/responses.
   - What's unclear: Does OpenAPI validation add value for our use case? We're not building a general-purpose SDK.
   - Recommendation: Skip OpenAPI validation. It adds dependency (openapi-core) and complexity. Manual testing of documented endpoints is sufficient.

3. **HTTP/2 Support**
   - What we know: requests library doesn't support HTTP/2. httpx does.
   - What's unclear: Would HTTP/2 multiplexing improve batch import performance?
   - Recommendation: Stick with requests. HTTP/2 benefits are marginal for sequential API calls. The added complexity (async, httpx vs requests differences) isn't worth it.

4. **Radarr/Sonarr API Version Detection**
   - What we know: Current code assumes /api/v3 endpoints. Radarr/Sonarr might release v4/v5 APIs.
   - What's unclear: Should we auto-detect API version from /api/version endpoint?
   - Recommendation: Hardcode /api/v3 for now. Both projects are stable on v3. Add version detection only when v4 is released and we need to support both.

## Architecture Concerns for Phase 9

Based on codebase review, document these for Phase 9 review:

1. **Over-Engineering: Service Layer Abstraction**
   - Current: Separate service modules (radarr_service.py, sonarr_service.py) with 15+ functions each
   - Concern: Functions are thin wrappers over API calls. Is the abstraction layer adding value or just indirection?
   - Evaluation needed: Could routes call HTTP client directly? Or does service layer provide testability benefits?

2. **Tight Coupling: Import Service + TMDB Cache + Service Modules**
   - Current: import_service.py imports from radarr_service, sonarr_service, tmdb_service, and tmdb_cache
   - Concern: Change ripples. Modifying one service function signature requires updates in 3+ places.
   - Evaluation needed: Consider dependency injection or a unified API client interface.

3. **Inconsistent Error Handling**
   - Current: Some functions return empty list/dict on error, others return None, some raise exceptions
   - Concern: Callers can't reliably detect errors. Leads to silent failures.
   - Evaluation needed: Standardize on Result type (success/failure) or consistent exception strategy.

4. **Dashboard Cache: Synchronous API Calls on Startup**
   - Current: initialize_dashboard_cache() blocks app startup while fetching Radarr/Sonarr stats
   - Concern: If Radarr/Sonarr are slow/down, app startup hangs. Poor user experience.
   - Evaluation needed: Move dashboard refresh to background thread or defer until first page load.

5. **Module Imports: Wildcard Imports from Services**
   - Current: `from listarr.services.crypto_utils import *  # noqa: F403`
   - Concern: Unclear what's imported. Namespace pollution. Violates PEP 8.
   - Evaluation needed: Explicit imports or __all__ list in __init__.py.

6. **API Delay: Global Sleep Between Calls**
   - Current: `API_CALL_DELAY = 0.2  # 200ms` with `time.sleep()` after each call
   - Concern: Hardcoded delay may be too conservative (slows imports) or too aggressive (triggers rate limits).
   - Evaluation needed: Implement adaptive rate limiting based on 429 responses, or make delay configurable.

## Sources

### Primary (HIGH confidence)
- [Radarr API Docs](https://radarr.video/docs/api/) - Official API documentation
- [Sonarr API Docs](https://sonarr.tv/docs/api/) - Official API documentation
- [TMDB API v3 Reference](https://developer.themoviedb.org/reference/getting-started) - Official REST API reference
- [Python requests documentation - Advanced Usage](https://requests.readthedocs.io/en/latest/user/advanced/) - Session management, adapters, retry
- [urllib3 Retry documentation](https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry) - Retry strategy configuration

### Secondary (MEDIUM confidence)
- [Python Requests Session Best Practices](https://python-requests.org/python-requests-session/) - Session usage patterns
- [Architecture Patterns with Python - Service Layer](https://www.cosmicpython.com/book/chapter_04_service_layer.html) - Flask service layer architecture
- [Python Requests Retry in 2026](https://decodo.com/blog/python-requests-retry) - HTTPAdapter retry patterns
- [Design Patterns for External API Integration](https://mshaeri.com/blog/design-patterns-i-use-in-external-service-integration-in-python/) - Singleton vs instance patterns
- [Python Dependency Management Best Practices](https://www.geeksforgeeks.org/python/best-practices-for-managing-python-dependencies/) - Dependency reduction benefits

### Tertiary (LOW confidence)
- [pyarr GitHub Repository](https://github.com/totaldebug/pyarr) - Source code review for migration
- [tmdbv3api GitHub Repository](https://github.com/AnthonyBloomer/tmdbv3api) - Source code review for migration
- [Python Code Smells and Refactoring](https://arjancodes.com/blog/best-practices-for-eliminating-python-code-smells/) - Over-engineering identification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - requests/urllib3 are industry standard, well-documented, verified in production
- Architecture: HIGH - Service layer pattern verified from O'Reilly book, official requests docs, current codebase review
- Pitfalls: HIGH - Based on official docs, common production issues, and codebase analysis
- API endpoints: MEDIUM - OpenAPI specs confirmed to exist but full endpoint details not extracted (page truncation)
- Over-engineering concerns: MEDIUM - Based on codebase review and code smell research, needs Phase 9 evaluation

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - stable technology stack)
