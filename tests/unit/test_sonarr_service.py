"""
Unit tests for sonarr_service.py - Sonarr API integration.

Tests cover:
- API key validation
- Quality profiles fetching
- Root folders fetching
- System status retrieval
- Series count retrieval
- Missing series count calculation
- Error handling and logging
- URL normalization (trailing slash)
- Mock external PyArr API calls
"""

from unittest.mock import MagicMock, patch

import pytest

from listarr.services.sonarr_service import (
    get_missing_series_count,
    get_quality_profiles,
    get_root_folders,
    get_series_count,
    get_system_status,
    validate_sonarr_api_key,
)


class TestValidateSonarrAPIKey:
    """Tests for validate_sonarr_api_key function."""

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_validate_sonarr_api_key_with_valid_credentials(self, mock_sonarr_class):
        """Test that valid credentials return True."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_system_status.return_value = {"version": "4.0.0.800"}
        mock_sonarr_class.return_value = mock_sonarr

        result = validate_sonarr_api_key("http://localhost:8989", "valid_key")

        assert result is True
        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")
        mock_sonarr.get_system_status.assert_called_once()

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_validate_sonarr_api_key_adds_trailing_slash(self, mock_sonarr_class):
        """Test that base_url gets trailing slash added."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_system_status.return_value = {"version": "4.0.0.800"}
        mock_sonarr_class.return_value = mock_sonarr

        result = validate_sonarr_api_key("http://localhost:8989", "valid_key")

        assert result is True
        # Verify URL was normalized with trailing slash
        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_validate_sonarr_api_key_with_invalid_credentials(self, mock_sonarr_class):
        """Test that invalid credentials return False."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_system_status.side_effect = Exception("Unauthorized")
        mock_sonarr_class.return_value = mock_sonarr

        result = validate_sonarr_api_key("http://localhost:8989", "invalid_key")

        assert result is False

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_validate_sonarr_api_key_handles_connection_error(self, mock_sonarr_class):
        """Test that connection errors return False."""
        mock_sonarr_class.side_effect = ConnectionError("Connection refused")

        result = validate_sonarr_api_key("http://localhost:8989", "valid_key")

        assert result is False

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_validate_sonarr_api_key_handles_timeout(self, mock_sonarr_class):
        """Test that timeouts return False."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_system_status.side_effect = TimeoutError("Request timeout")
        mock_sonarr_class.return_value = mock_sonarr

        result = validate_sonarr_api_key("http://localhost:8989", "valid_key")

        assert result is False


class TestGetQualityProfiles:
    """Tests for get_quality_profiles function."""

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_quality_profiles_returns_formatted_list(self, mock_sonarr_class):
        """Test that quality profiles are returned in correct format."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_quality_profile.return_value = [
            {"id": 1, "name": "HD-1080p", "items": []},
            {"id": 2, "name": "Ultra-HD", "items": []},
            {"id": 3, "name": "SD", "items": []},
        ]
        mock_sonarr_class.return_value = mock_sonarr

        result = get_quality_profiles("http://localhost:8989", "valid_key")

        assert len(result) == 3
        assert result[0] == {"id": 1, "name": "HD-1080p"}
        assert result[1] == {"id": 2, "name": "Ultra-HD"}
        assert result[2] == {"id": 3, "name": "SD"}
        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_quality_profiles_adds_trailing_slash(self, mock_sonarr_class):
        """Test that base_url gets trailing slash added."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_quality_profile.return_value = []
        mock_sonarr_class.return_value = mock_sonarr

        get_quality_profiles("http://localhost:8989", "valid_key")

        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_quality_profiles_returns_empty_list_on_error(self, mock_sonarr_class):
        """Test that errors return empty list."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_quality_profile.side_effect = Exception("API Error")
        mock_sonarr_class.return_value = mock_sonarr

        result = get_quality_profiles("http://localhost:8989", "invalid_key")

        assert result == []

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_quality_profiles_handles_empty_response(self, mock_sonarr_class):
        """Test that empty API response returns empty list."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_quality_profile.return_value = []
        mock_sonarr_class.return_value = mock_sonarr

        result = get_quality_profiles("http://localhost:8989", "valid_key")

        assert result == []


