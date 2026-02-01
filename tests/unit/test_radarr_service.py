"""
Unit tests for radarr_service.py - Radarr API integration.

Tests cover:
- API key validation
- Quality profiles fetching
- Root folders fetching
- System status retrieval
- Movie count retrieval
- Missing movies count calculation
- Error handling and logging
- URL normalization (trailing slash)
- Mock external PyArr API calls
"""

from unittest.mock import MagicMock, patch

import pytest

from listarr.services.radarr_service import (
    get_missing_movies_count,
    get_movie_count,
    get_quality_profiles,
    get_root_folders,
    get_system_status,
    validate_radarr_api_key,
)


class TestValidateRadarrAPIKey:
    """Tests for validate_radarr_api_key function."""

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_validate_radarr_api_key_with_valid_credentials(self, mock_radarr_class):
        """Test that valid credentials return True."""
        mock_radarr = MagicMock()
        mock_radarr.get_system_status.return_value = {"version": "4.5.2.7388"}
        mock_radarr_class.return_value = mock_radarr

        result = validate_radarr_api_key("http://localhost:7878", "valid_key")

        assert result is True
        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )
        mock_radarr.get_system_status.assert_called_once()

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_validate_radarr_api_key_adds_trailing_slash(self, mock_radarr_class):
        """Test that base_url gets trailing slash added."""
        mock_radarr = MagicMock()
        mock_radarr.get_system_status.return_value = {"version": "4.5.2.7388"}
        mock_radarr_class.return_value = mock_radarr

        result = validate_radarr_api_key("http://localhost:7878", "valid_key")

        assert result is True
        # Verify URL was normalized with trailing slash
        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_validate_radarr_api_key_with_invalid_credentials(self, mock_radarr_class):
        """Test that invalid credentials return False."""
        mock_radarr = MagicMock()
        mock_radarr.get_system_status.side_effect = Exception("Unauthorized")
        mock_radarr_class.return_value = mock_radarr

        result = validate_radarr_api_key("http://localhost:7878", "invalid_key")

        assert result is False

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_validate_radarr_api_key_handles_connection_error(self, mock_radarr_class):
        """Test that connection errors return False."""
        mock_radarr_class.side_effect = ConnectionError("Connection refused")

        result = validate_radarr_api_key("http://localhost:7878", "valid_key")

        assert result is False

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_validate_radarr_api_key_handles_timeout(self, mock_radarr_class):
        """Test that timeouts return False."""
        mock_radarr = MagicMock()
        mock_radarr.get_system_status.side_effect = TimeoutError("Request timeout")
        mock_radarr_class.return_value = mock_radarr

        result = validate_radarr_api_key("http://localhost:7878", "valid_key")

        assert result is False


class TestGetQualityProfiles:
    """Tests for get_quality_profiles function."""

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_quality_profiles_returns_formatted_list(self, mock_radarr_class):
        """Test that quality profiles are returned in correct format."""
        mock_radarr = MagicMock()
        mock_radarr.get_quality_profile.return_value = [
            {"id": 1, "name": "HD-1080p", "items": []},
            {"id": 2, "name": "Ultra-HD", "items": []},
            {"id": 3, "name": "SD", "items": []},
        ]
        mock_radarr_class.return_value = mock_radarr

        result = get_quality_profiles("http://localhost:7878", "valid_key")

        assert len(result) == 3
        assert result[0] == {"id": 1, "name": "HD-1080p"}
        assert result[1] == {"id": 2, "name": "Ultra-HD"}
        assert result[2] == {"id": 3, "name": "SD"}
        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_quality_profiles_adds_trailing_slash(self, mock_radarr_class):
        """Test that base_url gets trailing slash added."""
        mock_radarr = MagicMock()
        mock_radarr.get_quality_profile.return_value = []
        mock_radarr_class.return_value = mock_radarr

        get_quality_profiles("http://localhost:7878", "valid_key")

        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_quality_profiles_returns_empty_list_on_error(self, mock_radarr_class):
        """Test that errors return empty list."""
        mock_radarr = MagicMock()
        mock_radarr.get_quality_profile.side_effect = Exception("API Error")
        mock_radarr_class.return_value = mock_radarr

        result = get_quality_profiles("http://localhost:7878", "invalid_key")

        assert result == []

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_quality_profiles_handles_empty_response(self, mock_radarr_class):
        """Test that empty API response returns empty list."""
        mock_radarr = MagicMock()
        mock_radarr.get_quality_profile.return_value = []
        mock_radarr_class.return_value = mock_radarr

        result = get_quality_profiles("http://localhost:7878", "valid_key")

        assert result == []


