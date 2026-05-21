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

from unittest.mock import MagicMock, patch

import pytest
import requests

from listarr.services.tmdb_service import (
    discover_movies,
    discover_tv,
    get_imdb_id_from_tmdb,
    get_movie_details,
    get_popular_movies,
    get_popular_tv,
    get_top_rated_movies,
    get_top_rated_tv,
    get_trending_movies,
    get_trending_tv,
    get_tv_details,
    get_tvdb_id_from_tmdb,
    validate_tmdb_api_key,
)


class TestTMDBAPIKeyValidation:
    """Tests for TMDB API key validation."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_validate_tmdb_api_key_with_valid_key(self, mock_session):
        """Test that valid API key returns True."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = validate_tmdb_api_key("valid_key_12345")

        assert result is True
        mock_session.get.assert_called_once()

    @patch("listarr.services.tmdb_service.http_session")
    def test_validate_tmdb_api_key_with_invalid_key(self, mock_session):
        """Test that invalid API key returns False."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("Invalid API key")

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

    @patch("listarr.services.tmdb_service.http_session")
    def test_validate_tmdb_api_key_handles_network_error(self, mock_session):
        """Test that network errors return False."""
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Network error")

        result = validate_tmdb_api_key("valid_key")

        assert result is False


class TestGetTVDBID:
    """Tests for TVDB ID retrieval."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_tvdb_id_from_tmdb(self, mock_session):
        """Test retrieving TVDB ID for a TV show."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"tvdb_id": 12345}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_tvdb_id_from_tmdb(550, "test_key")

        assert result == 12345
        mock_session.get.assert_called_once()

    def test_get_tvdb_id_with_empty_api_key(self):
        """Test that empty API key returns None."""
        result = get_tvdb_id_from_tmdb(123, "")

        assert result is None

    def test_get_tvdb_id_with_none_tmdb_id(self):
        """Test that None TMDB ID returns None."""
        result = get_tvdb_id_from_tmdb(None, "test_key")

        assert result is None

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_tvdb_id_handles_exception(self, mock_session):
        """Test that exceptions are caught and None is returned."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("API error")

        result = get_tvdb_id_from_tmdb(123, "test_key")

        assert result is None


class TestGetIMDBID:
    """Tests for IMDB ID retrieval."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_imdb_id_from_tmdb_for_movie(self, mock_session):
        """Test retrieving IMDB ID for a movie."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"imdb_id": "tt1234567"}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_imdb_id_from_tmdb(550, "test_key", media_type="movie")

        assert result == "tt1234567"
        mock_session.get.assert_called_once()
        # Verify URL contains /movie/
        call_args = mock_session.get.call_args
        assert "/movie/550/external_ids" in call_args[0][0]

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_imdb_id_from_tmdb_for_tv(self, mock_session):
        """Test retrieving IMDB ID for a TV show."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"imdb_id": "tt7654321"}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_imdb_id_from_tmdb(1234, "test_key", media_type="tv")

        assert result == "tt7654321"
        mock_session.get.assert_called_once()
        # Verify URL contains /tv/
        call_args = mock_session.get.call_args
        assert "/tv/1234/external_ids" in call_args[0][0]

    def test_get_imdb_id_with_invalid_media_type(self):
        """Test that invalid media_type returns None."""
        result = get_imdb_id_from_tmdb(123, "test_key", media_type="invalid")

        assert result is None

    def test_get_imdb_id_with_empty_api_key(self):
        """Test that empty API key returns None."""
        result = get_imdb_id_from_tmdb(123, "", media_type="movie")

        assert result is None

    def test_get_imdb_id_with_none_tmdb_id(self):
        """Test that None TMDB ID returns None."""
        result = get_imdb_id_from_tmdb(None, "test_key", media_type="movie")

        assert result is None

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_imdb_id_handles_missing_imdb_id(self, mock_session):
        """Test handling when IMDB ID is not available."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No IMDB ID
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_imdb_id_from_tmdb(123, "test_key", media_type="movie")

        assert result is None

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_imdb_id_handles_exception(self, mock_session):
        """Test that exceptions are caught and None is returned."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("API error")

        result = get_imdb_id_from_tmdb(123, "test_key", media_type="movie")

        assert result is None


class TestGetTrendingMovies:
    """Tests for trending movies retrieval."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_trending_movies_week(self, mock_session):
        """Test fetching trending movies for the week."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": 1, "title": "Movie 1"},
                {"id": 2, "title": "Movie 2"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_trending_movies("test_key", time_window="week", page=1)

        assert len(result) == 2
        assert result[0]["title"] == "Movie 1"
        # Verify URL contains /week
        call_args = mock_session.get.call_args
        assert "/trending/movie/week" in call_args[0][0]

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_trending_movies_day(self, mock_session):
        """Test fetching trending movies for the day."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 3, "title": "Movie 3"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_trending_movies("test_key", time_window="day", page=1)

        assert len(result) == 1
        # Verify URL contains /day
        call_args = mock_session.get.call_args
        assert "/trending/movie/day" in call_args[0][0]

    def test_get_trending_movies_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = get_trending_movies("", time_window="week")

        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_trending_movies_handles_exception(self, mock_session):
        """Test that exceptions return empty list."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("API error")

        result = get_trending_movies("test_key", time_window="week")

        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_trending_movies_with_pagination(self, mock_session):
        """Test fetching trending movies with specific page."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 1}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        get_trending_movies("test_key", time_window="week", page=3)

        # Verify page parameter was passed
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["page"] == 3