class TestGetRootFolders:
    """Tests for get_root_folders function."""

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_root_folders_returns_formatted_list(self, mock_sonarr_class):
        """Test that root folders are returned in correct format."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_root_folder.return_value = [
            {"id": 1, "path": "/tv", "freeSpace": 1000000000},
            {"id": 2, "path": "/storage/tv", "freeSpace": 2000000000},
        ]
        mock_sonarr_class.return_value = mock_sonarr

        result = get_root_folders("http://localhost:8989", "valid_key")

        assert len(result) == 2
        assert result[0] == {"id": 1, "path": "/tv"}
        assert result[1] == {"id": 2, "path": "/storage/tv"}
        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_root_folders_adds_trailing_slash(self, mock_sonarr_class):
        """Test that base_url gets trailing slash added."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_root_folder.return_value = []
        mock_sonarr_class.return_value = mock_sonarr

        get_root_folders("http://localhost:8989", "valid_key")

        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_root_folders_returns_empty_list_on_error(self, mock_sonarr_class):
        """Test that errors return empty list."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_root_folder.side_effect = Exception("API Error")
        mock_sonarr_class.return_value = mock_sonarr

        result = get_root_folders("http://localhost:8989", "invalid_key")

        assert result == []


class TestGetSystemStatus:
    """Tests for get_system_status function."""

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_system_status_returns_formatted_dict(self, mock_sonarr_class):
        """Test that system status is returned in correct format."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_system_status.return_value = {
            "version": "4.0.0.800",
            "instanceName": "Sonarr",
            "isProduction": True,
            "isDebug": False,
        }
        mock_sonarr_class.return_value = mock_sonarr

        result = get_system_status("http://localhost:8989", "valid_key")

        assert result == {
            "version": "4.0.0.800",
            "instance_name": "Sonarr",
            "is_production": True,
            "is_debug": False,
        }
        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_system_status_handles_missing_fields(self, mock_sonarr_class):
        """Test that missing fields use defaults."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_system_status.return_value = {
            "version": "4.0.0.800",
            "instanceName": "Sonarr",
            # Missing isProduction and isDebug
        }
        mock_sonarr_class.return_value = mock_sonarr

        result = get_system_status("http://localhost:8989", "valid_key")

        assert result["version"] == "4.0.0.800"
        assert result["instance_name"] == "Sonarr"
        assert result["is_production"] is False  # Default
        assert result["is_debug"] is False  # Default

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_system_status_returns_empty_dict_on_error(self, mock_sonarr_class):
        """Test that errors return empty dict."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_system_status.side_effect = Exception("API Error")
        mock_sonarr_class.return_value = mock_sonarr

        result = get_system_status("http://localhost:8989", "invalid_key")

        assert result == {}

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_system_status_adds_trailing_slash(self, mock_sonarr_class):
        """Test that base_url gets trailing slash added."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_system_status.return_value = {}
        mock_sonarr_class.return_value = mock_sonarr

        get_system_status("http://localhost:8989", "valid_key")

        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")


class TestGetSeriesCount:
    """Tests for get_series_count function."""

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_series_count_returns_correct_count(self, mock_sonarr_class):
        """Test that series count is calculated correctly."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_series.return_value = [
            {"id": 1, "title": "Series 1"},
            {"id": 2, "title": "Series 2"},
            {"id": 3, "title": "Series 3"},
        ]
        mock_sonarr_class.return_value = mock_sonarr

        result = get_series_count("http://localhost:8989", "valid_key")

        assert result == 3
        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_series_count_returns_zero_for_empty_list(self, mock_sonarr_class):
        """Test that empty series list returns 0."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_series.return_value = []
        mock_sonarr_class.return_value = mock_sonarr

        result = get_series_count("http://localhost:8989", "valid_key")

        assert result == 0

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_series_count_returns_zero_for_none(self, mock_sonarr_class):
        """Test that None response returns 0."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_series.return_value = None
        mock_sonarr_class.return_value = mock_sonarr

        result = get_series_count("http://localhost:8989", "valid_key")

        assert result == 0

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_series_count_returns_zero_on_error(self, mock_sonarr_class):
        """Test that errors return 0."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_series.side_effect = Exception("API Error")
        mock_sonarr_class.return_value = mock_sonarr

        result = get_series_count("http://localhost:8989", "invalid_key")

        assert result == 0

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_series_count_adds_trailing_slash(self, mock_sonarr_class):
        """Test that base_url gets trailing slash added."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_series.return_value = []
        mock_sonarr_class.return_value = mock_sonarr

        get_series_count("http://localhost:8989", "valid_key")

        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")


