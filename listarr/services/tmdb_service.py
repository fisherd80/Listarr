"""
TMDB API Service
Handles all interactions with The Movie Database (TMDB) API using direct HTTP calls.
"""

import logging

import requests

from listarr.services.http_client import API_BASE_TMDB, DEFAULT_TIMEOUT, http_session

logger = logging.getLogger(__name__)


def validate_tmdb_api_key(api_key: str) -> bool:
    """
    Test the TMDB API key by fetching popular movies.

    Args:
        api_key (str): TMDB API key to test

    Returns:
        bool: True if valid, False otherwise
    """
    if not api_key:
        return False

    try:
        url = f"{API_BASE_TMDB}/movie/popular"
        params = {"api_key": api_key, "page": 1, "language": "en"}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def get_tvdb_id_from_tmdb(tmdb_id: int, api_key: str) -> int | None:
    """
    Get TVDB ID for a TMDB TV show.

    Args:
        tmdb_id (int): TMDB TV show ID
        api_key (str): TMDB API key

    Returns:
        int: TVDB ID or None if not found/not available
    """
    if not api_key or not tmdb_id:
        return None

    try:
        url = f"{API_BASE_TMDB}/tv/{tmdb_id}/external_ids"
        params = {"api_key": api_key}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("tvdb_id")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching TVDB ID for TMDB TV show {tmdb_id}: {e}", exc_info=True)
        return None


def get_imdb_id_from_tmdb(tmdb_id: int, api_key: str, media_type: str = "movie") -> str:
    """
    Get IMDB ID for a TMDB movie or TV show.

    Args:
        tmdb_id (int): TMDB ID
        api_key (str): TMDB API key
        media_type (str): 'movie' or 'tv'

    Returns:
        str: IMDB ID (e.g., 'tt1234567') or None if not found
    """
    if not api_key or not tmdb_id:
        return None

    if media_type not in ("movie", "tv"):
        return None

    try:
        url = f"{API_BASE_TMDB}/{media_type}/{tmdb_id}/external_ids"
        params = {"api_key": api_key}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("imdb_id")
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Error fetching IMDB ID for TMDB {media_type} {tmdb_id}: {e}",
            exc_info=True,
        )
        return None


def get_trending_movies(api_key: str, time_window: str = "week", page: int = 1) -> list:
    """
    Fetch trending movies from TMDB.

    Args:
        api_key (str): TMDB API key
        time_window (str): 'day' or 'week'
        page (int): Page number (default: 1)

    Returns:
        list: List of movie dicts with id, title, release_date, overview, etc.
    """
    if not api_key:
        return []

    try:
        url = f"{API_BASE_TMDB}/trending/movie/{time_window}"
        params = {"api_key": api_key, "page": page, "language": "en"}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching trending movies: {e}", exc_info=True)
        return []


def get_trending_tv(api_key: str, time_window: str = "week", page: int = 1) -> list:
    """
    Fetch trending TV shows from TMDB.

    Args:
        api_key (str): TMDB API key
        time_window (str): 'day' or 'week'
        page (int): Page number (default: 1)

    Returns:
        list: List of TV show dicts with id, name, first_air_date, overview, etc.
    """
    if not api_key:
        return []

    try:
        url = f"{API_BASE_TMDB}/trending/tv/{time_window}"
        params = {"api_key": api_key, "page": page, "language": "en"}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching trending TV shows: {e}", exc_info=True)
        return []


def get_popular_movies(api_key: str, page: int = 1, region: str = None) -> list:
    """
    Fetch popular movies from TMDB.

    Args:
        api_key (str): TMDB API key
        page (int): Page number (default: 1)
        region (str): ISO 3166-1 Alpha-2 region code (optional)

    Returns:
        list: List of movie dicts
    """
    if not api_key:
        return []

    try:
        url = f"{API_BASE_TMDB}/movie/popular"
        params = {"api_key": api_key, "page": page, "language": "en"}
        if region:
            params["region"] = region
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching popular movies: {e}", exc_info=True)
        return []


def get_popular_tv(api_key: str, page: int = 1) -> list:
    """
    Fetch popular TV shows from TMDB.

    Args:
        api_key (str): TMDB API key
        page (int): Page number (default: 1)

    Returns:
        list: List of TV show dicts
    """
    if not api_key:
        return []

    try:
        url = f"{API_BASE_TMDB}/tv/popular"
        params = {"api_key": api_key, "page": page, "language": "en"}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching popular TV shows: {e}", exc_info=True)
        return []


