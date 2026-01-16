import logging
from pyarr import SonarrAPI

logger = logging.getLogger(__name__)


def validate_sonarr_api_key(base_url: str, api_key: str, timeout: int = 5):
    """
    Validates Sonarr API URL and API key by calling the /api/v3/system/status endpoint.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.
        timeout (int): Timeout in seconds for the request.

    Returns:
        bool: True if valid, False otherwise.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        sonarr = SonarrAPI(host_url=base_url, api_key=api_key)
        sonarr.get_system_status()
        return True
    except Exception:
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
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        sonarr = SonarrAPI(host_url=base_url, api_key=api_key)
        profiles = sonarr.get_quality_profile()
        return [{"id": p["id"], "name": p["name"]} for p in profiles]
    except Exception as e:
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
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        sonarr = SonarrAPI(host_url=base_url, api_key=api_key)
        folders = sonarr.get_root_folder()
        return [{"id": f["id"], "path": f["path"]} for f in folders]
    except Exception as e:
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
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        sonarr = SonarrAPI(host_url=base_url, api_key=api_key)
        status = sonarr.get_system_status()
        return {
            "version": status.get("version"),
            "instance_name": status.get("instanceName"),
            "is_production": status.get("isProduction", False),
            "is_debug": status.get("isDebug", False)
        }
    except Exception as e:
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
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        sonarr = SonarrAPI(host_url=base_url, api_key=api_key)
        series = sonarr.get_series()
        return len(series) if series else 0
    except Exception as e:
        logger.error(f"Error fetching series count: {e}", exc_info=True)
        return 0


def get_missing_series_count(base_url: str, api_key: str):
    """
    Fetches the count of series with missing episodes from Sonarr.
    Uses Pyarr's get_wanted() function which directly returns missing episodes,
    making this much more efficient than checking all series individually.
    A series is considered "missing" if it has at least one monitored episode without a file.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

    Returns:
        int: Total number of series with missing episodes, or 0 on error.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        sonarr = SonarrAPI(host_url=base_url, api_key=api_key)
        # Use get_wanted() to directly fetch missing episodes
        # This is much more efficient than iterating through all series
        wanted_response = sonarr.get_wanted()
        
        if not wanted_response:
            return 0
        
        # Extract records from response (get_wanted returns a dict with 'records' key)
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
    except Exception as e:
        logger.error(f"Error fetching missing series count: {e}", exc_info=True)
        return 0


def get_missing_episodes_count(base_url: str, api_key: str):
    """
    Fetches the total count of missing episodes from Sonarr.
    Uses Pyarr's get_wanted() function which directly returns missing episodes.
    The response includes a 'totalRecords' field with the count.

    Args:
        base_url (str): Base URL of Sonarr (e.g., "http://localhost:8989/").
        api_key (str): Sonarr API key from Settings > General.

    Returns:
        int: Total number of missing episodes, or 0 on error.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        sonarr = SonarrAPI(host_url=base_url, api_key=api_key)
        # Use get_wanted() to directly fetch missing episodes
        wanted_response = sonarr.get_wanted()
        
        if not wanted_response:
            return 0
        
        # The get_wanted() response includes 'totalRecords' field with the count
        total_records = wanted_response.get("totalRecords", 0)
        return int(total_records) if total_records is not None else 0
    except Exception as e:
        logger.error(f"Error fetching missing episodes count: {e}", exc_info=True)
        return 0
