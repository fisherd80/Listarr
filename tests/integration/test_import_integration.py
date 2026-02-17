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
from requests.exceptions import RequestException

from listarr.models.lists_model import List
from listarr.services.import_service import BATCH_SIZE, _fetch_tmdb_items, _import_movies


class TestFetchTMDBItemsTopRated:
    """Integration tests for top_rated list type handling in import service (Phase 6.2)."""

    @patch("listarr.services.import_service.get_top_rated_movies_cached")
    def test_fetches_top_rated_movies_using_cached_function(self, mock_cached, app):
        """Test that top_rated_movies list type uses cached function."""
        mock_cached.return_value = [
            {"id": 238, "title": "The Godfather"},
            {"id": 278, "title": "The Shawshank Redemption"},
        ]

        with app.app_context():
            # Create mock list object
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = "top_rated_movies"
            list_obj.target_service = "RADARR"
            list_obj.filters_json = {}
            list_obj.limit = 20

            result = _fetch_tmdb_items(list_obj, "test_api_key")

            # Verify cached function was called
            mock_cached.assert_called_once_with("test_api_key", page=1)
            assert len(result) == 2
            assert result[0]["title"] == "The Godfather"

    @patch("listarr.services.import_service.get_top_rated_tv_cached")
    def test_fetches_top_rated_tv_using_cached_function(self, mock_cached, app):
        """Test that top_rated_tv list type uses cached function."""
        mock_cached.return_value = [
            {"id": 1396, "name": "Breaking Bad"},
            {"id": 1399, "name": "Game of Thrones"},
        ]

        with app.app_context():
            # Create mock list object
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = "top_rated_tv"
            list_obj.target_service = "SONARR"
            list_obj.filters_json = {}
            list_obj.limit = 20

            result = _fetch_tmdb_items(list_obj, "test_api_key")

            # Verify cached function was called
            mock_cached.assert_called_once_with("test_api_key", page=1)
            assert len(result) == 2
            assert result[0]["name"] == "Breaking Bad"

    @patch("listarr.services.import_service.get_top_rated_movies_cached")
    def test_limit_parameter_controls_item_count(self, mock_cached, app):
        """Test that limit parameter controls number of items fetched."""
        # Mock first page returns 20 items
        page1_items = [{"id": i, "title": f"Movie {i}"} for i in range(1, 21)]
        # Mock second page returns 20 items
        page2_items = [{"id": i, "title": f"Movie {i}"} for i in range(21, 41)]
        # Mock third page returns 20 items
        page3_items = [{"id": i, "title": f"Movie {i}"} for i in range(41, 61)]

        mock_cached.side_effect = [page1_items, page2_items, page3_items]

        with app.app_context():
            # Create mock list object with limit=50
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = "top_rated_movies"
            list_obj.target_service = "RADARR"
            list_obj.filters_json = {}
            list_obj.limit = 50

            result = _fetch_tmdb_items(list_obj, "test_api_key")

            # Should fetch 3 pages (20 + 20 + 10 = 50)
            assert mock_cached.call_count == 3
            # Should return exactly 50 items (sliced to limit)
            assert len(result) == 50
            assert result[0]["id"] == 1
            assert result[49]["id"] == 50

    @patch("listarr.services.import_service.get_top_rated_movies_cached")
    def test_handles_empty_response_gracefully(self, mock_cached, app):
        """Test that empty TMDB response is handled gracefully."""
        mock_cached.return_value = []

        with app.app_context():
            # Create mock list object
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = "top_rated_movies"
            list_obj.target_service = "RADARR"
            list_obj.filters_json = {}
            list_obj.limit = 20

            result = _fetch_tmdb_items(list_obj, "test_api_key")

            # Should return empty list without error
            assert result == []
            mock_cached.assert_called_once_with("test_api_key", page=1)

    @patch("listarr.services.import_service.get_top_rated_tv_cached")
    def test_handles_api_errors_gracefully(self, mock_cached, app):
        """Test that API errors are handled gracefully."""
        # Mock API error (cached function returns empty list on error)
        mock_cached.return_value = []

        with app.app_context():
            # Create mock list object
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = "top_rated_tv"
            list_obj.target_service = "SONARR"
            list_obj.filters_json = {}
            list_obj.limit = 20

            result = _fetch_tmdb_items(list_obj, "test_api_key")

            # Should return empty list without raising exception
            assert result == []


