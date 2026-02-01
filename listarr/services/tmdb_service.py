"""
TMDB API Service
Handles all interactions with The Movie Database (TMDB) API using tmdbv3api library.
"""

import logging

from tmdbv3api import TV, Discover, Movie, TMDb, Trending

logger = logging.getLogger(__name__)


def _init_tmdb(api_key: str) -> TMDb:
    """
    Initialize TMDB API client with the provided API key.

    Args:
        api_key (str): TMDB API key

    Returns:
        TMDb: Initialized TMDB client instance
    """
    tmdb = TMDb()
    tmdb.api_key = api_key
    tmdb.language = "en"  # Default language
    return tmdb


def validate_tmdb_api_key(api_key: str) -> bool:
    """
    Test the TMDB API key by fetching TMDB configuration.

    Args:
        api_key (str): TMDB API key to test

    Returns:
        bool: True if valid, False otherwise
    """
    if not api_key:
        return False

    try:
        _init_tmdb(api_key)
        # Test by fetching configuration
        # tmdbv3api will raise exception if API key is invalid
        movie = Movie()
        _ = movie.popular(page=1)  # Simple test call
        return True
    except Exception:
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
        _init_tmdb(api_key)
        tv = TV()
        external_ids = tv.external_ids(tmdb_id)
        return external_ids.get("tvdb_id")
    except Exception as e:
        logger.error(
            f"Error fetching TVDB ID for TMDB TV show {tmdb_id}: {e}", exc_info=True
        )
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

    try:
        _init_tmdb(api_key)

        if media_type == "movie":
            movie = Movie()
            external_ids = movie.external_ids(tmdb_id)
        elif media_type == "tv":
            tv = TV()
            external_ids = tv.external_ids(tmdb_id)
        else:
            return None

        return external_ids.get("imdb_id")
    except Exception as e:
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
        _init_tmdb(api_key)
        trending = Trending()
        results = trending.movie_week(page=page) if time_window == "week" else trending.movie_day(page=page)
        return results
    except Exception as e:
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
        _init_tmdb(api_key)
        trending = Trending()
        results = trending.tv_week(page=page) if time_window == "week" else trending.tv_day(page=page)
        return results
    except Exception as e:
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
        _init_tmdb(api_key)
        movie = Movie()
        # tmdbv3api popular() accepts region parameter
        results = (
            movie.popular(page=page, region=region)
            if region
            else movie.popular(page=page)
        )
        return results
    except Exception as e:
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
        _init_tmdb(api_key)
        tv = TV()
        results = tv.popular(page=page)
        return results
    except Exception as e:
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
        _init_tmdb(api_key)
        movie = Movie()
        # tmdbv3api top_rated() accepts region parameter
        results = (
            movie.top_rated(page=page, region=region)
            if region
            else movie.top_rated(page=page)
        )
        return results
    except Exception as e:
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
        _init_tmdb(api_key)
        tv = TV()
        results = tv.top_rated(page=page)
        return results
    except Exception as e:
        logger.error(f"Error fetching top rated TV shows: {e}", exc_info=True)
        return []


def discover_movies(
    api_key: str, filters: dict = None, page: int = 1, region: str = None
) -> list:
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
        _init_tmdb(api_key)
        discover = Discover()

        # Build discover parameters
        params = {"page": page}
        if region:
            params["region"] = region
        if filters:
            params.update(filters)

        results = discover.discover_movies(params)
        return results
    except Exception as e:
        logger.error(f"Error discovering movies: {e}", exc_info=True)
        return []


def discover_tv(
    api_key: str, filters: dict = None, page: int = 1, region: str = None
) -> list:
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
        _init_tmdb(api_key)
        discover = Discover()

        # Build discover parameters
        params = {"page": page}
        if region:
            params["region"] = region
        if filters:
            params.update(filters)

        results = discover.discover_tv_shows(params)
        return results
    except Exception as e:
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
        _init_tmdb(api_key)
        movie = Movie()
        details = movie.details(tmdb_id)
        return details
    except Exception as e:
        logger.error(
            f"Error fetching movie details for ID {tmdb_id}: {e}", exc_info=True
        )
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
        _init_tmdb(api_key)
        tv = TV()
        details = tv.details(tmdb_id)
        return details
    except Exception as e:
        logger.error(
            f"Error fetching TV show details for ID {tmdb_id}: {e}", exc_info=True
        )
        return {}
