"""
Radarr API service module.

Shared functions (quality profiles, root folders, tags, etc.) are delegated
to arr_service.py. This module contains Radarr-specific functions.
"""

import logging

from listarr.services.arr_service import (
    arr_api_get,
    validate_api_key,
)
from listarr.services.arr_service import (
    create_or_get_tag_id as create_or_get_tag_id,
)
from listarr.services.arr_service import (
    get_quality_profiles as get_quality_profiles,
)
from listarr.services.arr_service import (
    get_root_folders as get_root_folders,
)
from listarr.services.arr_service import (
    get_system_status as get_system_status,
)
from listarr.services.arr_service import (
    get_tags as get_tags,
)
from listarr.services.http_client import ADD_TIMEOUT, BULK_TIMEOUT, DEFAULT_TIMEOUT, http_session, normalize_url

logger = logging.getLogger(__name__)


def validate_radarr_api_key(base_url: str, api_key: str) -> bool:
    """
    Validates Radarr API URL and API key by calling the /api/v3/system/status endpoint.

    Args:
        base_url: Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key: Radarr API key from Settings > General.

    Returns:
        True if valid, False otherwise.
    """
    return validate_api_key(base_url, api_key)


def get_radarr_system_status(base_url: str, api_key: str) -> dict:
    """Fetches system status from Radarr. Alias for dashboard_cache compatibility."""
    return get_system_status(base_url, api_key)


def get_movie_count(base_url: str, api_key: str) -> int:
    """
    Fetches the total count of movies from Radarr.

    Args:
        base_url: Base URL of Radarr.
        api_key: Radarr API key.

    Returns:
        Total number of movies, or 0 on error.
    """
    movies = arr_api_get(base_url, api_key, "movie")
    if movies is None:
        return 0
    return len(movies) if movies else 0


def get_missing_movies_count(base_url: str, api_key: str) -> int:
    """
    Fetches the count of missing movies from Radarr.
    Missing movies are those that are monitored but don't have a file.

    Args:
        base_url: Base URL of Radarr.
        api_key: Radarr API key.

    Returns:
        Total number of missing movies, or 0 on error.
    """
    movies = arr_api_get(base_url, api_key, "movie")
    if not movies:
        return 0

    missing_count = sum(
        1
        for movie in movies
        if movie.get("monitored", False) and "hasFile" in movie and not movie.get("hasFile", False)
    )
    return missing_count


def get_existing_movie_tmdb_ids(base_url: str, api_key: str) -> set[int] | None:
    """
    Fetches all TMDB IDs of movies currently in Radarr.
    Used for pre-flight duplicate detection.

    Args:
        base_url: Base URL of Radarr.
        api_key: Radarr API key.

    Returns:
        Set of TMDB IDs, or None on API error (distinguishes from empty library).
    """
    movies = arr_api_get(base_url, api_key, "movie")
    if movies is None:
        return None
    return {m.get("tmdbId") for m in movies if m.get("tmdbId")}


def get_exclusions(base_url: str, api_key: str) -> set[int]:
    """
    Fetch excluded TMDB IDs from Radarr's exclusion list.

    Args:
        base_url: Base URL of Radarr.
        api_key: Radarr API key.

    Returns:
        Set of excluded TMDB IDs, empty set on error.
    """
    exclusions = arr_api_get(base_url, api_key, "exclusions")
    if not exclusions:
        return set()
    return {e.get("tmdbId") for e in exclusions if e.get("tmdbId")}


def lookup_movie(base_url: str, api_key: str, tmdb_id: int) -> dict | None:
    """
    Look up a movie in Radarr by TMDB ID.

    Args:
        base_url: Base URL of Radarr.
        api_key: Radarr API key.
        tmdb_id: TMDB movie ID to look up.

    Returns:
        Movie data suitable for add_movie(), or None if not found.
    """
    url = f"{normalize_url(base_url)}/api/v3/movie/lookup"
    headers = {"X-Api-Key": api_key}
    params = {"term": f"tmdb:{tmdb_id}"}

    try:
        logger.debug(f"Looking up movie with TMDB ID: {tmdb_id}")
        response = http_session.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        results = response.json()
        if results:
            return results[0]
        return None
    except Exception as e:
        logger.error(f"Error looking up movie by TMDB ID {tmdb_id}: {e}", exc_info=True)
        return None


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
        base_url: Base URL of Radarr.
        api_key: Radarr API key.
        movie_data: Movie dict from lookup_movie().
        root_folder: Path string (e.g., "/movies").
        quality_profile_id: Integer ID of quality profile.
        monitored: Whether to monitor the movie (default: True).
        search_on_add: Whether to search immediately after adding (default: True).
        tags: List of tag IDs (optional).

    Returns:
        Added movie data from Radarr.

    Raises:
        Exception: On API error (caller should handle).
    """
    url = f"{normalize_url(base_url)}/api/v3/movie"
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    title = movie_data.get("title", "Unknown")
    tmdb_id = movie_data.get("tmdbId", "Unknown")
    logger.info(f"Adding movie: {title} (TMDB: {tmdb_id})")

    payload = {
        "title": movie_data.get("title"),
        "tmdbId": movie_data.get("tmdbId"),
        "year": movie_data.get("year"),
        "qualityProfileId": quality_profile_id,
        "titleSlug": movie_data.get("titleSlug"),
        "images": movie_data.get("images", []),
        "rootFolderPath": root_folder,
        "monitored": monitored,
        "addOptions": {"searchForMovie": search_on_add},
        "tags": tags or [],
    }

    response = http_session.post(url, headers=headers, json=payload, timeout=ADD_TIMEOUT)
    if not response.ok:
        logger.error(f"Radarr API error adding movie {title} ({response.status_code}): {response.text}")
    response.raise_for_status()
    return response.json()


def bulk_add_movies(
    base_url: str,
    api_key: str,
    movie_payloads: list[dict],
) -> dict:
    """
    Add multiple movies to Radarr using bulk import endpoint.

    Args:
        base_url: Base URL of Radarr.
        api_key: Radarr API key.
        movie_payloads: List of movie payload dicts (pre-built with all required fields).

    Returns:
        List of added movie data from Radarr.

    Raises:
        Exception: On API error (caller should handle).
    """
    url = f"{normalize_url(base_url)}/api/v3/movie/import"
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    logger.info(f"Bulk adding {len(movie_payloads)} movies to Radarr")

    try:
        response = http_session.post(url, headers=headers, json=movie_payloads, timeout=BULK_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        status = response.status_code if "response" in locals() else "N/A"
        error_text = response.text if "response" in locals() else str(e)
        logger.error(f"Bulk import failed ({status}): {error_text}", exc_info=True)
        if "response" in locals():
            response.raise_for_status()
        raise
