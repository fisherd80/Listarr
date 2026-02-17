"""
Dashboard statistics cache service.

This module provides caching for dashboard statistics to improve page load performance.
Stats are calculated at application startup and can be refreshed on-demand.
"""

import logging
import threading
from typing import Dict

from cryptography.fernet import InvalidToken
from flask import current_app
from requests.exceptions import RequestException
from sqlalchemy.exc import OperationalError

from listarr import db
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.services.crypto_utils import decrypt_data
from listarr.services.radarr_service import get_missing_movies_count, get_movie_count
from listarr.services.radarr_service import (
    get_system_status as get_radarr_system_status,
)
from listarr.services.sonarr_service import get_missing_episodes_count, get_series_count
from listarr.services.sonarr_service import (
    get_system_status as get_sonarr_system_status,
)

logger = logging.getLogger(__name__)

# In-memory cache for dashboard statistics
_dashboard_cache: Dict = {
    "radarr": {
        "configured": False,
        "status": "not_configured",
        "version": None,
        "total_movies": 0,
        "missing_movies": 0,
        "added_by_listarr": 0,
    },
    "sonarr": {
        "configured": False,
        "status": "not_configured",
        "version": None,
        "total_series": 0,
        "missing_episodes": 0,
        "added_by_listarr": 0,
    },
}

# Lock for thread-safe cache updates
_cache_lock = threading.Lock()


def _calculate_service_stats(service: str) -> Dict:
    """
    Calculate statistics for a service (Radarr or Sonarr).

    Args:
        service: Service identifier ("RADARR" or "SONARR")

    Returns:
        dict: Service statistics dictionary
    """
    is_radarr = service == "RADARR"

    # Service-specific configuration
    if is_radarr:
        result_keys = {
            "total_key": "total_movies",
            "missing_key": "missing_movies",
        }
        get_status = get_radarr_system_status
        get_count = get_movie_count
        get_missing = get_missing_movies_count
    else:
        result_keys = {
            "total_key": "total_series",
            "missing_key": "missing_episodes",
        }
        get_status = get_sonarr_system_status
        get_count = get_series_count
        get_missing = get_missing_episodes_count

    # Initialize result with service-appropriate keys
    result = {
        "configured": False,
        "status": "not_configured",
        "version": None,
        result_keys["total_key"]: 0,
        result_keys["missing_key"]: 0,
        "added_by_listarr": 0,
    }

    # Calculate total items added by Listarr FIRST
    # This is database-only and should work regardless of service configuration
    try:
        try:
            # Use case-insensitive query to handle any case variations in stored data
            service_lists = List.query.filter(db.func.upper(List.target_service) == service).all()
        except OperationalError as db_error:
            if "no such table" in str(db_error).lower() or "operationalerror" in str(type(db_error).__name__).lower():
                logger.debug("Database tables not yet initialized for lists query")
                service_lists = []
            else:
                raise
        if service_lists:
            list_ids = [lst.id for lst in service_lists]
            # Count all jobs with items_added > 0, regardless of status
            total_added = (
                db.session.query(db.func.sum(Job.items_added))
                .filter(Job.list_id.in_(list_ids), Job.items_added > 0)
                .scalar()
                or 0
            )
            result["added_by_listarr"] = int(total_added)
            logger.debug(f"{service} added_by_listarr: {total_added} from {len(service_lists)} lists")
    except OperationalError as e:
        logger.error(f"Error calculating {service} items added by Listarr: {e}", exc_info=True)
        result["added_by_listarr"] = 0

    try:
        # Check if service is configured
        try:
            service_config = ServiceConfig.query.filter_by(service=service).first()
        except OperationalError as db_error:
            if "no such table" in str(db_error).lower() or "operationalerror" in str(type(db_error).__name__).lower():
                logger.debug("Database tables not yet initialized, returning not_configured status")
                return result
            raise

        if not service_config or not service_config.api_key_encrypted or not service_config.base_url:
            return result

        result["configured"] = True

        try:
            # Decrypt API key
            api_key = decrypt_data(
                service_config.api_key_encrypted,
                instance_path=current_app.instance_path,
            )
            base_url = service_config.base_url

            # Fetch System Status
            try:
                system_status = get_status(base_url, api_key)
                if system_status:
                    result["status"] = "online"
                    result["version"] = system_status.get("version")
                else:
                    result["status"] = "offline"
            except (RequestException, ValueError, InvalidToken, TimeoutError) as e:
                logger.error(f"Error fetching {service} system status: {e}", exc_info=True)
                result["status"] = "offline"

            # Fetch counts (only if online)
            if result["status"] == "online":
                try:
                    count = get_count(base_url, api_key)
                    result[result_keys["total_key"]] = count
                except (RequestException, TimeoutError) as e:
                    logger.error(f"Error fetching {service} count: {e}", exc_info=True)
                    result[result_keys["total_key"]] = 0

                try:
                    missing = get_missing(base_url, api_key)
                    result[result_keys["missing_key"]] = missing
                except (RequestException, TimeoutError) as e:
                    logger.error(f"Error fetching {service} missing count: {e}", exc_info=True)
                    result[result_keys["missing_key"]] = 0

        except (ValueError, InvalidToken) as e:
            logger.error(f"Error setting up {service} dashboard stats: {e}", exc_info=True)
            result["status"] = "offline"

    except OperationalError as e:
        if "no such table" in str(e).lower() or "operationalerror" in str(type(e).__name__).lower():
            logger.debug(f"Database tables not yet initialized during {service} stats calculation")
            return result
        logger.error(f"Unexpected error calculating {service} stats: {e}", exc_info=True)
        result["status"] = "offline"

    return result


def _calculate_radarr_stats() -> Dict:
    """Calculate Radarr statistics. Delegates to unified function."""
    return _calculate_service_stats("RADARR")


def _calculate_sonarr_stats() -> Dict:
    """Calculate Sonarr statistics. Delegates to unified function."""
    return _calculate_service_stats("SONARR")


def refresh_dashboard_cache() -> Dict:
    """
    Refreshes the dashboard cache by recalculating all statistics.

    This function should be called within a Flask application context.

    Returns:
        dict: Updated dashboard statistics
    """
    with _cache_lock:
        try:
            logger.info("Refreshing dashboard cache...")

            # Calculate Radarr stats
            _dashboard_cache["radarr"] = _calculate_radarr_stats()

            # Calculate Sonarr stats
            _dashboard_cache["sonarr"] = _calculate_sonarr_stats()

            logger.info("Dashboard cache refreshed successfully")
            return _dashboard_cache.copy()

        except (OperationalError, RequestException) as e:
            logger.error(f"Error refreshing dashboard cache: {e}", exc_info=True)
            return _dashboard_cache.copy()


def get_dashboard_cache() -> Dict:
    """
    Gets the current dashboard cache.

    Returns:
        dict: Copy of the current dashboard statistics
    """
    with _cache_lock:
        return _dashboard_cache.copy()


def initialize_dashboard_cache(app):
    """
    Initializes the dashboard cache at application startup.

    This function should be called after the Flask app is created and
    the database is initialized.

    Args:
        app: Flask application instance
    """
    with app.app_context():
        try:
            logger.info("Initializing dashboard cache at startup...")
            refresh_dashboard_cache()
            logger.info("Dashboard cache initialized successfully")
        except (OperationalError, RequestException) as e:
            logger.error(f"Error initializing dashboard cache: {e}", exc_info=True)
            # Continue with default cache values on error