def get_top_rated_movies(api_key: str, page: int = 1, region: str = None) -> list:
    """
    Fetch top rated movies from TMDB.

    Args:
        api_key (str): TMDB API key
        page (int): Page number (default: 1)
        region (str): ISO 3166-1 Alpha-2 region code (optional)

    Returns:
        list: List of movie dicts
    """
    if not api_key:
        return []

    try:
        url = f"{API_BASE_TMDB}/movie/top_rated"
        params = {"api_key": api_key, "page": page, "language": "en"}
        if region:
            params["region"] = region
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching top rated movies: {e}", exc_info=True)
        return []


def get_top_rated_tv(api_key: str, page: int = 1) -> list:
    """
    Fetch top rated TV shows from TMDB.

    Args:
        api_key (str): TMDB API key
        page (int): Page number (default: 1)

    Returns:
        list: List of TV show dicts
    """
    if not api_key:
        return []

    try:
        url = f"{API_BASE_TMDB}/tv/top_rated"
        params = {"api_key": api_key, "page": page, "language": "en"}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching top rated TV shows: {e}", exc_info=True)
        return []


def discover_movies(api_key: str, filters: dict = None, page: int = 1, region: str = None) -> list:
    """
    Discover movies with optional filters.

    Args:
        api_key (str): TMDB API key
        filters (dict): Optional filters (genre, year, language, rating, etc.)
            Example: {
                'with_genres': '28,12',  # Action, Adventure
                'primary_release_year': 2023,
                'vote_average.gte': 7.0,
                'with_original_language': 'en'
            }
        page (int): Page number (default: 1)
        region (str): ISO 3166-1 Alpha-2 region code (optional)

    Returns:
        list: List of movie dicts matching filters
    """
    if not api_key:
        return []

    try:
        url = f"{API_BASE_TMDB}/discover/movie"
        params = {"api_key": api_key, "page": page, "language": "en"}
        if region:
            params["region"] = region
        if filters:
            params.update(filters)
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error discovering movies: {e}", exc_info=True)
        return []


def discover_tv(api_key: str, filters: dict = None, page: int = 1, region: str = None) -> list:
    """
    Discover TV shows with optional filters.

    Args:
        api_key (str): TMDB API key
        filters (dict): Optional filters (genre, year, language, rating, etc.)
            Example: {
                'with_genres': '18,80',  # Drama, Crime
                'first_air_date_year': 2023,
                'vote_average.gte': 7.5
            }
        page (int): Page number (default: 1)
        region (str): ISO 3166-1 Alpha-2 region code (optional)

    Returns:
        list: List of TV show dicts matching filters
    """
    if not api_key:
        return []

    try:
        url = f"{API_BASE_TMDB}/discover/tv"
        params = {"api_key": api_key, "page": page, "language": "en"}
        if region:
            params["region"] = region
        if filters:
            params.update(filters)
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error discovering TV shows: {e}", exc_info=True)
        return []


def get_movie_details(tmdb_id: int, api_key: str) -> dict:
    """
    Get detailed information for a specific movie.

    Args:
        tmdb_id (int): TMDB movie ID
        api_key (str): TMDB API key

    Returns:
        dict: Movie details including genres, runtime, cast, etc.
    """
    if not api_key or not tmdb_id:
        return {}

    try:
        url = f"{API_BASE_TMDB}/movie/{tmdb_id}"
        params = {"api_key": api_key, "language": "en"}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching movie details for ID {tmdb_id}: {e}", exc_info=True)
        return {}


def get_tv_details(tmdb_id: int, api_key: str) -> dict:
    """
    Get detailed information for a specific TV show.

    Args:
        tmdb_id (int): TMDB TV show ID
        api_key (str): TMDB API key

    Returns:
        dict: TV show details including genres, seasons, cast, etc.
    """
    if not api_key or not tmdb_id:
        return {}

    try:
        url = f"{API_BASE_TMDB}/tv/{tmdb_id}"
        params = {"api_key": api_key, "language": "en"}
        response = http_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching TV show details for ID {tmdb_id}: {e}", exc_info=True)
        return {}
