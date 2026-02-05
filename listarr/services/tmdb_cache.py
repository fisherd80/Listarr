"""
TMDB API caching service.

This module provides TTL-aware caching for TMDB API calls using cachetools TTLCache.
Caching reduces API calls and improves response times for repeated requests.
"""

import hashlib
import json
import logging
import threading

from cachetools import TTLCache

from listarr.services import tmdb_service

logger = logging.getLogger(__name__)

# TTL constants (in seconds)
TTL_TRENDING = 3600  # 1 hour - trending data changes frequently
TTL_POPULAR = 14400  # 4 hours - popular lists update less often
TTL_DISCOVER = 21600  # 6 hours - discover results are relatively stable
TTL_DETAILS = 86400  # 24 hours - movie/TV details rarely change

# Cache instances with TTL
_trending_cache: TTLCache = TTLCache(maxsize=100, ttl=TTL_TRENDING)
_popular_cache: TTLCache = TTLCache(maxsize=100, ttl=TTL_POPULAR)
_discover_cache: TTLCache = TTLCache(maxsize=500, ttl=TTL_DISCOVER)
_details_cache: TTLCache = TTLCache(maxsize=1000, ttl=TTL_DETAILS)

# Single lock for thread-safe cache operations
_cache_lock = threading.Lock()


def _get_tmdb_region() -> str | None:
    """
    Get the configured TMDB region from ServiceConfig.
    Returns None if not configured (worldwide results).

    Note: This function must be called within a Flask app context.
    """
    try:
        from listarr.models.service_config_model import ServiceConfig

        tmdb_config = ServiceConfig.query.filter_by(service="TMDB").first()
        return tmdb_config.tmdb_region if tmdb_config else None
    except Exception:
        # Outside app context or error - return None (no region filter)
        return None


def _hash_filters(filters: dict) -> str:
    """
    Generate a stable hash key from a filter dictionary.

    Args:
        filters: Dictionary of filter parameters

    Returns:
        str: Stable hash string for the filter combination
    """
    if not filters:
        return "no_filters"

    # Sort keys for consistent ordering
    sorted_items = sorted(filters.items())
    filter_str = json.dumps(sorted_items, sort_keys=True)
    return hashlib.md5(filter_str.encode(), usedforsecurity=False).hexdigest()


