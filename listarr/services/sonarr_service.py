"""
Sonarr API integration using direct HTTP calls.

All functions use the shared HTTP client for consistent timeout handling,
retry behavior, and connection reuse.
"""

import logging

import requests

from listarr.services.http_client import DEFAULT_TIMEOUT, http_session, normalize_url

logger = logging.getLogger(__name__)


def validate_sonarr_api_key(base_url: str, api_key: str):
    """
    Validates Sonarr API URL and API key by calling the /api/v3/system/status endpoint.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

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


def get_quality_profiles(base_url: str, api_key: str):
    """
    Fetches quality profiles from Sonarr.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

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


def get_root_folders(base_url: str, api_key: str):
    """
    Fetches root folders from Sonarr.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

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


def get_system_status(base_url: str, api_key: str):
    """
    Fetches system status information from Sonarr for dashboard display.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

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


def get_series_count(base_url: str, api_key: str):
    """
    Fetches the total count of series from Sonarr.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

    Returns:
        int: Total number of series, or 0 on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/series"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        series = response.json()
        return len(series) if series else 0
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching series count: {e}", exc_info=True)
        return 0


def get_tags(base_url: str, api_key: str):
    """
    Fetches tags from Sonarr.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

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


def get_missing_series_count(base_url: str, api_key: str):
    """
    Fetches the count of series with missing episodes from Sonarr.
    Uses the /api/v3/wanted/missing endpoint which directly returns missing episodes,
    making this much more efficient than checking all series individually.
    A series is considered "missing" if it has at least one monitored episode without a file.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

    Returns:
        int: Total number of series with missing episodes, or 0 on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/wanted/missing"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        wanted_response = response.json()

        if not wanted_response:
            return 0

        # Extract records from response
        records = wanted_response.get("records", [])
        if not records:
            return 0

        # Extract unique series IDs from missing episodes
        # Each episode should have a 'seriesId' field
        unique_series_ids = set()
        for episode in records:
            # Try to get seriesId from episode directly
            series_id = episode.get("seriesId")
            if series_id:
                unique_series_ids.add(series_id)
            else:
                # Fallback: try to get from nested series object if include_series was True
                series = episode.get("series")
                if series and series.get("id"):
                    unique_series_ids.add(series.get("id"))

        return len(unique_series_ids)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching missing series count: {e}", exc_info=True)
        return 0


def get_missing_episodes_count(base_url: str, api_key: str):
    """
    Fetches the total count of missing episodes from Sonarr.
    Uses the /api/v3/wanted/missing endpoint which directly returns missing episodes.
    The response includes a 'totalRecords' field with the count.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

    Returns:
        int: Total number of missing episodes, or 0 on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/wanted/missing"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        wanted_response = response.json()

        if not wanted_response:
            return 0

        # The response includes 'totalRecords' field with the count
        total_records = wanted_response.get("totalRecords", 0)
        return int(total_records) if total_records is not None else 0
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching missing episodes count: {e}", exc_info=True)
        return 0


def get_existing_series_tvdb_ids(base_url: str, api_key: str) -> set[int]:
    """
    Fetches all TVDB IDs of series currently in Sonarr.
    Used for pre-flight duplicate detection.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

    Returns:
        set[int]: Set of TVDB IDs, empty set on error.
    """
    url = f"{normalize_url(base_url)}/api/v3/series"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        series = response.json()
        return {s.get("tvdbId") for s in series if s.get("tvdbId")}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching existing series TVDB IDs: {e}", exc_info=True)
        return set()


def lookup_series(base_url: str, api_key: str, tvdb_id: int) -> dict | None:
    """
    Look up a series in Sonarr by TVDB ID.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.
        tvdb_id (int): TVDB series ID to look up.

    Returns:
        dict: Series data suitable for add_series(), or None if not found.
    """
    url = f"{normalize_url(base_url)}/api/v3/series/lookup"
    headers = {"X-Api-Key": api_key}
    params = {"term": f"tvdb:{tvdb_id}"}

    try:
        logger.debug(f"Looking up series with TVDB ID: {tvdb_id}")
        response = http_session.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        results = response.json()
        if results:
            return results[0]
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error looking up series by TVDB ID {tvdb_id}: {e}", exc_info=True)
        return None


def add_series(
    base_url: str,
    api_key: str,
    series_data: dict,
    root_folder: str,
    quality_profile_id: int,
    monitored: bool = True,
    season_folder: bool = True,
    search_on_add: bool = True,
    tags: list[int] = None,
) -> dict:
    """
    Add a series to Sonarr.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.
        series_data (dict): Series dict from lookup_series().
        root_folder (str): Path string (e.g., "/tv").
        quality_profile_id (int): Integer ID of quality profile.
        monitored (bool): Whether to monitor the series (default: True).
        season_folder (bool): Whether to use season folders (default: True).
        search_on_add (bool): Whether to search for missing episodes after adding (default: True).
        tags (list[int]): List of tag IDs (optional).

    Returns:
        dict: Added series data from Sonarr.

    Raises:
        Exception: On API error (caller should handle).
    """
    url = f"{normalize_url(base_url)}/api/v3/series"
    headers = {"X-Api-Key": api_key}

    title = series_data.get("title", "Unknown")
    tvdb_id = series_data.get("tvdbId", "Unknown")
    logger.info(f"Adding series: {title} (TVDB: {tvdb_id})")

    # Build the series payload
    series_payload = series_data.copy()
    series_payload["rootFolderPath"] = root_folder
    series_payload["qualityProfileId"] = quality_profile_id
    series_payload["monitored"] = monitored
    series_payload["seasonFolder"] = season_folder
    series_payload["tags"] = tags or []
    series_payload["addOptions"] = {"searchForMissingEpisodes": search_on_add}

    response = http_session.post(url, json=series_payload, headers=headers, timeout=DEFAULT_TIMEOUT)

    if response.status_code == 201:
        return response.json()
    else:
        error_msg = response.text
        raise Exception(f"Sonarr API error ({response.status_code}): {error_msg}")


def create_or_get_tag_id(base_url: str, api_key: str, tag_label: str):
    """
    Creates a tag in Sonarr if it doesn't exist, or returns existing tag ID.
    Normalizes tag label to lowercase with hyphens (Radarr/Sonarr requirement).

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.
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
    url = f"{base}/api/v3/tag"
    headers = {"X-Api-Key": api_key}

    try:
        # Fetch all existing tags
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        tags = response.json()

        # Search for existing tag (case-insensitive match)
        for tag in tags:
            if tag.get("label", "").lower() == normalized_label:
                return tag["id"]

        # Tag not found, create new one
        create_response = http_session.post(
            url,
            json={"label": normalized_label},
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        create_response.raise_for_status()
        new_tag = create_response.json()
        return new_tag["id"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating/fetching tag '{tag_label}': {e}", exc_info=True)
        return None
