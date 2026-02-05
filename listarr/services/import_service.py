"""
Import Service
Orchestrates importing TMDB list items into Radarr/Sonarr.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from listarr.models.lists_model import List
from listarr.models.service_config_model import MediaImportSettings, ServiceConfig
from listarr.services import radarr_service, sonarr_service, tmdb_service
from listarr.services.crypto_utils import decrypt_data
from listarr.services.tmdb_cache import (
    discover_movies_cached,
    discover_tv_cached,
    get_popular_movies_cached,
    get_popular_tv_cached,
    get_top_rated_movies_cached,
    get_top_rated_tv_cached,
    get_trending_movies_cached,
    get_trending_tv_cached,
)

logger = logging.getLogger(__name__)

# Delay between API calls to be gentle on services
API_CALL_DELAY = 0.2  # 200ms


@dataclass
class ImportResult:
    """
    Structured result from an import operation.

    Categorizes items into:
    - added: Successfully imported to Radarr/Sonarr
    - skipped: Already existed in library (not an error)
    - failed: Error during import (API error, not found, etc.)
    """

    added: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total items processed."""
        return len(self.added) + len(self.skipped) + len(self.failed)

    @property
    def success_count(self) -> int:
        """Items that succeeded (added + skipped)."""
        return len(self.added) + len(self.skipped)

    @property
    def has_failures(self) -> bool:
        """Whether any items failed to import."""
        return len(self.failed) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "added": self.added,
            "skipped": self.skipped,
            "failed": self.failed,
            "summary": {
                "total": self.total,
                "added_count": len(self.added),
                "skipped_count": len(self.skipped),
                "failed_count": len(self.failed),
            },
        }


def resolve_import_settings(list_obj: List, import_settings: MediaImportSettings) -> dict:
    """
    Resolve import settings, preferring list overrides over service defaults.

    Tag Resolution Logic:
    - If list has override_tag_id: Use ONLY the override tag (replaces default)
    - Else if service has default_tag_id: Use the service default tag
    - Else: No tag applied (empty tags list)

    Args:
        list_obj: List model instance
        import_settings: MediaImportSettings model instance

    Returns:
        dict with keys: root_folder, quality_profile_id, monitored, search_on_add,
                        season_folder (Sonarr only), tags
    """
    # Resolve root folder
    if list_obj.override_root_folder:
        root_folder = list_obj.override_root_folder
    else:
        root_folder = import_settings.root_folder if import_settings else None

    # Resolve quality profile
    if list_obj.override_quality_profile is not None:
        quality_profile_id = list_obj.override_quality_profile
    else:
        quality_profile_id = import_settings.quality_profile_id if import_settings else None

    # Resolve monitored (stored as 0/1 in list, bool in import_settings)
    if list_obj.override_monitored is not None:
        monitored = bool(list_obj.override_monitored)
    else:
        monitored = import_settings.monitored if import_settings else True

    # Resolve search_on_add
    if list_obj.override_search_on_add is not None:
        search_on_add = bool(list_obj.override_search_on_add)
    else:
        search_on_add = import_settings.search_on_add if import_settings else True

    # Resolve season_folder (Sonarr only)
    if list_obj.override_season_folder is not None:
        season_folder = bool(list_obj.override_season_folder)
    else:
        season_folder = import_settings.season_folder if import_settings else True

    # Resolve tags - override REPLACES default (not merges)
    tags = []
    if list_obj.override_tag_id:
        # Use override tag only
        tags.append(list_obj.override_tag_id)
    elif import_settings and import_settings.default_tag_id:
        # Fall back to service default tag
        tags.append(import_settings.default_tag_id)
    # If neither: tags stays empty (no tag applied)

    return {
        "root_folder": root_folder,
        "quality_profile_id": quality_profile_id,
        "monitored": monitored,
        "search_on_add": search_on_add,
        "season_folder": season_folder,
        "tags": tags,
    }


