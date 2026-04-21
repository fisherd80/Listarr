"""
Unit tests for listarr.services.import_service._fetch_tmdb_items top-rated branches.

Phase 7 coverage gap closure targets the top_rated_movies and top_rated_tv
branches without making real TMDB calls.
"""

from unittest.mock import patch

from listarr.models.lists_model import List
from listarr.services import import_service


def _make_import_list(tmdb_list_type, limit=25):
    return List(
        name="Import Coverage",
        target_service="RADARR",
        tmdb_list_type=tmdb_list_type,
        filters_json={},
        limit=limit,
        is_active=True,
    )


class TestFetchTmdbItems:
    """TEST-03 and TEST-04 coverage for _fetch_tmdb_items top-rated branches."""

    @patch("listarr.services.import_service.get_top_rated_movies_cached")
    def test_fetch_top_rated_movies_calls_cache(self, mock_cache):
        mock_cache.return_value = [{"id": i, "title": f"Movie {i}"} for i in range(1, 26)]
        list_obj = _make_import_list("top_rated_movies", limit=25)

        items = import_service._fetch_tmdb_items(list_obj, "tmdb-key")

        assert len(items) == 25
        mock_cache.assert_any_call("tmdb-key", page=1)

    @patch("listarr.services.import_service.get_top_rated_movies_cached")
    def test_fetch_top_rated_movies_respects_limit(self, mock_cache):
        mock_cache.return_value = [{"id": i, "title": f"Movie {i}"} for i in range(1, 21)]
        list_obj = _make_import_list("top_rated_movies", limit=10)

        items = import_service._fetch_tmdb_items(list_obj, "tmdb-key")

        assert len(items) == 10

    @patch("listarr.services.import_service.get_top_rated_tv_cached")
    def test_fetch_top_rated_tv_calls_cache(self, mock_cache):
        mock_cache.return_value = [{"id": i, "name": f"Show {i}"} for i in range(1, 26)]
        list_obj = _make_import_list("top_rated_tv", limit=25)

        items = import_service._fetch_tmdb_items(list_obj, "tmdb-key")

        assert len(items) == 25
        mock_cache.assert_any_call("tmdb-key", page=1)

    @patch("listarr.services.import_service.get_top_rated_tv_cached")
    def test_fetch_top_rated_tv_respects_limit(self, mock_cache):
        mock_cache.return_value = [{"id": i, "name": f"Show {i}"} for i in range(1, 21)]
        list_obj = _make_import_list("top_rated_tv", limit=10)

        items = import_service._fetch_tmdb_items(list_obj, "tmdb-key")

        assert len(items) == 10

    @patch("listarr.services.import_service.get_top_rated_movies_cached")
    def test_fetch_top_rated_movies_fetches_multiple_pages_for_large_limit(self, mock_cache):
        mock_cache.side_effect = [
            [{"id": i, "title": f"Movie {i}"} for i in range(1, 21)],
            [{"id": i, "title": f"Movie {i}"} for i in range(21, 41)],
        ]
        list_obj = _make_import_list("top_rated_movies", limit=35)

        items = import_service._fetch_tmdb_items(list_obj, "tmdb-key")

        assert len(items) == 35
        mock_cache.assert_any_call("tmdb-key", page=1)
        mock_cache.assert_any_call("tmdb-key", page=2)
