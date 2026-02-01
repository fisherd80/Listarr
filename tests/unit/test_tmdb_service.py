"""
Unit tests for tmdb_service.py - TMDB API integration.

Tests cover:
- API key validation
- IMDB ID retrieval from TMDB
- Trending movies and TV shows
- Popular content fetching
- Discovery with filters
- Detailed information retrieval
- Error handling and logging
- Mock external API calls
"""

import pytest
from unittest.mock import patch, MagicMock
from listarr.services.tmdb_service import (
    validate_tmdb_api_key,
    get_imdb_id_from_tmdb,
    get_trending_movies,
    get_trending_tv,
    get_popular_movies,
    get_popular_tv,
    get_top_rated_movies,
    get_top_rated_tv,
    discover_movies,
    discover_tv,
    get_movie_details,
    get_tv_details,
    _init_tmdb
)


class TestInitTMDB:
    """Tests for TMDB client initialization."""

    def test_init_tmdb_sets_api_key(self):
        """Test that _init_tmdb properly configures TMDB client."""
        api_key = "test_key_12345"

        tmdb = _init_tmdb(api_key)

        assert tmdb.api_key == api_key
        assert tmdb.language == 'en'


class TestTMDBAPIKeyValidation:
    """Tests for TMDB API key validation."""

    @patch('listarr.services.tmdb_service.Movie')
    def test_validate_tmdb_api_key_with_valid_key(self, mock_movie_class):
        """Test that valid API key returns True."""
        # Mock Movie instance and popular() method
        mock_movie = MagicMock()
        mock_movie.popular.return_value = [{'id': 1, 'title': 'Test Movie'}]
        mock_movie_class.return_value = mock_movie

        result = validate_tmdb_api_key("valid_key_12345")

        assert result is True
        mock_movie.popular.assert_called_once_with(page=1)

    @patch('listarr.services.tmdb_service.Movie')
    def test_validate_tmdb_api_key_with_invalid_key(self, mock_movie_class):
        """Test that invalid API key returns False."""
        # Mock Movie to raise exception
        mock_movie = MagicMock()
        mock_movie.popular.side_effect = Exception("Invalid API key")
        mock_movie_class.return_value = mock_movie

        result = validate_tmdb_api_key("invalid_key")

        assert result is False

    def test_validate_tmdb_api_key_with_empty_key(self):
        """Test that empty API key returns False."""
        result = validate_tmdb_api_key("")

        assert result is False

    def test_validate_tmdb_api_key_with_none_key(self):
        """Test that None API key returns False."""
        result = validate_tmdb_api_key(None)

        assert result is False

    @patch('listarr.services.tmdb_service.Movie')
    def test_validate_tmdb_api_key_handles_network_error(self, mock_movie_class):
        """Test that network errors return False."""
        mock_movie = MagicMock()
        mock_movie.popular.side_effect = ConnectionError("Network error")
        mock_movie_class.return_value = mock_movie

        result = validate_tmdb_api_key("valid_key")

        assert result is False


class TestGetIMDBID:
    """Tests for IMDB ID retrieval."""

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_imdb_id_from_tmdb_for_movie(self, mock_init, mock_movie_class):
        """Test retrieving IMDB ID for a movie."""
        # Mock Movie.external_ids()
        mock_movie = MagicMock()
        mock_movie.external_ids.return_value = {'imdb_id': 'tt1234567'}
        mock_movie_class.return_value = mock_movie

        result = get_imdb_id_from_tmdb(550, "test_key", media_type='movie')

        assert result == 'tt1234567'
        mock_movie.external_ids.assert_called_once_with(550)

    @patch('listarr.services.tmdb_service.TV')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_imdb_id_from_tmdb_for_tv(self, mock_init, mock_tv_class):
        """Test retrieving IMDB ID for a TV show."""
        # Mock TV.external_ids()
        mock_tv = MagicMock()
        mock_tv.external_ids.return_value = {'imdb_id': 'tt7654321'}
        mock_tv_class.return_value = mock_tv

        result = get_imdb_id_from_tmdb(1234, "test_key", media_type='tv')

        assert result == 'tt7654321'
        mock_tv.external_ids.assert_called_once_with(1234)

    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_imdb_id_with_invalid_media_type(self, mock_init):
        """Test that invalid media_type returns None."""
        result = get_imdb_id_from_tmdb(123, "test_key", media_type='invalid')

        assert result is None

    def test_get_imdb_id_with_empty_api_key(self):
        """Test that empty API key returns None."""
        result = get_imdb_id_from_tmdb(123, "", media_type='movie')

        assert result is None

    def test_get_imdb_id_with_none_tmdb_id(self):
        """Test that None TMDB ID returns None."""
        result = get_imdb_id_from_tmdb(None, "test_key", media_type='movie')

        assert result is None

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_imdb_id_handles_missing_imdb_id(self, mock_init, mock_movie_class):
        """Test handling when IMDB ID is not available."""
        mock_movie = MagicMock()
        mock_movie.external_ids.return_value = {}  # No IMDB ID
        mock_movie_class.return_value = mock_movie

        result = get_imdb_id_from_tmdb(123, "test_key", media_type='movie')

        assert result is None

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_imdb_id_handles_exception(self, mock_init, mock_movie_class):
        """Test that exceptions are caught and None is returned."""
        mock_movie = MagicMock()
        mock_movie.external_ids.side_effect = Exception("API error")
        mock_movie_class.return_value = mock_movie

        result = get_imdb_id_from_tmdb(123, "test_key", media_type='movie')

        assert result is None