def _fetch_tmdb_items(list_obj: List, tmdb_api_key: str) -> list:
    """
    Fetch TMDB items based on list type and filters.

    Fetches multiple pages from TMDB when limit > 20 (TMDB returns 20 items per page).

    Args:
        list_obj: List model instance
        tmdb_api_key: TMDB API key

    Returns:
        list: List of TMDB items
    """
    import math

    tmdb_list_type = list_obj.tmdb_list_type
    filters = list_obj.filters_json or {}
    limit = list_obj.limit or 20

    # Calculate pages needed (TMDB returns 20 items per page)
    pages_needed = math.ceil(limit / 20)
    all_items = []

    # Build discovery filters once (used for discovery list type)
    tmdb_filters = {}
    if tmdb_list_type == "discovery":
        if filters.get("genres_include"):
            tmdb_filters["with_genres"] = ",".join(map(str, filters["genres_include"]))
        if filters.get("genres_exclude"):
            tmdb_filters["without_genres"] = ",".join(map(str, filters["genres_exclude"]))
        if filters.get("language"):
            tmdb_filters["with_original_language"] = filters["language"]
        if filters.get("year_min"):
            if list_obj.target_service == "RADARR":
                tmdb_filters["primary_release_date.gte"] = f"{filters['year_min']}-01-01"
            else:
                tmdb_filters["first_air_date.gte"] = f"{filters['year_min']}-01-01"
        if filters.get("year_max"):
            if list_obj.target_service == "RADARR":
                tmdb_filters["primary_release_date.lte"] = f"{filters['year_max']}-12-31"
            else:
                tmdb_filters["first_air_date.lte"] = f"{filters['year_max']}-12-31"
        if filters.get("rating_min"):
            tmdb_filters["vote_average.gte"] = filters["rating_min"]

    # Fetch pages
    for page in range(1, pages_needed + 1):
        if tmdb_list_type == "trending_movies":
            items = get_trending_movies_cached(tmdb_api_key, page=page)
        elif tmdb_list_type == "trending_tv":
            items = get_trending_tv_cached(tmdb_api_key, page=page)
        elif tmdb_list_type == "popular_movies":
            items = get_popular_movies_cached(tmdb_api_key, page=page)
        elif tmdb_list_type == "popular_tv":
            items = get_popular_tv_cached(tmdb_api_key, page=page)
        elif tmdb_list_type == "top_rated_movies":
            items = get_top_rated_movies_cached(tmdb_api_key, page=page)
        elif tmdb_list_type == "top_rated_tv":
            items = get_top_rated_tv_cached(tmdb_api_key, page=page)
        elif tmdb_list_type == "discovery":
            if list_obj.target_service == "RADARR":
                items = discover_movies_cached(tmdb_api_key, tmdb_filters, page=page)
            else:
                items = discover_tv_cached(tmdb_api_key, tmdb_filters, page=page)
        else:
            logger.warning(f"Unknown list type: {tmdb_list_type}")
            return []

        # Extract results from AsObj if needed
        if hasattr(items, "results") and items.results:
            page_items = list(items.results)
        elif isinstance(items, list):
            page_items = items
        else:
            page_items = []

        all_items.extend(page_items)

        # Stop if we got fewer items than expected (no more pages available)
        if len(page_items) < 20:
            break

        # Stop if we already have enough items
        if len(all_items) >= limit:
            break

    # Apply limit
    return all_items[:limit]


