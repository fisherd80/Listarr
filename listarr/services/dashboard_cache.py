"""
Dashboard statistics cache service.

This module provides caching for dashboard statistics to improve page load performance.
Stats are calculated at application startup and can be refreshed on-demand.
"""
import logging
import threading
from typing import Dict, Optional
from flask import current_app
from listarr import db
from listarr.models.service_config_model import ServiceConfig
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.services.radarr_service import (
    get_system_status as get_radarr_system_status,
    get_movie_count,
    get_missing_movies_count
)
from listarr.services.sonarr_service import (
    get_system_status as get_sonarr_system_status,
    get_series_count,
    get_missing_episodes_count
)
from listarr.services.crypto_utils import decrypt_data

logger = logging.getLogger(__name__)

# In-memory cache for dashboard statistics
_dashboard_cache: Dict = {
    "radarr": {
        "configured": False,
        "status": "not_configured",
        "version": None,
        "total_movies": 0,
        "missing_movies": 0,
        "added_by_listarr": 0
    },
    "sonarr": {
        "configured": False,
        "status": "not_configured",
        "version": None,
        "total_series": 0,
        "missing_episodes": 0,
        "added_by_listarr": 0
    }
}

# Lock for thread-safe cache updates
_cache_lock = threading.Lock()


def _calculate_radarr_stats() -> Dict:
    """
    Calculates Radarr statistics.
    
    Returns:
        dict: Radarr statistics dictionary
    """
    result = {
        "configured": False,
        "status": "not_configured",
        "version": None,
        "total_movies": 0,
        "missing_movies": 0,
        "added_by_listarr": 0
    }
    
    try:
        # Check if Radarr is configured
        # Handle case where database tables don't exist yet (e.g., during test setup)
        try:
            radarr_service = ServiceConfig.query.filter_by(service="RADARR").first()
        except Exception as db_error:
            # If tables don't exist, return not_configured status
            if "no such table" in str(db_error).lower() or "operationalerror" in str(type(db_error).__name__).lower():
                logger.debug("Database tables not yet initialized, returning not_configured status")
                return result
            raise
        
        if not radarr_service or not radarr_service.api_key_encrypted or not radarr_service.base_url:
            return result
        
        result["configured"] = True
        
        try:
            # Decrypt API key
            api_key = decrypt_data(
                radarr_service.api_key_encrypted,
                instance_path=current_app.instance_path
            )
            base_url = radarr_service.base_url
            
            # Fetch Radarr System Status
            try:
                system_status = get_radarr_system_status(base_url, api_key)
                if system_status:
                    result["status"] = "online"
                    result["version"] = system_status.get("version")
                else:
                    result["status"] = "offline"
            except Exception as e:
                logger.error(f"Error fetching Radarr system status: {e}", exc_info=True)
                result["status"] = "offline"
            
            # Fetch Movie Count (only if online)
            if result["status"] == "online":
                try:
                    movie_count = get_movie_count(base_url, api_key)
                    result["total_movies"] = movie_count
                except Exception as e:
                    logger.error(f"Error fetching Radarr movie count: {e}", exc_info=True)
                    result["total_movies"] = 0
                
                # Fetch Missing Movies Count (only if online)
                try:
                    missing_count = get_missing_movies_count(base_url, api_key)
                    result["missing_movies"] = missing_count
                except Exception as e:
                    logger.error(f"Error fetching Radarr missing movies count: {e}", exc_info=True)
                    result["missing_movies"] = 0
            
        except Exception as e:
            # Handle decryption errors or other setup errors
            logger.error(f"Error setting up Radarr dashboard stats: {e}", exc_info=True)
            result["status"] = "offline"
    
    except Exception as e:
        # If it's a database table error, keep status as not_configured
        if "no such table" in str(e).lower() or "operationalerror" in str(type(e).__name__).lower():
            logger.debug("Database tables not yet initialized during Radarr stats calculation")
            return result
        logger.error(f"Unexpected error calculating Radarr stats: {e}", exc_info=True)
        result["status"] = "offline"
    
    # Calculate total items added by Listarr for Radarr
    try:
        # Sum items_added from all completed jobs for Radarr lists
        # Handle case where tables don't exist
        try:
            radarr_lists = List.query.filter_by(target_service="RADARR").all()
        except Exception as db_error:
            if "no such table" in str(db_error).lower() or "operationalerror" in str(type(db_error).__name__).lower():
                logger.debug("Database tables not yet initialized for lists query")
                return result
            raise
        if radarr_lists:
            list_ids = [lst.id for lst in radarr_lists]
            total_added = db.session.query(
                db.func.sum(Job.items_added)
            ).filter(
                Job.list_id.in_(list_ids),
                Job.status == "completed"
            ).scalar() or 0
            result["added_by_listarr"] = int(total_added)
    except Exception as e:
        logger.error(f"Error calculating Radarr items added by Listarr: {e}", exc_info=True)
        result["added_by_listarr"] = 0
    
    return result