class TestGetTrendingTV:
    """Tests for trending TV shows retrieval."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_trending_tv_week(self, mock_session):
        """Test fetching trending TV shows for the week."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 10, "name": "TV Show 1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_trending_tv("test_key", time_window="week", page=1)

        assert len(result) == 1
        assert result[0]["name"] == "TV Show 1"
        # Verify URL contains /week
        call_args = mock_session.get.call_args
        assert "/trending/tv/week" in call_args[0][0]

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_trending_tv_day(self, mock_session):
        """Test fetching trending TV shows for the day."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_trending_tv("test_key", time_window="day", page=1)

        assert result == []
        # Verify URL contains /day
        call_args = mock_session.get.call_args
        assert "/trending/tv/day" in call_args[0][0]


class TestGetPopularMovies:
    """Tests for popular movies retrieval."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_popular_movies(self, mock_session):
        """Test fetching popular movies."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 100, "title": "Popular Movie"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_popular_movies("test_key", page=1)

        assert len(result) == 1
        assert result[0]["title"] == "Popular Movie"
        # Verify URL
        call_args = mock_session.get.call_args
        assert "/movie/popular" in call_args[0][0]

    def test_get_popular_movies_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = get_popular_movies("")

        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_popular_movies_handles_exception(self, mock_session):
        """Test that exceptions return empty list."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("Error")

        result = get_popular_movies("test_key")

        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_popular_movies_with_region(self, mock_session):
        """Test fetching popular movies with region."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 1, "title": "US Movie"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_popular_movies("test_key", page=1, region="US")

        assert len(result) == 1
        # Verify region parameter was passed
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["region"] == "US"


class TestGetPopularTV:
    """Tests for popular TV shows retrieval."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_popular_tv(self, mock_session):
        """Test fetching popular TV shows."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 200, "name": "Popular TV Show"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_popular_tv("test_key", page=1)

        assert len(result) == 1
        assert result[0]["name"] == "Popular TV Show"
        # Verify URL
        call_args = mock_session.get.call_args
        assert "/tv/popular" in call_args[0][0]


class TestGetTopRatedMovies:
    """Tests for top rated movies retrieval (Phase 6.2)."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_top_rated_movies_returns_results(self, mock_session):
        """Test fetching top rated movies successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": 238, "title": "The Godfather", "vote_average": 8.7},
                {"id": 278, "title": "The Shawshank Redemption", "vote_average": 8.7},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_top_rated_movies("test_key", page=1)

        assert len(result) == 2
        assert result[0]["title"] == "The Godfather"
        # Verify URL
        call_args = mock_session.get.call_args
        assert "/movie/top_rated" in call_args[0][0]

    def test_get_top_rated_movies_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = get_top_rated_movies("")
        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_top_rated_movies_handles_exception(self, mock_session):
        """Test that API exceptions return empty list."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("API error")

        result = get_top_rated_movies("test_key")
        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_top_rated_movies_with_pagination(self, mock_session):
        """Test fetching top rated movies with specific page."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 1}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        get_top_rated_movies("test_key", page=5)

        # Verify page parameter was passed
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["page"] == 5

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_top_rated_movies_with_region(self, mock_session):
        """Test fetching top rated movies with region."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 1}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        get_top_rated_movies("test_key", page=1, region="US")

        # Verify region parameter was passed
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["region"] == "US"


class TestGetTopRatedTV:
    """Tests for top rated TV shows retrieval (Phase 6.2)."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_top_rated_tv_returns_results(self, mock_session):
        """Test fetching top rated TV shows successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": 1396, "name": "Breaking Bad", "vote_average": 8.9},
                {"id": 1399, "name": "Game of Thrones", "vote_average": 8.4},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_top_rated_tv("test_key", page=1)

        assert len(result) == 2
        assert result[0]["name"] == "Breaking Bad"
        # Verify URL
        call_args = mock_session.get.call_args
        assert "/tv/top_rated" in call_args[0][0]

    def test_get_top_rated_tv_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = get_top_rated_tv("")
        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_top_rated_tv_handles_exception(self, mock_session):
        """Test that API exceptions return empty list."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("API error")

        result = get_top_rated_tv("test_key")
        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_top_rated_tv_with_pagination(self, mock_session):
        """Test fetching top rated TV with specific page."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        get_top_rated_tv("test_key", page=3)

        # Verify page parameter was passed
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["page"] == 3