def _import_movies(tmdb_items: list, base_url: str, api_key: str, settings: dict, tmdb_api_key: str) -> ImportResult:
    """
    Import movies to Radarr.

    Args:
        tmdb_items: List of TMDB movie items
        base_url: Radarr base URL
        api_key: Radarr API key
        settings: Resolved import settings dict
        tmdb_api_key: TMDB API key (unused for movies, kept for consistency)

    Returns:
        ImportResult with added/skipped/failed items
    """
    result = ImportResult()

    # Pre-flight: get existing movies
    existing_ids = radarr_service.get_existing_movie_tmdb_ids(base_url, api_key)
    logger.info(f"Found {len(existing_ids)} existing movies in Radarr")

    for item in tmdb_items:
        # Extract TMDB ID
        try:
            tmdb_id = item["id"] if isinstance(item, dict) else getattr(item, "id", None)
            title = item.get("title", "Unknown") if isinstance(item, dict) else getattr(item, "title", "Unknown")
        except (TypeError, KeyError, AttributeError):
            tmdb_id = None
            title = "Unknown"

        if not tmdb_id:
            result.failed.append({"tmdb_id": None, "title": title, "reason": "no_tmdb_id"})
            continue

        # Check if already exists
        if tmdb_id in existing_ids:
            result.skipped.append({"tmdb_id": tmdb_id, "title": title, "reason": "already_exists"})
            continue

        try:
            # Lookup movie in Radarr
            movie_data = radarr_service.lookup_movie(base_url, api_key, tmdb_id)
            if not movie_data:
                result.failed.append(
                    {
                        "tmdb_id": tmdb_id,
                        "title": title,
                        "reason": "not_found_in_radarr",
                    }
                )
                time.sleep(API_CALL_DELAY)
                continue

            # Add movie to Radarr
            radarr_service.add_movie(
                base_url=base_url,
                api_key=api_key,
                movie_data=movie_data,
                root_folder=settings["root_folder"],
                quality_profile_id=settings["quality_profile_id"],
                monitored=settings["monitored"],
                search_on_add=settings["search_on_add"],
                tags=settings["tags"],
            )

            result.added.append({"tmdb_id": tmdb_id, "title": title})

        except Exception as e:
            logger.error(f"Error adding movie {title} (TMDB: {tmdb_id}): {e}", exc_info=True)
            result.failed.append({"tmdb_id": tmdb_id, "title": title, "reason": str(e)})

        time.sleep(API_CALL_DELAY)

    logger.info(
        f"Import complete: {len(result.added)} added, {len(result.skipped)} skipped, {len(result.failed)} failed"
    )
    return result


def _import_series(tmdb_items: list, base_url: str, api_key: str, settings: dict, tmdb_api_key: str) -> ImportResult:
    """
    Import TV shows to Sonarr.

    Args:
        tmdb_items: List of TMDB TV show items
        base_url: Sonarr base URL
        api_key: Sonarr API key
        settings: Resolved import settings dict
        tmdb_api_key: TMDB API key for TVDB translation

    Returns:
        ImportResult with added/skipped/failed items
    """
    result = ImportResult()

    # Pre-flight: get existing series
    existing_ids = sonarr_service.get_existing_series_tvdb_ids(base_url, api_key)
    logger.info(f"Found {len(existing_ids)} existing series in Sonarr")

    for item in tmdb_items:
        # Extract TMDB ID and title
        try:
            tmdb_id = item["id"] if isinstance(item, dict) else getattr(item, "id", None)
            title = item.get("name", "Unknown") if isinstance(item, dict) else getattr(item, "name", "Unknown")
        except (TypeError, KeyError, AttributeError):
            tmdb_id = None
            title = "Unknown"

        if not tmdb_id:
            result.failed.append({"tmdb_id": None, "title": title, "reason": "no_tmdb_id"})
            continue

        # Translate TMDB ID to TVDB ID
        tvdb_id = tmdb_service.get_tvdb_id_from_tmdb(tmdb_id, tmdb_api_key)
        if not tvdb_id:
            result.failed.append({"tmdb_id": tmdb_id, "title": title, "reason": "no_tvdb_id"})
            time.sleep(API_CALL_DELAY)
            continue

        # Check if already exists
        if tvdb_id in existing_ids:
            result.skipped.append(
                {
                    "tmdb_id": tmdb_id,
                    "tvdb_id": tvdb_id,
                    "title": title,
                    "reason": "already_exists",
                }
            )
            continue

        try:
            # Lookup series in Sonarr
            series_data = sonarr_service.lookup_series(base_url, api_key, tvdb_id)
            if not series_data:
                result.failed.append(
                    {
                        "tmdb_id": tmdb_id,
                        "tvdb_id": tvdb_id,
                        "title": title,
                        "reason": "not_found_in_sonarr",
                    }
                )
                time.sleep(API_CALL_DELAY)
                continue

            # Add series to Sonarr
            sonarr_service.add_series(
                base_url=base_url,
                api_key=api_key,
                series_data=series_data,
                root_folder=settings["root_folder"],
                quality_profile_id=settings["quality_profile_id"],
                monitored=settings["monitored"],
                season_folder=settings["season_folder"],
                search_on_add=settings["search_on_add"],
                tags=settings["tags"],
            )

            result.added.append({"tmdb_id": tmdb_id, "tvdb_id": tvdb_id, "title": title})

        except Exception as e:
            logger.error(
                f"Error adding series {title} (TMDB: {tmdb_id}, TVDB: {tvdb_id}): {e}",
                exc_info=True,
            )
            result.failed.append(
                {
                    "tmdb_id": tmdb_id,
                    "tvdb_id": tvdb_id,
                    "title": title,
                    "reason": str(e),
                }
            )

        time.sleep(API_CALL_DELAY)

    logger.info(
        f"Import complete: {len(result.added)} added, {len(result.skipped)} skipped, {len(result.failed)} failed"
    )
    return result