class TestFetchTMDBItemsLimitBehavior:
    """Additional tests for multi-page fetching behavior."""

    @patch("listarr.services.import_service.get_top_rated_movies_cached")
    def test_stops_fetching_when_page_returns_less_than_20(self, mock_cached, app):
        """Test that fetching stops when page returns fewer than 20 items."""
        # Page 1: 20 items
        page1_items = [{"id": i, "title": f"Movie {i}"} for i in range(1, 21)]
        # Page 2: Only 15 items (end of available content)
        page2_items = [{"id": i, "title": f"Movie {i}"} for i in range(21, 36)]

        mock_cached.side_effect = [page1_items, page2_items]

        with app.app_context():
            # Request limit=100, but API only has 35 items
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = "top_rated_movies"
            list_obj.target_service = "RADARR"
            list_obj.filters_json = {}
            list_obj.limit = 100

            result = _fetch_tmdb_items(list_obj, "test_api_key")

            # Should only fetch 2 pages (stops when page 2 returns <20)
            assert mock_cached.call_count == 2
            # Should return all 35 items
            assert len(result) == 35

    @patch("listarr.services.import_service.get_top_rated_movies_cached")
    def test_respects_limit_across_multiple_pages(self, mock_cached, app):
        """Test that limit is respected across multiple page fetches."""
        # Each page returns 20 items
        page1_items = [{"id": i, "title": f"Movie {i}"} for i in range(1, 21)]
        page2_items = [{"id": i, "title": f"Movie {i}"} for i in range(21, 41)]
        page3_items = [{"id": i, "title": f"Movie {i}"} for i in range(41, 61)]
        page4_items = [{"id": i, "title": f"Movie {i}"} for i in range(61, 81)]

        mock_cached.side_effect = [page1_items, page2_items, page3_items, page4_items]

        with app.app_context():
            # Request exactly 65 items
            list_obj = MagicMock(spec=List)
            list_obj.tmdb_list_type = "top_rated_movies"
            list_obj.target_service = "RADARR"
            list_obj.filters_json = {}
            list_obj.limit = 65

            result = _fetch_tmdb_items(list_obj, "test_api_key")

            # Should fetch 4 pages (20+20+20+5=65)
            assert mock_cached.call_count == 4
            # Should return exactly 65 items
            assert len(result) == 65
            assert result[0]["id"] == 1
            assert result[64]["id"] == 65


class TestImportExclusionList:
    """Tests for exclusion list validation during import."""

    @patch("listarr.services.import_service.radarr_service")
    def test_import_movies_skips_excluded_items(self, mock_radarr, app):
        """Test that movies on Radarr exclusion list are skipped."""
        mock_radarr.get_existing_movie_tmdb_ids.return_value = set()
        mock_radarr.get_exclusions.return_value = {278}  # Shawshank excluded

        with app.app_context():
            items = [{"id": 278, "title": "The Shawshank Redemption"}]
            settings = {
                "root_folder": "/movies",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "tags": [],
            }

            result = _import_movies(items, "http://radarr", "key", settings, "tmdb_key")

            assert len(result.skipped) == 1
            assert result.skipped[0]["reason"] == "on_exclusion_list"
            assert result.skipped[0]["tmdb_id"] == 278
            mock_radarr.add_movie.assert_not_called()