class TestGetMissingSeriesCount:
    """Tests for get_missing_series_count function."""

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_missing_series_count_counts_series_with_missing_episodes(self, mock_sonarr_class):
        """Test that missing series are counted correctly using get_wanted()."""
        mock_sonarr = MagicMock()

        # Mock get_wanted() to return missing episodes from different series
        # Series 1 (ID: 1): Has 2 missing episodes
        # Series 2 (ID: 2): Has 1 missing episode
        # Series 3 (ID: 3): Has 1 missing episode
        mock_sonarr.get_wanted.return_value = {
            "records": [
                {"id": 101, "seriesId": 1, "title": "Episode 1.1"},  # Series 1
                {"id": 102, "seriesId": 1, "title": "Episode 1.2"},  # Series 1
                {"id": 201, "seriesId": 2, "title": "Episode 2.1"},  # Series 2
                {"id": 301, "seriesId": 3, "title": "Episode 3.1"},  # Series 3
            ]
        }
        mock_sonarr_class.return_value = mock_sonarr

        result = get_missing_series_count("http://localhost:8989", "valid_key")

        # Should count unique series: 1, 2, 3 = 3 series
        assert result == 3
        mock_sonarr.get_wanted.assert_called_once()

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_missing_series_count_returns_zero_for_empty_list(self, mock_sonarr_class):
        """Test that empty wanted list returns 0."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_wanted.return_value = {"records": []}
        mock_sonarr_class.return_value = mock_sonarr

        result = get_missing_series_count("http://localhost:8989", "valid_key")

        assert result == 0

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_missing_series_count_handles_none_response(self, mock_sonarr_class):
        """Test that None response returns 0."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_wanted.return_value = None
        mock_sonarr_class.return_value = mock_sonarr

        result = get_missing_series_count("http://localhost:8989", "valid_key")

        assert result == 0

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_missing_series_count_handles_missing_records_key(self, mock_sonarr_class):
        """Test that missing 'records' key returns 0."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_wanted.return_value = {}  # No 'records' key
        mock_sonarr_class.return_value = mock_sonarr

        result = get_missing_series_count("http://localhost:8989", "valid_key")

        assert result == 0

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_missing_series_count_uses_series_id_from_nested_series(self, mock_sonarr_class):
        """Test that seriesId can be extracted from nested series object."""
        mock_sonarr = MagicMock()
        # Some episodes might have series info nested instead of seriesId
        mock_sonarr.get_wanted.return_value = {
            "records": [
                {"id": 101, "seriesId": 1, "title": "Episode 1.1"},
                {
                    "id": 102,
                    "series": {"id": 2, "title": "Series 2"},
                    "title": "Episode 2.1",
                },
                {
                    "id": 103,
                    "seriesId": 1,
                    "title": "Episode 1.2",
                },  # Same series as first
            ]
        }
        mock_sonarr_class.return_value = mock_sonarr

        result = get_missing_series_count("http://localhost:8989", "valid_key")

        # Should count unique series: 1, 2 = 2 series
        assert result == 2

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_missing_series_count_handles_episodes_without_series_id(self, mock_sonarr_class):
        """Test that episodes without seriesId are skipped."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_wanted.return_value = {
            "records": [
                {"id": 101, "seriesId": 1, "title": "Episode 1.1"},
                {"id": 102, "title": "Episode without seriesId"},  # Missing seriesId
                {"id": 103, "seriesId": 2, "title": "Episode 2.1"},
            ]
        }
        mock_sonarr_class.return_value = mock_sonarr

        result = get_missing_series_count("http://localhost:8989", "valid_key")

        # Should count unique series: 1, 2 = 2 series (episode without seriesId skipped)
        assert result == 2

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_missing_series_count_returns_zero_on_error(self, mock_sonarr_class):
        """Test that API errors are handled gracefully."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_wanted.side_effect = Exception("API Error")
        mock_sonarr_class.return_value = mock_sonarr

        result = get_missing_series_count("http://localhost:8989", "invalid_key")

        # Should return 0 on error
        assert result == 0

    @patch("listarr.services.sonarr_service.SonarrAPI")
    def test_get_missing_series_count_adds_trailing_slash(self, mock_sonarr_class):
        """Test that base_url gets trailing slash added."""
        mock_sonarr = MagicMock()
        mock_sonarr.get_wanted.return_value = {"records": []}
        mock_sonarr_class.return_value = mock_sonarr

        get_missing_series_count("http://localhost:8989", "valid_key")

        mock_sonarr_class.assert_called_once_with(host_url="http://localhost:8989/", api_key="valid_key")