class TestGetTrendingMovies:
    """Tests for trending movies retrieval."""

    @patch('listarr.services.tmdb_service.Trending')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_trending_movies_week(self, mock_init, mock_trending_class):
        """Test fetching trending movies for the week."""
        mock_trending = MagicMock()
        mock_trending.movie_week.return_value = [
            {'id': 1, 'title': 'Movie 1'},
            {'id': 2, 'title': 'Movie 2'}
        ]
        mock_trending_class.return_value = mock_trending

        result = get_trending_movies("test_key", time_window='week', page=1)

        assert len(result) == 2
        assert result[0]['title'] == 'Movie 1'
        mock_trending.movie_week.assert_called_once_with(page=1)

    @patch('listarr.services.tmdb_service.Trending')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_trending_movies_day(self, mock_init, mock_trending_class):
        """Test fetching trending movies for the day."""
        mock_trending = MagicMock()
        mock_trending.movie_day.return_value = [
            {'id': 3, 'title': 'Movie 3'}
        ]
        mock_trending_class.return_value = mock_trending

        result = get_trending_movies("test_key", time_window='day', page=1)

        assert len(result) == 1
        mock_trending.movie_day.assert_called_once_with(page=1)

    def test_get_trending_movies_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = get_trending_movies("", time_window='week')

        assert result == []

    @patch('listarr.services.tmdb_service.Trending')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_trending_movies_handles_exception(self, mock_init, mock_trending_class):
        """Test that exceptions return empty list."""
        mock_trending = MagicMock()
        mock_trending.movie_week.side_effect = Exception("API error")
        mock_trending_class.return_value = mock_trending

        result = get_trending_movies("test_key", time_window='week')

        assert result == []

    @patch('listarr.services.tmdb_service.Trending')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_trending_movies_with_pagination(self, mock_init, mock_trending_class):
        """Test fetching trending movies with specific page."""
        mock_trending = MagicMock()
        mock_trending.movie_week.return_value = [{'id': 1}]
        mock_trending_class.return_value = mock_trending

        get_trending_movies("test_key", time_window='week', page=3)

        mock_trending.movie_week.assert_called_once_with(page=3)


class TestGetTrendingTV:
    """Tests for trending TV shows retrieval."""

    @patch('listarr.services.tmdb_service.Trending')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_trending_tv_week(self, mock_init, mock_trending_class):
        """Test fetching trending TV shows for the week."""
        mock_trending = MagicMock()
        mock_trending.tv_week.return_value = [
            {'id': 10, 'name': 'TV Show 1'}
        ]
        mock_trending_class.return_value = mock_trending

        result = get_trending_tv("test_key", time_window='week', page=1)

        assert len(result) == 1
        assert result[0]['name'] == 'TV Show 1'
        mock_trending.tv_week.assert_called_once_with(page=1)

    @patch('listarr.services.tmdb_service.Trending')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_trending_tv_day(self, mock_init, mock_trending_class):
        """Test fetching trending TV shows for the day."""
        mock_trending = MagicMock()
        mock_trending.tv_day.return_value = []
        mock_trending_class.return_value = mock_trending

        result = get_trending_tv("test_key", time_window='day', page=1)

        assert result == []
        mock_trending.tv_day.assert_called_once_with(page=1)


class TestGetPopularMovies:
    """Tests for popular movies retrieval."""

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_popular_movies(self, mock_init, mock_movie_class):
        """Test fetching popular movies."""
        mock_movie = MagicMock()
        mock_movie.popular.return_value = [
            {'id': 100, 'title': 'Popular Movie'}
        ]
        mock_movie_class.return_value = mock_movie

        result = get_popular_movies("test_key", page=1)

        assert len(result) == 1
        assert result[0]['title'] == 'Popular Movie'
        mock_movie.popular.assert_called_once_with(page=1)

    def test_get_popular_movies_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = get_popular_movies("")

        assert result == []

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_popular_movies_handles_exception(self, mock_init, mock_movie_class):
        """Test that exceptions return empty list."""
        mock_movie = MagicMock()
        mock_movie.popular.side_effect = Exception("Error")
        mock_movie_class.return_value = mock_movie

        result = get_popular_movies("test_key")

        assert result == []


