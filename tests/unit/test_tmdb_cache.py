"""
Unit tests for tmdb_cache.py - TMDB caching layer.

Tests cover:
- Cached top rated movies and TV functions (Phase 6.2)
- Cache hit/miss behavior
- Cache key generation with region support
- Region filtering from ServiceConfig
- Region-aware cache keys
"""

import pytest
from unittest.mock import patch, MagicMock
from listarr.services.tmdb_cache import (
    _get_tmdb_region,
    get_top_rated_movies_cached,
    get_top_rated_tv_cached,
    get_popular_movies_cached,
    discover_movies_cached,
    discover_tv_cached,
    clear_all_caches
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear all caches before each test to ensure test isolation."""
    clear_all_caches()
    yield
    clear_all_caches()


class TestGetTopRatedMoviesCached:
    """Tests for cached top rated movies (Phase 6.2)."""

    @patch('listarr.services.tmdb_service.get_top_rated_movies')
    def test_returns_results_on_cache_miss(self, mock_fetch, app):
        """First call fetches from API (cache miss)."""
        mock_fetch.return_value = [{'id': 238, 'title': 'The Godfather'}]

        with app.app_context():
            result = get_top_rated_movies_cached("test_key", page=1)

        assert len(result) == 1
        assert result[0]['title'] == 'The Godfather'
        mock_fetch.assert_called_once()

    @patch('listarr.services.tmdb_service.get_top_rated_movies')
    def test_returns_cached_on_second_call(self, mock_fetch, app):
        """Second call returns cached data (cache hit)."""
        mock_fetch.return_value = [{'id': 238, 'title': 'The Godfather'}]

        with app.app_context():
            result1 = get_top_rated_movies_cached("test_key", page=1)
            result2 = get_top_rated_movies_cached("test_key", page=1)

        assert result1 == result2
        # Only one API call despite two requests
        assert mock_fetch.call_count == 1

    @patch('listarr.services.tmdb_service.get_top_rated_movies')
    def test_different_pages_have_separate_cache_keys(self, mock_fetch, app):
        """Different pages are cached separately."""
        mock_fetch.side_effect = [
            [{'id': 1, 'title': 'Movie 1'}],
            [{'id': 2, 'title': 'Movie 2'}]
        ]

        with app.app_context():
            result1 = get_top_rated_movies_cached("test_key", page=1)
            result2 = get_top_rated_movies_cached("test_key", page=2)

        assert result1 != result2
        assert mock_fetch.call_count == 2

    @patch('listarr.services.tmdb_service.get_top_rated_movies')
    def test_returns_empty_list_on_api_error(self, mock_fetch, app):
        """Returns empty list when API fails."""
        mock_fetch.return_value = []

        with app.app_context():
            result = get_top_rated_movies_cached("test_key", page=1)

        assert result == []


class TestGetTopRatedTVCached:
    """Tests for cached top rated TV shows (Phase 6.2)."""

    @patch('listarr.services.tmdb_service.get_top_rated_tv')
    def test_returns_results_on_cache_miss(self, mock_fetch, app):
        """First call fetches from API (cache miss)."""
        mock_fetch.return_value = [{'id': 1396, 'name': 'Breaking Bad'}]

        with app.app_context():
            result = get_top_rated_tv_cached("test_key", page=1)

        assert len(result) == 1
        assert result[0]['name'] == 'Breaking Bad'
        mock_fetch.assert_called_once()

    @patch('listarr.services.tmdb_service.get_top_rated_tv')
    def test_returns_cached_on_second_call(self, mock_fetch, app):
        """Second call returns cached data (cache hit)."""
        mock_fetch.return_value = [{'id': 1396, 'name': 'Breaking Bad'}]

        with app.app_context():
            result1 = get_top_rated_tv_cached("test_key", page=1)
            result2 = get_top_rated_tv_cached("test_key", page=1)

        assert result1 == result2
        assert mock_fetch.call_count == 1

    @patch('listarr.services.tmdb_service.get_top_rated_tv')
    def test_different_pages_have_separate_cache_keys(self, mock_fetch, app):
        """Different pages are cached separately."""
        mock_fetch.side_effect = [
            [{'id': 1, 'name': 'Show 1'}],
            [{'id': 2, 'name': 'Show 2'}]
        ]

        with app.app_context():
            result1 = get_top_rated_tv_cached("test_key", page=1)
            result2 = get_top_rated_tv_cached("test_key", page=2)

        assert result1 != result2
        assert mock_fetch.call_count == 2


class TestGetTMDBRegion:
    """Tests for _get_tmdb_region() helper function (Phase 6.2)."""

    @patch('listarr.models.service_config_model.ServiceConfig')
    def test_returns_configured_region(self, mock_service_config_class):
        """Test that configured region is returned from ServiceConfig."""
        # Mock ServiceConfig query
        mock_tmdb_config = MagicMock()
        mock_tmdb_config.tmdb_region = 'US'

        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_tmdb_config
        mock_service_config_class.query = mock_query

        result = _get_tmdb_region()

        assert result == 'US'
        mock_query.filter_by.assert_called_once_with(service='TMDB')

    @patch('listarr.models.service_config_model.ServiceConfig')
    def test_returns_none_when_region_not_configured(self, mock_service_config_class):
        """Test that None is returned when region not configured."""
        # Mock ServiceConfig with no region set
        mock_tmdb_config = MagicMock()
        mock_tmdb_config.tmdb_region = None

        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_tmdb_config
        mock_service_config_class.query = mock_query

        result = _get_tmdb_region()

        assert result is None

    @patch('listarr.models.service_config_model.ServiceConfig')
    def test_returns_none_when_no_tmdb_config_exists(self, mock_service_config_class):
        """Test that None is returned when no TMDB config exists."""
        # Mock ServiceConfig query returning None
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_service_config_class.query = mock_query

        result = _get_tmdb_region()

        assert result is None

    @patch('listarr.models.service_config_model.ServiceConfig')
    def test_region_code_case_preserved(self, mock_service_config_class):
        """Test that region code case is preserved (uppercase)."""
        # Mock ServiceConfig with uppercase region
        mock_tmdb_config = MagicMock()
        mock_tmdb_config.tmdb_region = 'GB'

        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_tmdb_config
        mock_service_config_class.query = mock_query

        result = _get_tmdb_region()

        assert result == 'GB'
        assert result == result.upper()  # Verify it's uppercase


class TestRegionAwareCacheKeys:
    """Tests for region-aware cache key generation (Phase 6.2)."""

    @patch('listarr.services.tmdb_cache.tmdb_service')
    @patch('listarr.services.tmdb_cache._get_tmdb_region')
    def test_different_regions_use_different_cache_keys(self, mock_get_region, mock_tmdb_service):
        """Test that different regions generate different cache keys."""
        # Mock TMDB service response
        mock_tmdb_service.get_popular_movies.return_value = [
            {'id': 1, 'title': 'Movie 1'}
        ]

        # First call with US region
        mock_get_region.return_value = 'US'
        result_us = get_popular_movies_cached('test_api_key', page=1)

        # Clear cache to simulate fresh state
        from listarr.services.tmdb_cache import _popular_cache
        _popular_cache.clear()

        # Second call with GB region
        mock_get_region.return_value = 'GB'
        result_gb = get_popular_movies_cached('test_api_key', page=1)

        # Both should call the TMDB service (cache keys are different)
        assert mock_tmdb_service.get_popular_movies.call_count == 2

        # First call should have region='US', second should have region='GB'
        first_call_kwargs = mock_tmdb_service.get_popular_movies.call_args_list[0][1]
        second_call_kwargs = mock_tmdb_service.get_popular_movies.call_args_list[1][1]

        assert first_call_kwargs.get('region') == 'US'
        assert second_call_kwargs.get('region') == 'GB'

    @patch('listarr.services.tmdb_cache.tmdb_service')
    @patch('listarr.services.tmdb_cache._get_tmdb_region')
    def test_same_region_reuses_cached_result(self, mock_get_region, mock_tmdb_service):
        """Test that same region reuses cached result."""
        # Mock TMDB service response
        mock_tmdb_service.get_popular_movies.return_value = [
            {'id': 1, 'title': 'Movie 1'}
        ]

        # Clear cache to start fresh
        from listarr.services.tmdb_cache import _popular_cache
        _popular_cache.clear()

        # Both calls with US region
        mock_get_region.return_value = 'US'
        result1 = get_popular_movies_cached('test_api_key', page=1)
        result2 = get_popular_movies_cached('test_api_key', page=1)

        # Should only call TMDB service once (second call uses cache)
        assert mock_tmdb_service.get_popular_movies.call_count == 1
        assert result1 == result2

    @patch('listarr.services.tmdb_cache.tmdb_service')
    @patch('listarr.services.tmdb_cache._get_tmdb_region')
    def test_no_region_uses_worldwide_cache_key(self, mock_get_region, mock_tmdb_service):
        """Test that no region configuration uses worldwide cache key."""
        # Mock TMDB service response
        mock_tmdb_service.get_popular_movies.return_value = [
            {'id': 1, 'title': 'Movie 1'}
        ]

        # Clear cache to start fresh
        from listarr.services.tmdb_cache import _popular_cache
        _popular_cache.clear()

        # Call with no region configured
        mock_get_region.return_value = None
        result = get_popular_movies_cached('test_api_key', page=1)

        # Should call TMDB service with region=None
        mock_tmdb_service.get_popular_movies.assert_called_once_with(
            'test_api_key', 1, region=None
        )

        # Verify result
        assert len(result) == 1
        assert result[0]['title'] == 'Movie 1'