class TestGetRootFolders:
    """Tests for get_root_folders function."""

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_root_folders_returns_formatted_list(self, mock_radarr_class):
        """Test that root folders are returned in correct format."""
        mock_radarr = MagicMock()
        mock_radarr.get_root_folder.return_value = [
            {"id": 1, "path": "/movies", "freeSpace": 1000000000},
            {"id": 2, "path": "/storage/movies", "freeSpace": 2000000000},
        ]
        mock_radarr_class.return_value = mock_radarr

        result = get_root_folders("http://localhost:7878", "valid_key")

        assert len(result) == 2
        assert result[0] == {"id": 1, "path": "/movies"}
        assert result[1] == {"id": 2, "path": "/storage/movies"}
        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_root_folders_adds_trailing_slash(self, mock_radarr_class):
        """Test that base_url gets trailing slash added."""
        mock_radarr = MagicMock()
        mock_radarr.get_root_folder.return_value = []
        mock_radarr_class.return_value = mock_radarr

        get_root_folders("http://localhost:7878", "valid_key")

        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_root_folders_returns_empty_list_on_error(self, mock_radarr_class):
        """Test that errors return empty list."""
        mock_radarr = MagicMock()
        mock_radarr.get_root_folder.side_effect = Exception("API Error")
        mock_radarr_class.return_value = mock_radarr

        result = get_root_folders("http://localhost:7878", "invalid_key")

        assert result == []


class TestGetSystemStatus:
    """Tests for get_system_status function."""

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_system_status_returns_formatted_dict(self, mock_radarr_class):
        """Test that system status is returned in correct format."""
        mock_radarr = MagicMock()
        mock_radarr.get_system_status.return_value = {
            "version": "4.5.2.7388",
            "instanceName": "Radarr",
            "isProduction": True,
            "isDebug": False,
        }
        mock_radarr_class.return_value = mock_radarr

        result = get_system_status("http://localhost:7878", "valid_key")

        assert result == {
            "version": "4.5.2.7388",
            "instance_name": "Radarr",
            "is_production": True,
            "is_debug": False,
        }
        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_system_status_handles_missing_fields(self, mock_radarr_class):
        """Test that missing fields use defaults."""
        mock_radarr = MagicMock()
        mock_radarr.get_system_status.return_value = {
            "version": "4.5.2.7388",
            "instanceName": "Radarr"
            # Missing isProduction and isDebug
        }
        mock_radarr_class.return_value = mock_radarr

        result = get_system_status("http://localhost:7878", "valid_key")

        assert result["version"] == "4.5.2.7388"
        assert result["instance_name"] == "Radarr"
        assert result["is_production"] is False  # Default
        assert result["is_debug"] is False  # Default

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_system_status_returns_empty_dict_on_error(self, mock_radarr_class):
        """Test that errors return empty dict."""
        mock_radarr = MagicMock()
        mock_radarr.get_system_status.side_effect = Exception("API Error")
        mock_radarr_class.return_value = mock_radarr

        result = get_system_status("http://localhost:7878", "invalid_key")

        assert result == {}

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_system_status_adds_trailing_slash(self, mock_radarr_class):
        """Test that base_url gets trailing slash added."""
        mock_radarr = MagicMock()
        mock_radarr.get_system_status.return_value = {}
        mock_radarr_class.return_value = mock_radarr

        get_system_status("http://localhost:7878", "valid_key")

        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )


class TestGetMovieCount:
    """Tests for get_movie_count function."""

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_movie_count_returns_correct_count(self, mock_radarr_class):
        """Test that movie count is calculated correctly."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.return_value = [
            {"id": 1, "title": "Movie 1"},
            {"id": 2, "title": "Movie 2"},
            {"id": 3, "title": "Movie 3"},
        ]
        mock_radarr_class.return_value = mock_radarr

        result = get_movie_count("http://localhost:7878", "valid_key")

        assert result == 3
        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_movie_count_returns_zero_for_empty_list(self, mock_radarr_class):
        """Test that empty movie list returns 0."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.return_value = []
        mock_radarr_class.return_value = mock_radarr

        result = get_movie_count("http://localhost:7878", "valid_key")

        assert result == 0

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_movie_count_returns_zero_for_none(self, mock_radarr_class):
        """Test that None response returns 0."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.return_value = None
        mock_radarr_class.return_value = mock_radarr

        result = get_movie_count("http://localhost:7878", "valid_key")

        assert result == 0

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_movie_count_returns_zero_on_error(self, mock_radarr_class):
        """Test that errors return 0."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.side_effect = Exception("API Error")
        mock_radarr_class.return_value = mock_radarr

        result = get_movie_count("http://localhost:7878", "invalid_key")

        assert result == 0

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_movie_count_adds_trailing_slash(self, mock_radarr_class):
        """Test that base_url gets trailing slash added."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.return_value = []
        mock_radarr_class.return_value = mock_radarr

        get_movie_count("http://localhost:7878", "valid_key")

        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )


class TestGetMissingMoviesCount:
    """Tests for get_missing_movies_count function."""

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_missing_movies_count_counts_monitored_without_file(self, mock_radarr_class):
        """Test that missing movies are counted correctly."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.return_value = [
            {
                "id": 1,
                "title": "Movie 1",
                "monitored": True,
                "hasFile": False,
            },  # Missing
            {
                "id": 2,
                "title": "Movie 2",
                "monitored": True,
                "hasFile": True,
            },  # Has file
            {
                "id": 3,
                "title": "Movie 3",
                "monitored": False,
                "hasFile": False,
            },  # Not monitored
            {
                "id": 4,
                "title": "Movie 4",
                "monitored": True,
                "hasFile": False,
            },  # Missing
        ]
        mock_radarr_class.return_value = mock_radarr

        result = get_missing_movies_count("http://localhost:7878", "valid_key")

        assert result == 2  # Only movies 1 and 4 are monitored and missing files

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_missing_movies_count_returns_zero_for_empty_list(self, mock_radarr_class):
        """Test that empty movie list returns 0."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.return_value = []
        mock_radarr_class.return_value = mock_radarr

        result = get_missing_movies_count("http://localhost:7878", "valid_key")

        assert result == 0

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_missing_movies_count_handles_missing_fields(self, mock_radarr_class):
        """Test that missing fields are handled gracefully."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.return_value = [
            {"id": 1, "title": "Movie 1"},  # Missing monitored and hasFile fields
            {"id": 2, "title": "Movie 2", "monitored": True},  # Missing hasFile
            {"id": 3, "title": "Movie 3", "hasFile": False},  # Missing monitored
        ]
        mock_radarr_class.return_value = mock_radarr

        result = get_missing_movies_count("http://localhost:7878", "valid_key")

        # All should be treated as not missing (defaults to False)
        assert result == 0

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_missing_movies_count_returns_zero_on_error(self, mock_radarr_class):
        """Test that errors return 0."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.side_effect = Exception("API Error")
        mock_radarr_class.return_value = mock_radarr

        result = get_missing_movies_count("http://localhost:7878", "invalid_key")

        assert result == 0

    @patch("listarr.services.radarr_service.RadarrAPI")
    def test_get_missing_movies_count_adds_trailing_slash(self, mock_radarr_class):
        """Test that base_url gets trailing slash added."""
        mock_radarr = MagicMock()
        mock_radarr.get_movie.return_value = []
        mock_radarr_class.return_value = mock_radarr

        get_missing_movies_count("http://localhost:7878", "valid_key")

        mock_radarr_class.assert_called_once_with(
            host_url="http://localhost:7878/", api_key="valid_key"
        )
