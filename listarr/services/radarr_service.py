"""
Radarr API service module using direct HTTP calls.

All external API calls use the shared HTTP session from http_client.py
for consistent timeout handling, retry behavior, and connection reuse.
"""

import logging

import requests

from listarr.services.http_client import (
    DEFAULT_TIMEOUT,
    http_session,
    normalize_url,
)

logger = logging.getLogger(__name__)


def validate_radarr_api_key(base_url: str, api_key: str) -> bool:
    """
    Validates Radarr API URL and API key by calling the /api/v3/system/status endpoint.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        bool: True if valid, False otherwise.
    """
    url = f"{normalize_url(base_url)}/api/v3/system/status"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def get_quality_profiles(base_url: str, api_key: str) -> list:
    """
    Fetches quality profiles from Radarr.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        list: List of quality profile dicts with 'id' and 'name' keys, or empty list on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/qualityprofile"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        profiles = response.json()
        return [{"id": p["id"], "name": p["name"]} for p in profiles]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching quality profiles: {e}", exc_info=True)
        return []


def get_root_folders(base_url: str, api_key: str) -> list:
    """
    Fetches root folders from Radarr.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        list: List of root folder dicts with 'id' and 'path' keys, or empty list on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/rootfolder"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        folders = response.json()
        return [{"id": f["id"], "path": f["path"]} for f in folders]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching root folders: {e}", exc_info=True)
        return []


def get_system_status(base_url: str, api_key: str) -> dict:
    """
    Fetches system status information from Radarr for dashboard display.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        dict: System status information with keys: version, instance_name, is_production, is_debug.
              Returns empty dict on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/system/status"
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


def get_movie_count(base_url: str, api_key: str) -> int:
    """
    Fetches the total count of movies from Radarr.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        int: Total number of movies, or 0 on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/movie"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        movies = response.json()
        return len(movies) if movies else 0
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching movie count: {e}", exc_info=True)
        return 0


def get_tags(base_url: str, api_key: str) -> list:
    """
    Fetches tags from Radarr.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        list: List of tag dicts with 'id' and 'label' keys, or empty list on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/tag"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        tags = response.json()
        return [{"id": t["id"], "label": t["label"]} for t in tags]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching tags: {e}", exc_info=True)
        return []


def get_missing_movies_count(base_url: str, api_key: str) -> int:
    """
    Fetches the count of missing movies from Radarr.
    Missing movies are those that are monitored but don't have a file.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        int: Total number of missing movies, or 0 on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/movie"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        movies = response.json()
        if not movies:
            return 0

        # Count movies that are monitored but don't have a file
        # If hasFile field is missing, treat as having a file (not missing)
        missing_count = sum(
            1
            for movie in movies
            if movie.get("monitored", False) and "hasFile" in movie and not movie.get("hasFile", False)
        )
        return missing_count
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching missing movies count: {e}", exc_info=True)
        return 0


def get_existing_movie_tmdb_ids(base_url: str, api_key: str) -> set[int]:
    """
    Fetches all TMDB IDs of movies currently in Radarr.
    Used for pre-flight duplicate detection.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        set[int]: Set of TMDB IDs, empty set on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/movie"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        movies = response.json()
        return {m.get("tmdbId") for m in movies if m.get("tmdbId")}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching existing movie TMDB IDs: {e}", exc_info=True)
        return set()


def lookup_movie(base_url: str, api_key: str, tmdb_id: int) -> dict | None:
    """
    Look up a movie in Radarr by TMDB ID.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.
        tmdb_id (int): TMDB movie ID to look up.

    Returns:
        dict: Movie data suitable for add_movie(), or None if not found.
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
    except requests.exceptions.RequestException as e:
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
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.
        movie_data (dict): Movie dict from lookup_movie().
        root_folder (str): Path string (e.g., "/movies").
        quality_profile_id (int): Integer ID of quality profile.
        monitored (bool): Whether to monitor the movie (default: True).
        search_on_add (bool): Whether to search immediately after adding (default: True).
        tags (list[int]): List of tag IDs (optional).

    Returns:
        dict: Added movie data from Radarr.

    Raises:
        Exception: On API error (caller should handle).
    """
    url = f"{normalize_url(base_url)}/api/v3/movie"
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    title = movie_data.get("title", "Unknown")
    tmdb_id = movie_data.get("tmdbId", "Unknown")
    logger.info(f"Adding movie: {title} (TMDB: {tmdb_id})")

    # Build payload from movie_data
    payload = movie_data.copy()
    payload["rootFolderPath"] = root_folder
    payload["qualityProfileId"] = quality_profile_id
    payload["monitored"] = monitored
    payload["tags"] = tags or []
    payload["addOptions"] = {"searchForMovie": search_on_add}

    response = http_session.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def create_or_get_tag_id(base_url: str, api_key: str, tag_label: str) -> int | None:
    """
    Creates a tag in Radarr if it doesn't exist, or returns existing tag ID.
    Normalizes tag label to lowercase with hyphens (Radarr/Sonarr requirement).

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.
        tag_label (str): Tag label to create or find.

    Returns:
        int or None: Tag ID if successful, None on error or if label is empty.
    """
    # Normalize tag label
    # 1. Convert to lowercase
    # 2. Replace spaces with hyphens
    # 3. Remove consecutive hyphens
    # 4. Strip leading/trailing hyphens
    normalized_label = tag_label.lower().replace(" ", "-")
    # Remove consecutive hyphens
    while "--" in normalized_label:
        normalized_label = normalized_label.replace("--", "-")
    normalized_label = normalized_label.strip("-")

    # Return None if normalized label is empty
    if not normalized_label:
        return None

    base = normalize_url(base_url)
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    try:
        # Fetch all existing tags
        get_url = f"{base}/api/v3/tag"
        response = http_session.get(get_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        tags = response.json()

        # Search for existing tag (case-insensitive match)
        for tag in tags:
            if tag.get("label", "").lower() == normalized_label:
                return tag["id"]

        # Tag not found, create new one
        post_url = f"{base}/api/v3/tag"
        response = http_session.post(
            post_url, headers=headers, json={"label": normalized_label}, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        new_tag = response.json()
        return new_tag["id"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating/fetching tag '{tag_label}': {e}", exc_info=True)
        return None
