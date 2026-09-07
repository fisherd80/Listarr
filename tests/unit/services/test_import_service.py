"""
Unit tests for listarr.services.import_service._fetch_tmdb_items top-rated branches.

Phase 7 coverage gap closure targets the top_rated_movies and top_rated_tv
branches without making real TMDB calls.
"""

import logging
from unittest.mock import patch

import pytest

from listarr.models.lists_model import List
from listarr.models.service_config_model import MediaImportSettings
from listarr.services import import_service
from listarr.services.import_service import resolve_import_settings


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


MONITOR_MODES = ["all", "firstSeason", "lastSeason", "pilot", "none"]

_IMPORT_LOGGER = "listarr.services.import_service"


def _resolver_list(**overrides):
    """Plain, unsaved List. Defaults resolve monitored / search_on_add to True so the
    monitor_mode precedence assertions are isolated from D-06 reconciliation."""
    base = dict(
        name="Resolver Test",
        target_service="SONARR",
        tmdb_list_type="popular_tv",
        filters_json={},
        limit=25,
        is_active=True,
        override_monitored=1,
        override_search_on_add=1,
    )
    base.update(overrides)
    return List(**base)


def _resolver_settings(**overrides):
    """Plain, unsaved MediaImportSettings. The ORM ``default="all"`` only fires on
    flush, so ``sonarr_monitor_mode`` is None here unless explicitly set."""
    base = dict(
        service="SONARR",
        root_folder="/tv",
        quality_profile_id=1,
        monitored=True,
        search_on_add=True,
        season_folder=True,
    )
    base.update(overrides)
    return MediaImportSettings(**base)