class TestBatchImportMovies:
    """Integration tests for batch-based movie import flow."""

    @patch("listarr.services.import_service.time")
    @patch("listarr.services.import_service.radarr_service")
    def test_batch_import_movies_uses_bulk_endpoint(self, mock_radarr, mock_time, app):
        """Test that batch import uses bulk_add_movies endpoint instead of single adds."""
        # Mock pre-flight checks
        mock_radarr.get_existing_movie_tmdb_ids.return_value = set()
        mock_radarr.get_exclusions.return_value = set()

        # Mock lookup for 3 movies
        def mock_lookup(base_url, api_key, tmdb_id):
            return {
                "tmdbId": tmdb_id,
                "title": f"Movie {tmdb_id}",
                "titleSlug": f"movie-{tmdb_id}",
                "year": 2020,
                "images": [],
            }

        mock_radarr.lookup_movie.side_effect = mock_lookup

        # Mock bulk_add_movies to return list of added items
        mock_radarr.bulk_add_movies.return_value = [
            {"tmdbId": 1, "title": "Movie 1"},
            {"tmdbId": 2, "title": "Movie 2"},
            {"tmdbId": 3, "title": "Movie 3"},
        ]

        with app.app_context():
            items = [
                {"id": 1, "title": "Movie 1"},
                {"id": 2, "title": "Movie 2"},
                {"id": 3, "title": "Movie 3"},
            ]
            settings = {
                "root_folder": "/movies",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "tags": [],
            }

            result = _import_movies(items, "http://radarr", "key", settings, "tmdb_key")

            # Verify bulk endpoint was called once (single batch)
            mock_radarr.bulk_add_movies.assert_called_once()
            # Verify add_movie was NOT called (no single-item adds)
            mock_radarr.add_movie.assert_not_called()
            # Verify all 3 items added
            assert len(result.added) == 3

    @patch("listarr.services.import_service.time")
    @patch("listarr.services.import_service.radarr_service")
    def test_batch_import_skips_existing_before_lookup(self, mock_radarr, mock_time, app):
        """Test that existing movies are skipped before lookup (pre-flight check)."""
        # Mock existing IDs
        mock_radarr.get_existing_movie_tmdb_ids.return_value = {1, 3}
        mock_radarr.get_exclusions.return_value = set()

        # Mock lookup for remaining items
        def mock_lookup(base_url, api_key, tmdb_id):
            return {
                "tmdbId": tmdb_id,
                "title": f"Movie {tmdb_id}",
                "titleSlug": f"movie-{tmdb_id}",
                "year": 2020,
                "images": [],
            }

        mock_radarr.lookup_movie.side_effect = mock_lookup
        mock_radarr.bulk_add_movies.return_value = [
            {"tmdbId": 2, "title": "Movie 2"},
            {"tmdbId": 4, "title": "Movie 4"},
            {"tmdbId": 5, "title": "Movie 5"},
        ]

        with app.app_context():
            items = [
                {"id": 1, "title": "Movie 1"},
                {"id": 2, "title": "Movie 2"},
                {"id": 3, "title": "Movie 3"},
                {"id": 4, "title": "Movie 4"},
                {"id": 5, "title": "Movie 5"},
            ]
            settings = {
                "root_folder": "/movies",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "tags": [],
            }

            result = _import_movies(items, "http://radarr", "key", settings, "tmdb_key")

            # Verify lookup only called 3 times (not 5)
            assert mock_radarr.lookup_movie.call_count == 3
            # Verify 2 items skipped with correct reason
            assert len(result.skipped) == 2
            assert all(item["reason"] == "already_exists" for item in result.skipped)
            assert {item["tmdb_id"] for item in result.skipped} == {1, 3}
            # Verify 3 items added
            assert len(result.added) == 3

    @patch("listarr.services.import_service.time")
    @patch("listarr.services.import_service.radarr_service")
    def test_batch_import_skips_excluded_before_lookup(self, mock_radarr, mock_time, app):
        """Test that excluded movies are skipped before lookup (pre-flight check)."""
        # Mock excluded IDs
        mock_radarr.get_existing_movie_tmdb_ids.return_value = set()
        mock_radarr.get_exclusions.return_value = {2}

        # Mock lookup for remaining items
        def mock_lookup(base_url, api_key, tmdb_id):
            return {
                "tmdbId": tmdb_id,
                "title": f"Movie {tmdb_id}",
                "titleSlug": f"movie-{tmdb_id}",
                "year": 2020,
                "images": [],
            }

        mock_radarr.lookup_movie.side_effect = mock_lookup
        mock_radarr.bulk_add_movies.return_value = [
            {"tmdbId": 1, "title": "Movie 1"},
            {"tmdbId": 3, "title": "Movie 3"},
        ]

        with app.app_context():
            items = [
                {"id": 1, "title": "Movie 1"},
                {"id": 2, "title": "Movie 2"},
                {"id": 3, "title": "Movie 3"},
            ]
            settings = {
                "root_folder": "/movies",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "tags": [],
            }

            result = _import_movies(items, "http://radarr", "key", settings, "tmdb_key")

            # Verify lookup only called 2 times (not 3)
            assert mock_radarr.lookup_movie.call_count == 2
            # Verify 1 item skipped with correct reason
            assert len(result.skipped) == 1
            assert result.skipped[0]["reason"] == "on_exclusion_list"
            assert result.skipped[0]["tmdb_id"] == 2
            # Verify 2 items added
            assert len(result.added) == 2

    @patch("listarr.services.import_service.time")
    @patch("listarr.services.import_service.radarr_service")
    def test_batch_import_handles_lookup_failure(self, mock_radarr, mock_time, app):
        """Test that lookup failures are tracked as failed items."""
        # Mock pre-flight checks
        mock_radarr.get_existing_movie_tmdb_ids.return_value = set()
        mock_radarr.get_exclusions.return_value = set()

        # Mock lookup: item 2 fails (returns None)
        def mock_lookup(base_url, api_key, tmdb_id):
            if tmdb_id == 2:
                return None
            return {
                "tmdbId": tmdb_id,
                "title": f"Movie {tmdb_id}",
                "titleSlug": f"movie-{tmdb_id}",
                "year": 2020,
                "images": [],
            }

        mock_radarr.lookup_movie.side_effect = mock_lookup
        mock_radarr.bulk_add_movies.return_value = [
            {"tmdbId": 1, "title": "Movie 1"},
            {"tmdbId": 3, "title": "Movie 3"},
        ]

        with app.app_context():
            items = [
                {"id": 1, "title": "Movie 1"},
                {"id": 2, "title": "Movie 2"},
                {"id": 3, "title": "Movie 3"},
            ]
            settings = {
                "root_folder": "/movies",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "tags": [],
            }

            result = _import_movies(items, "http://radarr", "key", settings, "tmdb_key")

            # Verify 1 item failed with correct reason
            assert len(result.failed) == 1
            assert result.failed[0]["reason"] == "not_found_in_radarr"
            assert result.failed[0]["tmdb_id"] == 2
            # Verify bulk_add called with 2-item batch
            assert mock_radarr.bulk_add_movies.call_count == 1
            call_args = mock_radarr.bulk_add_movies.call_args
            assert len(call_args[0][2]) == 2  # 2 payloads
            # Verify 2 items added
            assert len(result.added) == 2

    @patch("listarr.services.import_service.time")
    @patch("listarr.services.import_service.radarr_service")
    def test_batch_import_flushes_at_batch_size(self, mock_radarr, mock_time, app):
        """Test that batches are flushed at BATCH_SIZE intervals."""
        # Mock pre-flight checks
        mock_radarr.get_existing_movie_tmdb_ids.return_value = set()
        mock_radarr.get_exclusions.return_value = set()

        # Generate BATCH_SIZE + 10 items (e.g., 60 items if BATCH_SIZE=50)
        num_items = BATCH_SIZE + 10

        # Mock lookup for all items
        def mock_lookup(base_url, api_key, tmdb_id):
            return {
                "tmdbId": tmdb_id,
                "title": f"Movie {tmdb_id}",
                "titleSlug": f"movie-{tmdb_id}",
                "year": 2020,
                "images": [],
            }

        mock_radarr.lookup_movie.side_effect = mock_lookup

        # Mock bulk_add_movies to return matching items for each batch
        def mock_bulk_add(base_url, api_key, payloads):
            return [{"tmdbId": p["tmdbId"], "title": p["title"]} for p in payloads]

        mock_radarr.bulk_add_movies.side_effect = mock_bulk_add

        with app.app_context():
            items = [{"id": i, "title": f"Movie {i}"} for i in range(1, num_items + 1)]
            settings = {
                "root_folder": "/movies",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "tags": [],
            }

            result = _import_movies(items, "http://radarr", "key", settings, "tmdb_key")

            # Verify bulk_add_movies called exactly 2 times (BATCH_SIZE + 10)
            assert mock_radarr.bulk_add_movies.call_count == 2
            # Verify total added equals num_items
            assert len(result.added) == num_items

    @patch("listarr.services.import_service.time")
    @patch("listarr.services.import_service.radarr_service")
    def test_batch_import_handles_bulk_failure(self, mock_radarr, mock_time, app):
        """Test that bulk import failures are tracked correctly."""
        # Mock pre-flight checks
        mock_radarr.get_existing_movie_tmdb_ids.return_value = set()
        mock_radarr.get_exclusions.return_value = set()

        # Mock lookup for 3 movies
        def mock_lookup(base_url, api_key, tmdb_id):
            return {
                "tmdbId": tmdb_id,
                "title": f"Movie {tmdb_id}",
                "titleSlug": f"movie-{tmdb_id}",
                "year": 2020,
                "images": [],
            }

        mock_radarr.lookup_movie.side_effect = mock_lookup

        # Mock bulk_add_movies to raise exception
        mock_radarr.bulk_add_movies.side_effect = RequestException("Bulk import failed: API error")

        with app.app_context():
            items = [
                {"id": 1, "title": "Movie 1"},
                {"id": 2, "title": "Movie 2"},
                {"id": 3, "title": "Movie 3"},
            ]
            settings = {
                "root_folder": "/movies",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "tags": [],
            }

            result = _import_movies(items, "http://radarr", "key", settings, "tmdb_key")

            # Verify all 3 items in result.failed
            assert len(result.failed) == 3
            # Verify failure reason contains exception message
            for item in result.failed:
                assert "Bulk import failed" in item["reason"]


