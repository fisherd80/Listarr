"""
Integration tests for import_service.py - TMDB import workflows.

Tests cover:
- Top rated import flow (Phase 6.2)
- Fetching top_rated list types using cached functions
- Limit parameter controls
- Empty response handling
- API error handling
"""

from unittest.mock import MagicMock, patch

import pytest

from listarr.models.lists_model import List
from listarr.services.import_service import _fetch_tmdb_items


class TestFetchTMDBItemsTopRated:
    """Integration tests for top_rated list type handling in import service (Phase 6.2)."""

    @patch('listarr.services.import_service.get_top_rated_movies_cached')
    def test_fetches_top_rated_movies_using_cached_function(self, mock_cached, app):
        """Test that top_rated_movies list type uses cached function."""
        mock_cached.return_value = [
            {'id': 238, 'title': 'The Godfather'},
            {'id': 278, 'title': 'The Shawshank Redemption'}
        ]

        with app.app_context():
            # Create mock list object
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = 'top_rated_movies'
            list_obj.target_service = 'RADARR'
            list_obj.filters_json = {}
            list_obj.limit = 20

            result = _fetch_tmdb_items(list_obj, 'test_api_key')

            # Verify cached function was called
            mock_cached.assert_called_once_with('test_api_key', page=1)
            assert len(result) == 2
            assert result[0]['title'] == 'The Godfather'

    @patch('listarr.services.import_service.get_top_rated_tv_cached')
    def test_fetches_top_rated_tv_using_cached_function(self, mock_cached, app):
        """Test that top_rated_tv list type uses cached function."""
        mock_cached.return_value = [
            {'id': 1396, 'name': 'Breaking Bad'},
            {'id': 1399, 'name': 'Game of Thrones'}
        ]

        with app.app_context():
            # Create mock list object
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = 'top_rated_tv'
            list_obj.target_service = 'SONARR'
            list_obj.filters_json = {}
            list_obj.limit = 20

            result = _fetch_tmdb_items(list_obj, 'test_api_key')

            # Verify cached function was called
            mock_cached.assert_called_once_with('test_api_key', page=1)
            assert len(result) == 2
            assert result[0]['name'] == 'Breaking Bad'

    @patch('listarr.services.import_service.get_top_rated_movies_cached')
    def test_limit_parameter_controls_item_count(self, mock_cached, app):
        """Test that limit parameter controls number of items fetched."""
        # Mock first page returns 20 items
        page1_items = [{'id': i, 'title': f'Movie {i}'} for i in range(1, 21)]
        # Mock second page returns 20 items
        page2_items = [{'id': i, 'title': f'Movie {i}'} for i in range(21, 41)]
        # Mock third page returns 20 items
        page3_items = [{'id': i, 'title': f'Movie {i}'} for i in range(41, 61)]

        mock_cached.side_effect = [page1_items, page2_items, page3_items]

        with app.app_context():
            # Create mock list object with limit=50
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = 'top_rated_movies'
            list_obj.target_service = 'RADARR'
            list_obj.filters_json = {}
            list_obj.limit = 50

            result = _fetch_tmdb_items(list_obj, 'test_api_key')

            # Should fetch 3 pages (20 + 20 + 10 = 50)
            assert mock_cached.call_count == 3
            # Should return exactly 50 items (sliced to limit)
            assert len(result) == 50
            assert result[0]['id'] == 1
            assert result[49]['id'] == 50

    @patch('listarr.services.import_service.get_top_rated_movies_cached')
    def test_handles_empty_response_gracefully(self, mock_cached, app):
        """Test that empty TMDB response is handled gracefully."""
        mock_cached.return_value = []

        with app.app_context():
            # Create mock list object
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = 'top_rated_movies'
            list_obj.target_service = 'RADARR'
            list_obj.filters_json = {}
            list_obj.limit = 20

            result = _fetch_tmdb_items(list_obj, 'test_api_key')

            # Should return empty list without error
            assert result == []
            mock_cached.assert_called_once_with('test_api_key', page=1)

    @patch('listarr.services.import_service.get_top_rated_tv_cached')
    def test_handles_api_errors_gracefully(self, mock_cached, app):
        """Test that API errors are handled gracefully."""
        # Mock API error (cached function returns empty list on error)
        mock_cached.return_value = []

        with app.app_context():
            # Create mock list object
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = 'top_rated_tv'
            list_obj.target_service = 'SONARR'
            list_obj.filters_json = {}
            list_obj.limit = 20

            result = _fetch_tmdb_items(list_obj, 'test_api_key')

            # Should return empty list without raising exception
            assert result == []


class TestFetchTMDBItemsLimitBehavior:
    """Additional tests for multi-page fetching behavior."""

    @patch('listarr.services.import_service.get_top_rated_movies_cached')
    def test_stops_fetching_when_page_returns_less_than_20(self, mock_cached, app):
        """Test that fetching stops when page returns fewer than 20 items."""
        # Page 1: 20 items
        page1_items = [{'id': i, 'title': f'Movie {i}'} for i in range(1, 21)]
        # Page 2: Only 15 items (end of available content)
        page2_items = [{'id': i, 'title': f'Movie {i}'} for i in range(21, 36)]

        mock_cached.side_effect = [page1_items, page2_items]

        with app.app_context():
            # Request limit=100, but API only has 35 items
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = 'top_rated_movies'
            list_obj.target_service = 'RADARR'
            list_obj.filters_json = {}
            list_obj.limit = 100

            result = _fetch_tmdb_items(list_obj, 'test_api_key')

            # Should only fetch 2 pages (stops when page 2 returns <20)
            assert mock_cached.call_count == 2
            # Should return all 35 items
            assert len(result) == 35

    @patch('listarr.services.import_service.get_top_rated_movies_cached')
    def test_respects_limit_across_multiple_pages(self, mock_cached, app):
        """Test that limit is respected across multiple page fetches."""
        # Each page returns 20 items
        page1_items = [{'id': i, 'title': f'Movie {i}'} for i in range(1, 21)]
        page2_items = [{'id': i, 'title': f'Movie {i}'} for i in range(21, 41)]
        page3_items = [{'id': i, 'title': f'Movie {i}'} for i in range(41, 61)]
        page4_items = [{'id': i, 'title': f'Movie {i}'} for i in range(61, 81)]

        mock_cached.side_effect = [page1_items, page2_items, page3_items, page4_items]

        with app.app_context():
            # Request exactly 65 items
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = 'top_rated_movies'
            list_obj.target_service = 'RADARR'
            list_obj.filters_json = {}
            list_obj.limit = 65

            result = _fetch_tmdb_items(list_obj, 'test_api_key')

            # Should fetch 4 pages (20+20+20+5=65)
            assert mock_cached.call_count == 4
            # Should return exactly 65 items
            assert len(result) == 65
            assert result[0]['id'] == 1
            assert result[64]['id'] == 65
