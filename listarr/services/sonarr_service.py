"""
Sonarr API service module.

Shared functions (quality profiles, root folders, tags, etc.) are delegated
to arr_service.py. This module contains Sonarr-specific functions.
"""

import logging

from requests.exceptions import RequestException

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


def validate_sonarr_api_key(base_url: str, api_key: str) -> bool:
    """
    Validates Sonarr API URL and API key by calling the /api/v3/system/status endpoint.

    Args:
        base_url: Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key: Sonarr API key from Settings > General.

    Returns:
        True if valid, False otherwise.
    """
    return validate_api_key(base_url, api_key)


def get_sonarr_system_status(base_url: str, api_key: str) -> dict:
    """Fetches system status from Sonarr. Alias for dashboard_cache compatibility."""
    return get_system_status(base_url, api_key)


def get_series_count(base_url: str, api_key: str) -> int:
    """
    Fetches the total count of series from Sonarr.

    Args:
        base_url: Base URL of Sonarr.
        api_key: Sonarr API key.

    Returns:
        Total number of series, or 0 on error.
    """
    series = arr_api_get(base_url, api_key, "series")
    if series is None:
        return 0
    return len(series) if series else 0


def get_missing_series_count(base_url: str, api_key: str) -> int:
    """
    Fetches the count of series with missing episodes from Sonarr.
    Uses the /api/v3/wanted/missing endpoint.

    Args:
        base_url: Base URL of Sonarr.
        api_key: Sonarr API key.

    Returns:
        Total number of series with missing episodes, or 0 on error.
    """
    wanted_response = arr_api_get(base_url, api_key, "wanted/missing")
    if not wanted_response:
        return 0

    records = wanted_response.get("records", [])
    if not records:
        return 0

    unique_series_ids = set()
    for episode in records:
        series_id = episode.get("seriesId")
        if series_id:
            unique_series_ids.add(series_id)
        else:
            series = episode.get("series")
            if series and series.get("id"):
                unique_series_ids.add(series.get("id"))

    return len(unique_series_ids)


def get_missing_episodes_count(base_url: str, api_key: str) -> int:
    """
    Fetches the total count of missing episodes from Sonarr.
    Uses the /api/v3/wanted/missing endpoint totalRecords field.

    Args:
        base_url: Base URL of Sonarr.
        api_key: Sonarr API key.

    Returns:
        Total number of missing episodes, or 0 on error.
    """
    wanted_response = arr_api_get(base_url, api_key, "wanted/missing")
    if not wanted_response:
        return 0

    total_records = wanted_response.get("totalRecords", 0)
    return int(total_records) if total_records is not None else 0


def get_existing_series_tvdb_ids(base_url: str, api_key: str) -> set[int] | None:
    """
    Fetches all TVDB IDs of series currently in Sonarr.
    Used for pre-flight duplicate detection.

    Args:
        base_url: Base URL of Sonarr.
        api_key: Sonarr API key.

    Returns:
        Set of TVDB IDs, or None on API error (distinguishes from empty library).
    """
    series = arr_api_get(base_url, api_key, "series")
    if series is None:
        return None
    return {s.get("tvdbId") for s in series if s.get("tvdbId")}


def get_exclusions(base_url: str, api_key: str) -> set[int]:
    """
    Fetch excluded TVDB IDs from Sonarr's import list exclusion.

    Args:
        base_url: Base URL of Sonarr.
        api_key: Sonarr API key.

    Returns:
        Set of excluded TVDB IDs, empty set on error.
    """
    exclusions = arr_api_get(base_url, api_key, "importlistexclusion")
    if not exclusions:
        return set()
    return {e.get("tvdbId") for e in exclusions if e.get("tvdbId")}


def lookup_series(base_url: str, api_key: str, tvdb_id: int) -> dict | None:
    """
    Look up a series in Sonarr by TVDB ID.

    Args:
        base_url: Base URL of Sonarr.
        api_key: Sonarr API key.
        tvdb_id: TVDB series ID to look up.

    Returns:
        Series data suitable for add_series(), or None if not found.
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
    except RequestException as e:
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
        base_url: Base URL of Sonarr.
        api_key: Sonarr API key.
        series_data: Series dict from lookup_series().
        root_folder: Path string (e.g., "/tv").
        quality_profile_id: Integer ID of quality profile.
        monitored: Whether to monitor the series (default: True).
        season_folder: Whether to use season folders (default: True).
        search_on_add: Whether to search for missing episodes after adding (default: True).
        tags: List of tag IDs (optional).

    Returns:
        Added series data from Sonarr.

    Raises:
        Exception: On API error (caller should handle).
    """
    url = f"{normalize_url(base_url)}/api/v3/series"
    headers = {"X-Api-Key": api_key}

    title = series_data.get("title", "Unknown")
    tvdb_id = series_data.get("tvdbId", "Unknown")
    logger.info(f"Adding series: {title} (TVDB: {tvdb_id})")

    series_payload = {
        "title": series_data.get("title"),
        "tvdbId": series_data.get("tvdbId"),
        "year": series_data.get("year"),
        "qualityProfileId": quality_profile_id,
        "titleSlug": series_data.get("titleSlug"),
        "images": series_data.get("images", []),
        "seasons": series_data.get("seasons", []),
        "rootFolderPath": root_folder,
        "monitored": monitored,
        "seasonFolder": season_folder,
        "addOptions": {"searchForMissingEpisodes": search_on_add},
        "tags": tags or [],
    }

    response = http_session.post(url, json=series_payload, headers=headers, timeout=ADD_TIMEOUT)

    if response.status_code == 201:
        return response.json()
    else:
        error_msg = response.text
        raise Exception(f"Sonarr API error ({response.status_code}): {error_msg}")


def bulk_add_series(
    base_url: str,
    api_key: str,
    series_payloads: list[dict],
) -> dict:
    """
    Add multiple series to Sonarr using bulk import endpoint.

    Args:
        base_url: Base URL of Sonarr.
        api_key: Sonarr API key.
        series_payloads: List of series payload dicts (pre-built with all required fields).

    Returns:
        List of added series data from Sonarr.

    Raises:
        Exception: On API error (caller should handle).
    """
    url = f"{normalize_url(base_url)}/api/v3/series/import"
    headers = {"X-Api-Key": api_key}

    logger.info(f"Bulk adding {len(series_payloads)} series to Sonarr")

    try:
        response = http_session.post(url, json=series_payloads, headers=headers, timeout=BULK_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        if "response" in locals() and hasattr(response, "status_code"):
            logger.error(f"Bulk import failed ({response.status_code}): {response.text}", exc_info=True)
            raise Exception(f"Sonarr API error ({response.status_code}): {response.text}")
        else:
            logger.error(f"Bulk import failed: {e}", exc_info=True)
            raise