class TestBatchImportSeries:
    """Integration tests for batch-based series import flow."""

    @patch("listarr.services.import_service.time")
    @patch("listarr.services.import_service.tmdb_service")
    @patch("listarr.services.import_service.sonarr_service")
    def test_batch_import_series_uses_bulk_endpoint(self, mock_sonarr, mock_tmdb, mock_time, app):
        """Test that batch import uses bulk_add_series endpoint instead of single adds."""
        # Mock pre-flight checks
        mock_sonarr.get_existing_series_tvdb_ids.return_value = set()
        mock_sonarr.get_exclusions.return_value = set()

        # Mock TMDB to TVDB translation
        def mock_get_tvdb(tmdb_id, api_key):
            return tmdb_id + 1000  # Simple translation

        mock_tmdb.get_tvdb_id_from_tmdb.side_effect = mock_get_tvdb

        # Mock lookup for 2 series
        def mock_lookup(base_url, api_key, tvdb_id):
            return {
                "tvdbId": tvdb_id,
                "title": f"Series {tvdb_id}",
                "titleSlug": f"series-{tvdb_id}",
                "year": 2020,
                "images": [],
                "seasons": [],
            }

        mock_sonarr.lookup_series.side_effect = mock_lookup

        # Mock bulk_add_series to return list of added items
        mock_sonarr.bulk_add_series.return_value = [
            {"tvdbId": 1001, "title": "Series 1001"},
            {"tvdbId": 1002, "title": "Series 1002"},
        ]

        with app.app_context():
            items = [
                {"id": 1, "name": "Series 1"},
                {"id": 2, "name": "Series 2"},
            ]
            settings = {
                "root_folder": "/tv",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "season_folder": True,
                "tags": [],
            }

            from listarr.services.import_service import _import_series

            result = _import_series(items, "http://sonarr", "key", settings, "tmdb_key")

            # Verify bulk endpoint was called
            mock_sonarr.bulk_add_series.assert_called_once()
            # Verify add_series was NOT called (no single-item adds)
            mock_sonarr.add_series.assert_not_called()
            # Verify all 2 items added
            assert len(result.added) == 2

    @patch("listarr.services.import_service.time")
    @patch("listarr.services.import_service.tmdb_service")
    @patch("listarr.services.import_service.sonarr_service")
    def test_batch_import_series_translates_tmdb_to_tvdb(self, mock_sonarr, mock_tmdb, mock_time, app):
        """Test that TMDB IDs are correctly translated to TVDB IDs."""
        # Mock pre-flight checks
        mock_sonarr.get_existing_series_tvdb_ids.return_value = set()
        mock_sonarr.get_exclusions.return_value = set()

        # Mock TMDB to TVDB translation
        tvdb_mapping = {1: 1001, 2: 1002}
        mock_tmdb.get_tvdb_id_from_tmdb.side_effect = lambda tmdb_id, api_key: tvdb_mapping.get(tmdb_id)

        # Mock lookup for series (expect TVDB IDs, not TMDB IDs)
        lookup_calls = []

        def mock_lookup(base_url, api_key, tvdb_id):
            lookup_calls.append(tvdb_id)
            return {
                "tvdbId": tvdb_id,
                "title": f"Series {tvdb_id}",
                "titleSlug": f"series-{tvdb_id}",
                "year": 2020,
                "images": [],
                "seasons": [],
            }

        mock_sonarr.lookup_series.side_effect = mock_lookup
        mock_sonarr.bulk_add_series.return_value = [
            {"tvdbId": 1001, "title": "Series 1001"},
            {"tvdbId": 1002, "title": "Series 1002"},
        ]

        with app.app_context():
            items = [
                {"id": 1, "name": "Series 1"},
                {"id": 2, "name": "Series 2"},
            ]
            settings = {
                "root_folder": "/tv",
                "quality_profile_id": 1,
                "monitored": True,
                "search_on_add": True,
                "season_folder": True,
                "tags": [],
            }

            from listarr.services.import_service import _import_series

            result = _import_series(items, "http://sonarr", "key", settings, "tmdb_key")

            # Verify lookup was called with TVDB IDs (not TMDB IDs)
            assert lookup_calls == [1001, 1002]
            # Verify translation was called
            assert mock_tmdb.get_tvdb_id_from_tmdb.call_count == 2
            # Verify both items added
            assert len(result.added) == 2