def get_trending_movies_cached(api_key: str, time_window: str = "week", page: int = 1) -> list:
    """
    Fetch trending movies with caching.

    Args:
        api_key: TMDB API key
        time_window: 'day' or 'week'
        page: Page number

    Returns:
        list: List of trending movie dicts
    """
    cache_key = f"trending_movies:{time_window}:{page}"

    with _cache_lock:
        if cache_key in _trending_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _trending_cache[cache_key]

    # Fetch outside lock to avoid blocking other cache operations
    result = tmdb_service.get_trending_movies(api_key, time_window, page)

    if result:  # Only cache successful results
        with _cache_lock:
            _trending_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached {len(result)} items")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def get_trending_tv_cached(api_key: str, time_window: str = "week", page: int = 1) -> list:
    """
    Fetch trending TV shows with caching.

    Args:
        api_key: TMDB API key
        time_window: 'day' or 'week'
        page: Page number

    Returns:
        list: List of trending TV show dicts
    """
    cache_key = f"trending_tv:{time_window}:{page}"

    with _cache_lock:
        if cache_key in _trending_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _trending_cache[cache_key]

    result = tmdb_service.get_trending_tv(api_key, time_window, page)

    if result:
        with _cache_lock:
            _trending_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached {len(result)} items")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def get_popular_movies_cached(api_key: str, page: int = 1) -> list:
    """
    Fetch popular movies with caching.
    Region is automatically fetched from ServiceConfig if configured.

    Args:
        api_key: TMDB API key
        page: Page number

    Returns:
        list: List of popular movie dicts
    """
    region = _get_tmdb_region()
    cache_key = f"popular_movies:{page}:{region or 'WW'}"

    with _cache_lock:
        if cache_key in _popular_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _popular_cache[cache_key]

    result = tmdb_service.get_popular_movies(api_key, page, region=region)

    if result:
        with _cache_lock:
            _popular_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached {len(result)} items")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def get_popular_tv_cached(api_key: str, page: int = 1) -> list:
    """
    Fetch popular TV shows with caching.

    Args:
        api_key: TMDB API key
        page: Page number

    Returns:
        list: List of popular TV show dicts
    """
    cache_key = f"popular_tv:{page}"

    with _cache_lock:
        if cache_key in _popular_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _popular_cache[cache_key]

    result = tmdb_service.get_popular_tv(api_key, page)

    if result:
        with _cache_lock:
            _popular_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached {len(result)} items")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def get_top_rated_movies_cached(api_key: str, page: int = 1) -> list:
    """
    Fetch top rated movies with caching.
    Region is automatically fetched from ServiceConfig if configured.

    Args:
        api_key: TMDB API key
        page: Page number

    Returns:
        list: List of top rated movie dicts
    """
    region = _get_tmdb_region()
    cache_key = f"top_rated_movies:{page}:{region or 'WW'}"

    with _cache_lock:
        if cache_key in _popular_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _popular_cache[cache_key]

    result = tmdb_service.get_top_rated_movies(api_key, page, region=region)

    if result:
        with _cache_lock:
            _popular_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached {len(result)} items")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def get_top_rated_tv_cached(api_key: str, page: int = 1) -> list:
    """
    Fetch top rated TV shows with caching.

    Args:
        api_key: TMDB API key
        page: Page number

    Returns:
        list: List of top rated TV show dicts
    """
    cache_key = f"top_rated_tv:{page}"

    with _cache_lock:
        if cache_key in _popular_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _popular_cache[cache_key]

    result = tmdb_service.get_top_rated_tv(api_key, page)

    if result:
        with _cache_lock:
            _popular_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached {len(result)} items")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def discover_movies_cached(api_key: str, filters: dict = None, page: int = 1) -> list:
    """
    Discover movies with caching.
    Region is automatically fetched from ServiceConfig if configured.

    Args:
        api_key: TMDB API key
        filters: Optional filter parameters
        page: Page number

    Returns:
        list: List of discovered movie dicts
    """
    region = _get_tmdb_region()
    filter_hash = _hash_filters(filters)
    cache_key = f"discover_movies:{filter_hash}:{page}:{region or 'WW'}"

    with _cache_lock:
        if cache_key in _discover_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _discover_cache[cache_key]

    result = tmdb_service.discover_movies(api_key, filters, page, region=region)

    if result:
        with _cache_lock:
            _discover_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached {len(result)} items")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def discover_tv_cached(api_key: str, filters: dict = None, page: int = 1) -> list:
    """
    Discover TV shows with caching.
    Region is automatically fetched from ServiceConfig if configured.

    Args:
        api_key: TMDB API key
        filters: Optional filter parameters
        page: Page number

    Returns:
        list: List of discovered TV show dicts
    """
    region = _get_tmdb_region()
    filter_hash = _hash_filters(filters)
    cache_key = f"discover_tv:{filter_hash}:{page}:{region or 'WW'}"

    with _cache_lock:
        if cache_key in _discover_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _discover_cache[cache_key]

    result = tmdb_service.discover_tv(api_key, filters, page, region=region)

    if result:
        with _cache_lock:
            _discover_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached {len(result)} items")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def get_movie_details_cached(tmdb_id: int, api_key: str) -> dict:
    """
    Get movie details with caching.

    Args:
        tmdb_id: TMDB movie ID
        api_key: TMDB API key

    Returns:
        dict: Movie details
    """
    cache_key = f"movie_details:{tmdb_id}"

    with _cache_lock:
        if cache_key in _details_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _details_cache[cache_key]

    result = tmdb_service.get_movie_details(tmdb_id, api_key)

    if result:
        with _cache_lock:
            _details_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached movie details")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def get_tv_details_cached(tmdb_id: int, api_key: str) -> dict:
    """
    Get TV show details with caching.

    Args:
        tmdb_id: TMDB TV show ID
        api_key: TMDB API key

    Returns:
        dict: TV show details
    """
    cache_key = f"tv_details:{tmdb_id}"

    with _cache_lock:
        if cache_key in _details_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _details_cache[cache_key]

    result = tmdb_service.get_tv_details(tmdb_id, api_key)

    if result:
        with _cache_lock:
            _details_cache[cache_key] = result
        logger.debug(f"Cache MISS for {cache_key} - cached TV details")
    else:
        logger.debug(f"Cache MISS for {cache_key} - empty result, not cached")

    return result


def get_cache_stats() -> dict:
    """
    Get statistics for all TMDB caches.

    Returns:
        dict: Dictionary with cache statistics for each cache type
    """
    with _cache_lock:
        return {
            "trending": {
                "size": len(_trending_cache),
                "maxsize": _trending_cache.maxsize,
                "ttl": TTL_TRENDING,
            },
            "popular": {
                "size": len(_popular_cache),
                "maxsize": _popular_cache.maxsize,
                "ttl": TTL_POPULAR,
            },
            "discover": {
                "size": len(_discover_cache),
                "maxsize": _discover_cache.maxsize,
                "ttl": TTL_DISCOVER,
            },
            "details": {
                "size": len(_details_cache),
                "maxsize": _details_cache.maxsize,
                "ttl": TTL_DETAILS,
            },
        }


def clear_all_caches() -> None:
    """
    Clear all TMDB caches.

    This function removes all cached entries from all TMDB caches.
    Useful for forcing fresh data fetch or freeing memory.
    """
    with _cache_lock:
        _trending_cache.clear()
        _popular_cache.clear()
        _discover_cache.clear()
        _details_cache.clear()
        logger.info("All TMDB caches cleared")