def _calculate_sonarr_stats() -> Dict:
    """
    Calculates Sonarr statistics.
    
    Returns:
        dict: Sonarr statistics dictionary
    """
    result = {
        "configured": False,
        "status": "not_configured",
        "version": None,
        "total_series": 0,
        "missing_episodes": 0,
        "added_by_listarr": 0
    }
    
    try:
        # Check if Sonarr is configured
        # Handle case where database tables don't exist yet (e.g., during test setup)
        try:
            sonarr_service = ServiceConfig.query.filter_by(service="SONARR").first()
        except Exception as db_error:
            # If tables don't exist, return not_configured status
            if "no such table" in str(db_error).lower() or "operationalerror" in str(type(db_error).__name__).lower():
                logger.debug("Database tables not yet initialized, returning not_configured status")
                return result
            raise
        
        if not sonarr_service or not sonarr_service.api_key_encrypted or not sonarr_service.base_url:
            return result
        
        result["configured"] = True
        
        try:
            # Decrypt API key
            api_key = decrypt_data(
                sonarr_service.api_key_encrypted,
                instance_path=current_app.instance_path
            )
            base_url = sonarr_service.base_url
            
            # Fetch Sonarr System Status
            try:
                system_status = get_sonarr_system_status(base_url, api_key)
                if system_status:
                    result["status"] = "online"
                    result["version"] = system_status.get("version")
                else:
                    result["status"] = "offline"
            except Exception as e:
                logger.error(f"Error fetching Sonarr system status: {e}", exc_info=True)
                result["status"] = "offline"
            
            # Fetch Series Count (only if online)
            if result["status"] == "online":
                try:
                    series_count = get_series_count(base_url, api_key)
                    result["total_series"] = series_count
                except Exception as e:
                    logger.error(f"Error fetching Sonarr series count: {e}", exc_info=True)
                    result["total_series"] = 0
                
                # Fetch Missing Episodes Count (only if online)
                # Uses get_wanted() function with totalRecords
                try:
                    missing_count = get_missing_episodes_count(base_url, api_key)
                    result["missing_episodes"] = missing_count
                except Exception as e:
                    logger.error(f"Error fetching Sonarr missing episodes count: {e}", exc_info=True)
                    result["missing_episodes"] = 0
            
        except Exception as e:
            # Handle decryption errors or other setup errors
            logger.error(f"Error setting up Sonarr dashboard stats: {e}", exc_info=True)
            result["status"] = "offline"
    
    except Exception as e:
        # If it's a database table error, keep status as not_configured
        if "no such table" in str(e).lower() or "operationalerror" in str(type(e).__name__).lower():
            logger.debug("Database tables not yet initialized during Sonarr stats calculation")
            return result
        logger.error(f"Unexpected error calculating Sonarr stats: {e}", exc_info=True)
        result["status"] = "offline"
    
    # Calculate total items added by Listarr for Sonarr
    try:
        # Sum items_added from all completed jobs for Sonarr lists
        # Handle case where tables don't exist
        try:
            sonarr_lists = List.query.filter_by(target_service="SONARR").all()
        except Exception as db_error:
            if "no such table" in str(db_error).lower() or "operationalerror" in str(type(db_error).__name__).lower():
                logger.debug("Database tables not yet initialized for lists query")
                return result
            raise
        if sonarr_lists:
            list_ids = [lst.id for lst in sonarr_lists]
            total_added = db.session.query(
                db.func.sum(Job.items_added)
            ).filter(
                Job.list_id.in_(list_ids),
                Job.status == "completed"
            ).scalar() or 0
            result["added_by_listarr"] = int(total_added)
    except Exception as e:
        logger.error(f"Error calculating Sonarr items added by Listarr: {e}", exc_info=True)
        result["added_by_listarr"] = 0
    
    return result


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
        
        except Exception as e:
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
        except Exception as e:
            logger.error(f"Error initializing dashboard cache: {e}", exc_info=True)
            # Continue with default cache values on error