class TestDiscoverMovies:
    """Tests for movie discovery with filters."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_discover_movies_with_filters(self, mock_session):
        """Test discovering movies with filters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 300, "title": "Filtered Movie"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        filters = {
            "with_genres": "28",
            "primary_release_year": 2023,
            "vote_average.gte": 7.0,
        }

        result = discover_movies("test_key", filters=filters, page=1)

        assert len(result) == 1
        # Verify filters were passed
        call_args = mock_session.get.call_args
        params = call_args[1]["params"]
        assert params["with_genres"] == "28"
        assert params["primary_release_year"] == 2023
        assert params["vote_average.gte"] == 7.0
        assert params["page"] == 1

    @patch("listarr.services.tmdb_service.http_session")
    def test_discover_movies_without_filters(self, mock_session):
        """Test discovering movies without filters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = discover_movies("test_key", filters=None, page=1)

        assert result == []
        # Should still be called with page parameter
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["page"] == 1

    def test_discover_movies_with_empty_api_key(self):
        """Test that empty API key returns empty list."""
        result = discover_movies("")

        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_discover_movies_handles_exception(self, mock_session):
        """Test that exceptions return empty list."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("Error")

        result = discover_movies("test_key")

        assert result == []

    @patch("listarr.services.tmdb_service.http_session")
    def test_discover_movies_with_region(self, mock_session):
        """Test discovering movies with region."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 1}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        discover_movies("test_key", filters=None, page=1, region="US")

        # Verify region parameter was passed
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["region"] == "US"


class TestDiscoverTV:
    """Tests for TV show discovery with filters."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_discover_tv_with_filters(self, mock_session):
        """Test discovering TV shows with filters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 400, "name": "Filtered TV"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        filters = {"with_genres": "18", "first_air_date_year": 2023}

        result = discover_tv("test_key", filters=filters, page=1)

        assert len(result) == 1
        # Verify URL
        call_args = mock_session.get.call_args
        assert "/discover/tv" in call_args[0][0]

    @patch("listarr.services.tmdb_service.http_session")
    def test_discover_tv_with_region(self, mock_session):
        """Test discovering TV with region."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": 1}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        discover_tv("test_key", filters=None, page=1, region="GB")

        # Verify region parameter was passed
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["region"] == "GB"


class TestGetMovieDetails:
    """Tests for movie details retrieval."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_movie_details(self, mock_session):
        """Test fetching detailed movie information."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 550,
            "title": "Fight Club",
            "runtime": 139,
            "genres": [{"id": 18, "name": "Drama"}],
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_movie_details(550, "test_key")

        assert result["id"] == 550
        assert result["title"] == "Fight Club"
        assert result["runtime"] == 139
        # Verify URL
        call_args = mock_session.get.call_args
        assert "/movie/550" in call_args[0][0]

    def test_get_movie_details_with_empty_api_key(self):
        """Test that empty API key returns empty dict."""
        result = get_movie_details(123, "")

        assert result == {}

    def test_get_movie_details_with_none_tmdb_id(self):
        """Test that None TMDB ID returns empty dict."""
        result = get_movie_details(None, "test_key")

        assert result == {}

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_movie_details_handles_exception(self, mock_session):
        """Test that exceptions return empty dict."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("Not found")

        result = get_movie_details(123, "test_key")

        assert result == {}


class TestGetTVDetails:
    """Tests for TV show details retrieval."""

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_tv_details(self, mock_session):
        """Test fetching detailed TV show information."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 1234,
            "name": "Breaking Bad",
            "number_of_seasons": 5,
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = get_tv_details(1234, "test_key")

        assert result["id"] == 1234
        assert result["name"] == "Breaking Bad"
        # Verify URL
        call_args = mock_session.get.call_args
        assert "/tv/1234" in call_args[0][0]

    def test_get_tv_details_with_empty_api_key(self):
        """Test that empty API key returns empty dict."""
        result = get_tv_details(123, "")

        assert result == {}

    def test_get_tv_details_with_none_tmdb_id(self):
        """Test that None TMDB ID returns empty dict."""
        result = get_tv_details(None, "test_key")

        assert result == {}

    @patch("listarr.services.tmdb_service.http_session")
    def test_get_tv_details_handles_exception(self, mock_session):
        """Test that exceptions return empty dict."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("Not found")

        result = get_tv_details(123, "test_key")

        assert result == {}
