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
TTL_TRENDING = 3600      # 1 hour - trending data changes frequently
TTL_POPULAR = 14400      # 4 hours - popular lists update less often
TTL_DISCOVER = 21600     # 6 hours - discover results are relatively stable
TTL_DETAILS = 86400      # 24 hours - movie/TV details rarely change

# Cache instances with TTL
_trending_cache: TTLCache = TTLCache(maxsize=100, ttl=TTL_TRENDING)
_popular_cache: TTLCache = TTLCache(maxsize=100, ttl=TTL_POPULAR)
_discover_cache: TTLCache = TTLCache(maxsize=500, ttl=TTL_DISCOVER)
_details_cache: TTLCache = TTLCache(maxsize=1000, ttl=TTL_DETAILS)

# Single lock for thread-safe cache operations
_cache_lock = threading.Lock()


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
    return hashlib.md5(filter_str.encode()).hexdigest()


def get_trending_movies_cached(api_key: str, time_window: str = 'week', page: int = 1) -> list:
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


def get_trending_tv_cached(api_key: str, time_window: str = 'week', page: int = 1) -> list:
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

    Args:
        api_key: TMDB API key
        page: Page number

    Returns:
        list: List of popular movie dicts
    """
    cache_key = f"popular_movies:{page}"

    with _cache_lock:
        if cache_key in _popular_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _popular_cache[cache_key]

    result = tmdb_service.get_popular_movies(api_key, page)

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


def discover_movies_cached(api_key: str, filters: dict = None, page: int = 1) -> list:
    """
    Discover movies with caching.

    Args:
        api_key: TMDB API key
        filters: Optional filter parameters
        page: Page number

    Returns:
        list: List of discovered movie dicts
    """
    filter_hash = _hash_filters(filters)
    cache_key = f"discover_movies:{filter_hash}:{page}"

    with _cache_lock:
        if cache_key in _discover_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _discover_cache[cache_key]

    result = tmdb_service.discover_movies(api_key, filters, page)

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

    Args:
        api_key: TMDB API key
        filters: Optional filter parameters
        page: Page number

    Returns:
        list: List of discovered TV show dicts
    """
    filter_hash = _hash_filters(filters)
    cache_key = f"discover_tv:{filter_hash}:{page}"

    with _cache_lock:
        if cache_key in _discover_cache:
            logger.debug(f"Cache HIT for {cache_key}")
            return _discover_cache[cache_key]

    result = tmdb_service.discover_tv(api_key, filters, page)

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
