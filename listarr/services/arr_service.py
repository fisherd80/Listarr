"""
Shared *arr service helpers for Radarr and Sonarr.

Contains functions that are identical between Radarr and Sonarr,
reducing code duplication across the service modules.
"""

import logging

import requests

from listarr.services.http_client import DEFAULT_TIMEOUT, http_session, normalize_url

logger = logging.getLogger(__name__)


def arr_api_get(base_url: str, api_key: str, endpoint: str) -> dict | list | None:
    """
    Make a GET request to an *arr API v3 endpoint.

    Args:
        base_url: Base URL of the service
        api_key: API key for authentication
        endpoint: API endpoint (e.g., "qualityprofile", "rootfolder")

    Returns:
        JSON response data, or None on error
    """
    url = f"{normalize_url(base_url)}/api/v3/{endpoint}"
    headers = {"X-Api-Key": api_key}

    try:
        response = http_session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making GET request to {endpoint}: {e}", exc_info=True)
        return None


def arr_api_post(base_url: str, api_key: str, endpoint: str, data: dict) -> dict | None:
    """
    Make a POST request to an *arr API v3 endpoint.

    Args:
        base_url: Base URL of the service
        api_key: API key for authentication
        endpoint: API endpoint
        data: JSON data to send

    Returns:
        JSON response data, or None on error
    """
    url = f"{normalize_url(base_url)}/api/v3/{endpoint}"
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    try:
        response = http_session.post(url, headers=headers, json=data, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making POST request to {endpoint}: {e}", exc_info=True)
        return None


def validate_api_key(base_url: str, api_key: str) -> bool:
    """
    Validate API URL and key by calling /api/v3/system/status.

    Args:
        base_url: Base URL of the service
        api_key: API key to validate

    Returns:
        True if valid, False otherwise
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
    Fetch quality profiles from *arr service.

    Args:
        base_url: Base URL of the service
        api_key: API key for authentication

    Returns:
        List of quality profile dicts with 'id' and 'name' keys, or empty list on error
    """
    profiles = arr_api_get(base_url, api_key, "qualityprofile")
    if profiles is None:
        return []
    return [{"id": p["id"], "name": p["name"]} for p in profiles]


def get_root_folders(base_url: str, api_key: str) -> list:
    """
    Fetch root folders from *arr service.

    Args:
        base_url: Base URL of the service
        api_key: API key for authentication

    Returns:
        List of root folder dicts with 'id' and 'path' keys, or empty list on error
    """
    folders = arr_api_get(base_url, api_key, "rootfolder")
    if folders is None:
        return []
    return [{"id": f["id"], "path": f["path"]} for f in folders]


def get_system_status(base_url: str, api_key: str) -> dict:
    """
    Fetch system status information from *arr service.

    Args:
        base_url: Base URL of the service
        api_key: API key for authentication

    Returns:
        System status dict with version info, or empty dict on error
    """
    status = arr_api_get(base_url, api_key, "system/status")
    if status is None:
        return {}
    return {
        "version": status.get("version"),
        "instance_name": status.get("instanceName"),
        "is_production": status.get("isProduction", False),
        "is_debug": status.get("isDebug", False),
    }


def get_tags(base_url: str, api_key: str) -> list:
    """
    Fetch tags from *arr service.

    Args:
        base_url: Base URL of the service
        api_key: API key for authentication

    Returns:
        List of tag dicts with 'id' and 'label' keys, or empty list on error
    """
    tags = arr_api_get(base_url, api_key, "tag")
    if tags is None:
        return []
    return [{"id": t["id"], "label": t["label"]} for t in tags]


def create_or_get_tag_id(base_url: str, api_key: str, tag_label: str) -> int | None:
    """
    Create a tag if it doesn't exist, or return existing tag ID.
    Normalizes tag label to lowercase with hyphens (*arr requirement).

    Args:
        base_url: Base URL of the service
        api_key: API key for authentication
        tag_label: Tag label to find or create

    Returns:
        Tag ID if found or created, None on error or if label is empty
    """
    normalized_label = tag_label.lower().replace(" ", "-")
    while "--" in normalized_label:
        normalized_label = normalized_label.replace("--", "-")
    normalized_label = normalized_label.strip("-")

    if not normalized_label:
        return None

    base = normalize_url(base_url)
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    try:
        get_url = f"{base}/api/v3/tag"
        response = http_session.get(get_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        tags = response.json()

        for tag in tags:
            if tag.get("label", "").lower() == normalized_label:
                return tag["id"]

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