def import_list(list_id: int) -> ImportResult:
    """
    Import all items from a TMDB list into Radarr or Sonarr.

    Args:
        list_id: Database ID of the List to import

    Returns:
        ImportResult with added/skipped/failed items
    """
    # Fetch list from database
    list_obj = List.query.get(list_id)
    if not list_obj:
        logger.error(f"List {list_id} not found")
        result = ImportResult()
        result.failed.append({"reason": "list_not_found", "list_id": list_id})
        return result

    target_service = list_obj.target_service  # 'RADARR' or 'SONARR'
    logger.info(f"Starting import for list '{list_obj.name}' (ID: {list_id}) to {target_service}")

    # Fetch service config
    service_config = ServiceConfig.query.filter_by(service=target_service).first()
    if not service_config or not service_config.api_key_encrypted:
        logger.error(f"{target_service} not configured")
        result = ImportResult()
        result.failed.append({"reason": "service_not_configured", "service": target_service})
        return result

    # Fetch TMDB config
    tmdb_config = ServiceConfig.query.filter_by(service="TMDB").first()
    if not tmdb_config or not tmdb_config.api_key_encrypted:
        logger.error("TMDB not configured")
        result = ImportResult()
        result.failed.append({"reason": "tmdb_not_configured"})
        return result

    # Fetch import settings
    import_settings = MediaImportSettings.query.filter_by(service=target_service).first()

    # Decrypt API keys
    try:
        service_api_key = decrypt_data(service_config.api_key_encrypted)
        tmdb_api_key = decrypt_data(tmdb_config.api_key_encrypted)
    except Exception as e:
        logger.error(f"Error decrypting API keys: {e}", exc_info=True)
        result = ImportResult()
        result.failed.append({"reason": "decryption_error", "error": str(e)})
        return result

    base_url = service_config.base_url

    # Resolve import settings
    settings = resolve_import_settings(list_obj, import_settings)
    logger.debug(f"Resolved settings: {settings}")

    # Validate required settings
    if not settings["root_folder"]:
        logger.error("No root folder configured")
        result = ImportResult()
        result.failed.append({"reason": "no_root_folder"})
        return result

    if not settings["quality_profile_id"]:
        logger.error("No quality profile configured")
        result = ImportResult()
        result.failed.append({"reason": "no_quality_profile"})
        return result

    # Fetch TMDB items
    tmdb_items = _fetch_tmdb_items(list_obj, tmdb_api_key)
    logger.info(f"Fetched {len(tmdb_items)} items from TMDB")

    if not tmdb_items:
        logger.warning("No items fetched from TMDB")
        return ImportResult()

    # Route to appropriate import function
    if target_service == "RADARR":
        return _import_movies(tmdb_items, base_url, service_api_key, settings, tmdb_api_key)
    else:
        return _import_series(tmdb_items, base_url, service_api_key, settings, tmdb_api_key)