class TestGetPopularTV:
    """Tests for popular TV shows retrieval."""

    @patch('listarr.services.tmdb_service.TV')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_popular_tv(self, mock_init, mock_tv_class):
        """Test fetching popular TV shows."""
        mock_tv = MagicMock()
        mock_tv.popular.return_value = [
            {'id': 200, 'name': 'Popular TV Show'}
        ]
        mock_tv_class.return_value = mock_tv

        result = get_popular_tv("test_key", page=1)

        assert len(result) == 1
        assert result[0]['name'] == 'Popular TV Show'
        mock_tv.popular.assert_called_once_with(page=1)


class TestGetTopRatedMovies:
    """Tests for top rated movies retrieval (Phase 6.2)."""

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_top_rated_movies_returns_results(self, mock_init, mock_movie_class):
        """Test fetching top rated movies successfully."""
        mock_movie = MagicMock()
        mock_movie.top_rated.return_value = [
            {'id': 238, 'title': 'The Godfather', 'vote_average': 8.7},
            {'id': 278, 'title': 'The Shawshank Redemption', 'vote_average': 8.7}
        ]
        mock_movie_class.return_value = mock_movie

        result = get_top_rated_movies("test_key", page=1)

        assert len(result) == 2
        assert result[0]['title'] == 'The Godfather'
        mock_movie.top_rated.assert_called_once_with(page=1)

    def test_get_top_rated_movies_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = get_top_rated_movies("")
        assert result == []

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_top_rated_movies_handles_exception(self, mock_init, mock_movie_class):
        """Test that API exceptions return empty list."""
        mock_movie = MagicMock()
        mock_movie.top_rated.side_effect = Exception("API error")
        mock_movie_class.return_value = mock_movie

        result = get_top_rated_movies("test_key")
        assert result == []

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_top_rated_movies_with_pagination(self, mock_init, mock_movie_class):
        """Test fetching top rated movies with specific page."""
        mock_movie = MagicMock()
        mock_movie.top_rated.return_value = [{'id': 1}]
        mock_movie_class.return_value = mock_movie

        get_top_rated_movies("test_key", page=5)

        mock_movie.top_rated.assert_called_once_with(page=5)


class TestGetTopRatedTV:
    """Tests for top rated TV shows retrieval (Phase 6.2)."""

    @patch('listarr.services.tmdb_service.TV')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_top_rated_tv_returns_results(self, mock_init, mock_tv_class):
        """Test fetching top rated TV shows successfully."""
        mock_tv = MagicMock()
        mock_tv.top_rated.return_value = [
            {'id': 1396, 'name': 'Breaking Bad', 'vote_average': 8.9},
            {'id': 1399, 'name': 'Game of Thrones', 'vote_average': 8.4}
        ]
        mock_tv_class.return_value = mock_tv

        result = get_top_rated_tv("test_key", page=1)

        assert len(result) == 2
        assert result[0]['name'] == 'Breaking Bad'
        mock_tv.top_rated.assert_called_once_with(page=1)

    def test_get_top_rated_tv_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = get_top_rated_tv("")
        assert result == []

    @patch('listarr.services.tmdb_service.TV')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_top_rated_tv_handles_exception(self, mock_init, mock_tv_class):
        """Test that API exceptions return empty list."""
        mock_tv = MagicMock()
        mock_tv.top_rated.side_effect = Exception("API error")
        mock_tv_class.return_value = mock_tv

        result = get_top_rated_tv("test_key")
        assert result == []

    @patch('listarr.services.tmdb_service.TV')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_top_rated_tv_with_pagination(self, mock_init, mock_tv_class):
        """Test fetching top rated TV with specific page."""
        mock_tv = MagicMock()
        mock_tv.top_rated.return_value = []
        mock_tv_class.return_value = mock_tv

        get_top_rated_tv("test_key", page=3)

        mock_tv.top_rated.assert_called_once_with(page=3)