class TestResolveImportSettings:
    """Phase 13-02: precedence matrix, D-06 reconciliation and the emit-time allow-list."""

    # --- Precedence matrix: 5 tokens x 3 sources (D-02, MON-02, MON-06) ---

    @pytest.mark.parametrize("source", ["list_override", "import_default", "hard_default"])
    @pytest.mark.parametrize("mode", MONITOR_MODES)
    def test_monitor_mode_precedence(self, source, mode):
        if source == "list_override":
            list_obj = _resolver_list(sonarr_monitor_mode=mode)
            other = "all" if mode != "all" else "pilot"
            import_settings = _resolver_settings(sonarr_monitor_mode=other)
            expected = mode
        elif source == "import_default":
            list_obj = _resolver_list(sonarr_monitor_mode=None)
            import_settings = _resolver_settings(sonarr_monitor_mode=mode)
            expected = mode
        else:  # hard_default: neither source set -> "all" regardless of the parametrised token
            list_obj = _resolver_list(sonarr_monitor_mode=None)
            import_settings = _resolver_settings(sonarr_monitor_mode=None)
            expected = "all"

        result = resolve_import_settings(list_obj, import_settings)

        assert result["monitor_mode"] == expected

    def test_monitor_mode_pre_upgrade_list_with_no_import_settings_resolves_all(self):
        # MON-02: a list and an environment that both predate the phase -> "all".
        result = resolve_import_settings(_resolver_list(sonarr_monitor_mode=None), None)

        assert result["monitor_mode"] == "all"

    def test_monitor_mode_blank_import_default_falls_through_to_all(self):
        # RESEARCH A3: an empty-string import-default row (migrated without DEFAULT 'all')
        # is falsy, so the elif falls through to the hard default.
        result = resolve_import_settings(
            _resolver_list(sonarr_monitor_mode=None),
            _resolver_settings(sonarr_monitor_mode=""),
        )

        assert result["monitor_mode"] == "all"

    # --- D-06 reconciliation (T-13-07): ordering is load-bearing ---

    def test_reconcile_monitored_false_forces_none_and_no_search(self):
        list_obj = _resolver_list(sonarr_monitor_mode="lastSeason", override_monitored=0, override_search_on_add=1)

        result = resolve_import_settings(list_obj, _resolver_settings())

        assert result["monitored"] is False
        assert result["monitor_mode"] == "none"
        assert result["search_on_add"] is False

    def test_reconcile_monitored_true_preserves_resolved_mode(self):
        # Negative case for rule 1.
        list_obj = _resolver_list(sonarr_monitor_mode="lastSeason", override_monitored=1, override_search_on_add=1)

        result = resolve_import_settings(list_obj, _resolver_settings())

        assert result["monitor_mode"] == "lastSeason"
        assert result["search_on_add"] is True

    def test_reconcile_mode_none_forces_no_search(self):
        list_obj = _resolver_list(sonarr_monitor_mode="none", override_monitored=1, override_search_on_add=1)

        result = resolve_import_settings(list_obj, _resolver_settings())

        assert result["monitor_mode"] == "none"
        assert result["search_on_add"] is False

    def test_reconcile_other_modes_preserve_independent_search(self):
        # Rule 3 positive: mode resolved independently, search honoured as resolved.
        list_obj = _resolver_list(sonarr_monitor_mode="lastSeason", override_monitored=1, override_search_on_add=1)

        result = resolve_import_settings(list_obj, _resolver_settings())

        assert result["monitor_mode"] == "lastSeason"
        assert result["search_on_add"] is True

    def test_reconcile_other_modes_keep_search_off_when_resolved_off(self):
        # Rule 3 negative: search stays off, mode still independently resolved.
        list_obj = _resolver_list(sonarr_monitor_mode="lastSeason", override_monitored=1, override_search_on_add=0)

        result = resolve_import_settings(list_obj, _resolver_settings())

        assert result["monitor_mode"] == "lastSeason"
        assert result["search_on_add"] is False

    # --- D-08 search contract ---

    def test_search_on_add_forced_false_for_none_mode(self):
        list_obj = _resolver_list(sonarr_monitor_mode="none", override_search_on_add=1)

        assert resolve_import_settings(list_obj, _resolver_settings())["search_on_add"] is False

    @pytest.mark.parametrize("mode", ["all", "firstSeason", "lastSeason", "pilot"])
    def test_search_on_add_survives_for_non_none_modes(self, mode):
        list_obj = _resolver_list(sonarr_monitor_mode=mode, override_search_on_add=1)

        assert resolve_import_settings(list_obj, _resolver_settings())["search_on_add"] is True

    # --- Allow-list / emit-time guard (security V5, T-13-05) ---

    def test_invalid_monitor_mode_injection_string_coerced_to_all(self, caplog):
        list_obj = _resolver_list(sonarr_monitor_mode="'; DROP TABLE lists; --")

        with caplog.at_level(logging.WARNING, logger=_IMPORT_LOGGER):
            result = resolve_import_settings(list_obj, _resolver_settings())

        assert result["monitor_mode"] == "all"
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_obsolete_latestseason_token_coerced_to_all(self, caplog):
        import_settings = _resolver_settings(sonarr_monitor_mode="latestSeason")

        with caplog.at_level(logging.WARNING, logger=_IMPORT_LOGGER):
            result = resolve_import_settings(_resolver_list(sonarr_monitor_mode=None), import_settings)

        assert result["monitor_mode"] == "all"
        assert any("latestSeason" in r.getMessage() for r in caplog.records)

    # --- Non-regression ---

    def test_returned_key_set_is_exact(self):
        result = resolve_import_settings(_resolver_list(sonarr_monitor_mode="all"), _resolver_settings())

        assert set(result) == {
            "root_folder",
            "quality_profile_id",
            "monitored",
            "search_on_add",
            "season_folder",
            "monitor_mode",
            "tags",
        }

    def test_radarr_shaped_list_other_resolved_values_unchanged(self):
        list_obj = _resolver_list(
            target_service="RADARR",
            sonarr_monitor_mode=None,
            override_root_folder="/movies",
            override_quality_profile=3,
            override_monitored=1,
            override_search_on_add=1,
            override_season_folder=1,
        )
        import_settings = _resolver_settings(service="RADARR", root_folder="/def", quality_profile_id=9)

        result = resolve_import_settings(list_obj, import_settings)

        assert result["root_folder"] == "/movies"
        assert result["quality_profile_id"] == 3
        assert result["monitored"] is True
        assert result["search_on_add"] is True
        assert result["season_folder"] is True
        assert result["tags"] == []
        assert result["monitor_mode"] == "all"
