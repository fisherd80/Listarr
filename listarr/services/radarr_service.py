import logging
from pyarr import RadarrAPI

logger = logging.getLogger(__name__)


def validate_radarr_api_key(base_url: str, api_key: str, timeout: int = 5):
    """
    Validates Radarr API URL and API key by calling the /api/v3/system/status endpoint.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.
        timeout (int): Timeout in seconds for the request.

    Returns:
        bool: True if valid, False otherwise.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        radarr = RadarrAPI(host_url=base_url, api_key=api_key)
        radarr.get_system_status()
        return True
    except Exception:
        return False


def get_quality_profiles(base_url: str, api_key: str):
    """
    Fetches quality profiles from Radarr.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        list: List of quality profile dicts with 'id' and 'name' keys, or empty list on error.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        radarr = RadarrAPI(host_url=base_url, api_key=api_key)
        profiles = radarr.get_quality_profile()
        return [{"id": p["id"], "name": p["name"]} for p in profiles]
    except Exception as e:
        logger.error(f"Error fetching quality profiles: {e}", exc_info=True)
        return []


def get_root_folders(base_url: str, api_key: str):
    """
    Fetches root folders from Radarr.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        list: List of root folder dicts with 'id' and 'path' keys, or empty list on error.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        radarr = RadarrAPI(host_url=base_url, api_key=api_key)
        folders = radarr.get_root_folder()
        return [{"id": f["id"], "path": f["path"]} for f in folders]
    except Exception as e:
        logger.error(f"Error fetching root folders: {e}", exc_info=True)
        return []


def get_system_status(base_url: str, api_key: str):
    """
    Fetches system status information from Radarr for dashboard display.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        dict: System status information with keys: version, instance_name, is_production, is_debug.
              Returns empty dict on error.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        radarr = RadarrAPI(host_url=base_url, api_key=api_key)
        status = radarr.get_system_status()
        return {
            "version": status.get("version"),
            "instance_name": status.get("instanceName"),
            "is_production": status.get("isProduction", False),
            "is_debug": status.get("isDebug", False)
        }
    except Exception as e:
        logger.error(f"Error fetching system status: {e}", exc_info=True)
        return {}


def get_movie_count(base_url: str, api_key: str):
    """
    Fetches the total count of movies from Radarr.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        int: Total number of movies, or 0 on error.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        radarr = RadarrAPI(host_url=base_url, api_key=api_key)
        movies = radarr.get_movie()
        return len(movies) if movies else 0
    except Exception as e:
        logger.error(f"Error fetching movie count: {e}", exc_info=True)
        return 0


def get_tags(base_url: str, api_key: str):
    """
    Fetches tags from Radarr.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        list: List of tag dicts with 'id' and 'label' keys, or empty list on error.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        radarr = RadarrAPI(host_url=base_url, api_key=api_key)
        tags = radarr.get_tag()
        return [{"id": t["id"], "label": t["label"]} for t in tags]
    except Exception as e:
        logger.error(f"Error fetching tags: {e}", exc_info=True)
        return []


def get_missing_movies_count(base_url: str, api_key: str):
    """
    Fetches the count of missing movies from Radarr.
    Missing movies are those that are monitored but don't have a file.

    Args:
        base_url (str): Base URL of Radarr (e.g., "http://localhost:7878/").
        api_key (str): Radarr API key from Settings > General.

    Returns:
        int: Total number of missing movies, or 0 on error.
    """
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

    try:
        radarr = RadarrAPI(host_url=base_url, api_key=api_key)
        movies = radarr.get_movie()
        if not movies:
            return 0

        # Count movies that are monitored but don't have a file
        # If hasFile field is missing, treat as having a file (not missing)
        missing_count = sum(
            1 for movie in movies
            if movie.get("monitored", False) and "hasFile" in movie and not movie.get("hasFile", False)
        )
        return missing_count
    except Exception as e:
        logger.error(f"Error fetching missing movies count: {e}", exc_info=True)
        return 0


def create_or_get_tag_id(base_url: str, api_key: str, tag_label: str):
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
    # Ensure base_url ends with a slash
    if not base_url.endswith("/"):
        base_url += "/"

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

    try:
        radarr = RadarrAPI(host_url=base_url, api_key=api_key)

        # Fetch all existing tags
        tags = radarr.get_tag()

        # Search for existing tag (case-insensitive match)
        for tag in tags:
            if tag.get("label", "").lower() == normalized_label:
                return tag["id"]

        # Tag not found, create new one
        new_tag = radarr.create_tag(label=normalized_label)
        return new_tag["id"]
    except Exception as e:
        logger.error(f"Error creating/fetching tag '{tag_label}': {e}", exc_info=True)
        return None