class TestDiscoverMovies:
    """Tests for movie discovery with filters."""

    @patch('listarr.services.tmdb_service.Discover')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_discover_movies_with_filters(self, mock_init, mock_discover_class):
        """Test discovering movies with filters."""
        mock_discover = MagicMock()
        mock_discover.discover_movies.return_value = [
            {'id': 300, 'title': 'Filtered Movie'}
        ]
        mock_discover_class.return_value = mock_discover

        filters = {
            'with_genres': '28',
            'primary_release_year': 2023,
            'vote_average.gte': 7.0
        }

        result = discover_movies("test_key", filters=filters, page=1)

        assert len(result) == 1
        mock_discover.discover_movies.assert_called_once()

        # Verify filters were passed
        call_args = mock_discover.discover_movies.call_args[0][0]
        assert call_args['with_genres'] == '28'
        assert call_args['primary_release_year'] == 2023
        assert call_args['vote_average.gte'] == 7.0
        assert call_args['page'] == 1

    @patch('listarr.services.tmdb_service.Discover')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_discover_movies_without_filters(self, mock_init, mock_discover_class):
        """Test discovering movies without filters."""
        mock_discover = MagicMock()
        mock_discover.discover_movies.return_value = []
        mock_discover_class.return_value = mock_discover

        result = discover_movies("test_key", filters=None, page=1)

        assert result == []
        # Should still be called with page parameter
        call_args = mock_discover.discover_movies.call_args[0][0]
        assert call_args['page'] == 1

    def test_discover_movies_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = discover_movies("")

        assert result == []

    @patch('listarr.services.tmdb_service.Discover')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_discover_movies_handles_exception(self, mock_init, mock_discover_class):
        """Test that exceptions return empty list."""
        mock_discover = MagicMock()
        mock_discover.discover_movies.side_effect = Exception("Error")
        mock_discover_class.return_value = mock_discover

        result = discover_movies("test_key")

        assert result == []


class TestDiscoverTV:
    """Tests for TV show discovery with filters."""

    @patch('listarr.services.tmdb_service.Discover')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_discover_tv_with_filters(self, mock_init, mock_discover_class):
        """Test discovering TV shows with filters."""
        mock_discover = MagicMock()
        mock_discover.discover_tv_shows.return_value = [
            {'id': 400, 'name': 'Filtered TV'}
        ]
        mock_discover_class.return_value = mock_discover

        filters = {'with_genres': '18', 'first_air_date_year': 2023}

        result = discover_tv("test_key", filters=filters, page=1)

        assert len(result) == 1
        mock_discover.discover_tv_shows.assert_called_once()


class TestGetMovieDetails:
    """Tests for movie details retrieval."""

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_movie_details(self, mock_init, mock_movie_class):
        """Test fetching detailed movie information."""
        mock_movie = MagicMock()
        mock_movie.details.return_value = {
            'id': 550,
            'title': 'Fight Club',
            'runtime': 139,
            'genres': [{'id': 18, 'name': 'Drama'}]
        }
        mock_movie_class.return_value = mock_movie

        result = get_movie_details(550, "test_key")

        assert result['id'] == 550
        assert result['title'] == 'Fight Club'
        assert result['runtime'] == 139
        mock_movie.details.assert_called_once_with(550)

    def test_get_movie_details_with_empty_api_key(self):
        """Test that empty API key returns empty dict."""
        result = get_movie_details(123, "")

        assert result == {}

    def test_get_movie_details_with_none_tmdb_id(self):
        """Test that None TMDB ID returns empty dict."""
        result = get_movie_details(None, "test_key")

        assert result == {}

    @patch('listarr.services.tmdb_service.Movie')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_movie_details_handles_exception(self, mock_init, mock_movie_class):
        """Test that exceptions return empty dict."""
        mock_movie = MagicMock()
        mock_movie.details.side_effect = Exception("Not found")
        mock_movie_class.return_value = mock_movie

        result = get_movie_details(123, "test_key")

        assert result == {}


class TestGetTVDetails:
    """Tests for TV show details retrieval."""

    @patch('listarr.services.tmdb_service.TV')
    @patch('listarr.services.tmdb_service._init_tmdb')
    def test_get_tv_details(self, mock_init, mock_tv_class):
        """Test fetching detailed TV show information."""
        mock_tv = MagicMock()
        mock_tv.details.return_value = {
            'id': 1234,
            'name': 'Breaking Bad',
            'number_of_seasons': 5
        }
        mock_tv_class.return_value = mock_tv

        result = get_tv_details(1234, "test_key")

        assert result['id'] == 1234
        assert result['name'] == 'Breaking Bad'
        mock_tv.details.assert_called_once_with(1234)

    def test_get_tv_details_with_empty_api_key(self):
        """Test that empty API key returns empty dict."""
        result = get_tv_details(123, "")

        assert result == {}

    def test_get_tv_details_with_none_tmdb_id(self):
        """Test that None TMDB ID returns empty dict."""
        result = get_tv_details(None, "test_key")

        assert result == {}
