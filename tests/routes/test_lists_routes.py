"""
Route tests for lists_routes.py - All 13 list route endpoints.

Tests cover:
- GET /lists - Lists page render
- GET /api/lists - Lists JSON API
- POST /lists/create - Create list via form
- GET /lists/edit/<id> - Edit list form render
- POST /lists/edit/<id> - Update list via form
- POST /lists/delete/<id> - Delete list
- GET /lists/wizard - Wizard page (create and edit modes)
- POST /lists/toggle/<id> - Toggle list active state
- POST /lists/wizard/preview - TMDB preview
- POST /lists/wizard/submit - Wizard form submit
- GET /lists/wizard/defaults/<service> - Import defaults
- POST /lists/<id>/run - Trigger list import
- GET /lists/<id>/status - Get job status
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from listarr import db
from listarr.models.jobs_model import Job
from listarr.models.lists_model import List
from listarr.models.service_config_model import MediaImportSettings, ServiceConfig


def make_list(
    name="Test List",
    target_service="RADARR",
    tmdb_list_type="trending_movies",
    is_active=True,
    schedule_cron=None,
    last_run_at=None,
):
    """Helper to create a test list with required fields."""
    return List(
        name=name,
        target_service=target_service,
        tmdb_list_type=tmdb_list_type,
        filters_json={},
        is_active=is_active,
        schedule_cron=schedule_cron,
        last_run_at=last_run_at,
    )


def make_service_config(service, api_key_encrypted=None, base_url=None, temp_instance_path=None):
    """Helper to create a ServiceConfig. Encrypts a dummy key if no api_key_encrypted provided."""
    if api_key_encrypted is None:
        from listarr.services.crypto_utils import encrypt_data

        api_key_encrypted = encrypt_data("test_api_key", instance_path=temp_instance_path)
    return ServiceConfig(
        service=service,
        api_key_encrypted=api_key_encrypted,
        base_url=base_url or "http://localhost:7878",
    )


# ---------------------------------------------------------------------------
# 1. GET /lists - Lists page
# ---------------------------------------------------------------------------


class TestListsPage:
    """Tests for GET /lists endpoint."""

    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_renders_lists_page(self, mock_next_run, client):
        """Returns 200 and renders lists page."""
        mock_next_run.return_value = None
        response = client.get("/lists")
        assert response.status_code == 200

    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_shows_empty_state_when_no_lists(self, mock_next_run, client):
        """Renders page with no lists in DB."""
        mock_next_run.return_value = None
        response = client.get("/lists")
        assert response.status_code == 200

    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_shows_lists_when_they_exist(self, mock_next_run, client, db_session):
        """Renders page showing existing lists."""
        mock_next_run.return_value = None

        lst = make_list(name="My Trending List")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/lists")
        assert response.status_code == 200
        assert b"My Trending List" in response.data

    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_shows_next_run_for_active_scheduled_list(self, mock_next_run, client, db_session):
        """Lists with schedule_cron and is_active get next run time computed."""
        from datetime import timedelta

        future_dt = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_next_run.return_value = future_dt

        lst = make_list(name="Scheduled List", schedule_cron="0 * * * *", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.get("/lists")
        assert response.status_code == 200
        mock_next_run.assert_called()


# ---------------------------------------------------------------------------
# 2. GET /api/lists - Lists JSON API
# ---------------------------------------------------------------------------


class TestGetListsAPI:
    """Tests for GET /api/lists endpoint."""

    def test_returns_empty_list_when_no_lists(self, client):
        """Returns empty lists array when no lists exist."""
        response = client.get("/api/lists")
        assert response.status_code == 200
        data = response.get_json()
        assert "lists" in data
        assert data["lists"] == []

    def test_returns_all_lists_as_json(self, client, db_session):
        """Returns all lists with expected fields."""
        lst1 = make_list(name="Alpha List", target_service="RADARR")
        lst2 = make_list(name="Beta List", target_service="SONARR", is_active=False)
        db.session.add_all([lst1, lst2])
        db.session.commit()

        response = client.get("/api/lists")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["lists"]) == 2
        names = [item["name"] for item in data["lists"]]
        assert "Alpha List" in names
        assert "Beta List" in names

    def test_returns_lists_ordered_by_name(self, client, db_session):
        """Returns lists in alphabetical order."""
        lst_z = make_list(name="Zebra List")
        lst_a = make_list(name="Ant List")
        db.session.add_all([lst_z, lst_a])
        db.session.commit()

        response = client.get("/api/lists")
        data = response.get_json()
        names = [item["name"] for item in data["lists"]]
        assert names == sorted(names)

    def test_response_fields(self, client, db_session):
        """Each list item has required fields."""
        lst = make_list(name="Field Test")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/lists")
        data = response.get_json()
        assert len(data["lists"]) == 1
        item = data["lists"][0]
        assert "id" in item
        assert "name" in item
        assert "target_service" in item
        assert "is_active" in item


# ---------------------------------------------------------------------------
# 3. POST /lists/create - Create list via WTForm
# ---------------------------------------------------------------------------


class TestCreateList:
    """POST /lists/create is intentionally removed (security: unvalidated target_service write path).

    The route prefix /lists/create is preserved by the GET handlers that render the creation
    wizard. POST requests must return 405 Method Not Allowed.
    """

    def test_post_lists_create_returns_405_handler_removed(self, client, db_session):
        """POST /lists/create has no handler (security review: dead endpoint removed); Flask returns 405.

        Uses a delta-based DB count assertion rather than an absolute `== 0` check so this
        test remains robust if fixtures are ever changed to seed `List` rows.
        """
        count_before = List.query.count()
        response = client.post(
            "/lists/create",
            data={
                "name": "anything",
                "target_service": "RADARR",
                "tmdb_list_type": "trending_movies",
                "filters_json": "{}",
            },
        )
        assert response.status_code == 405
        assert List.query.count() == count_before

    def test_get_lists_create_still_renders(self, client):
        """Regression guard: GET /lists/create must still return 200 (wizard landing preserved)."""
        response = client.get("/lists/create")
        assert response.status_code == 200

    def test_get_lists_create_preset_still_renders(self, client):
        """Regression guard: GET /lists/create/preset must still return 200 (preset wizard preserved)."""
        response = client.get("/lists/create/preset")
        assert response.status_code == 200

    def test_get_lists_create_custom_still_renders(self, client):
        """Regression guard: GET /lists/create/custom must still return 200 (custom wizard preserved)."""
        response = client.get("/lists/create/custom")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 4 & 5. GET /lists/edit/<id> and POST /lists/edit/<id>
# ---------------------------------------------------------------------------


class TestEditListGET:
    """Tests for GET /lists/edit/<id> endpoint."""

    def test_returns_404_for_missing_list(self, client):
        """Returns 404 when list does not exist."""
        response = client.get("/lists/edit/9999")
        assert response.status_code == 404

    def test_renders_edit_form_with_list_data(self, client, db_session):
        """Renders edit form pre-populated with list data (no service config)."""
        lst = make_list(name="Editable List")
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/edit/{lst.id}")
        assert response.status_code == 200
        assert b"Editable List" in response.data

    def test_renders_edit_form_with_service_config(self, client, db_session, temp_instance_path):
        """Renders edit form and fetches service options when config exists."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)

        lst = make_list(name="List With Config")
        db.session.add(lst)
        db.session.commit()

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="radarr_key"),
            patch("listarr.services.radarr_service.get_quality_profiles", return_value=[{"id": 1, "name": "HD"}]),
            patch("listarr.services.radarr_service.get_root_folders", return_value=[{"path": "/movies"}]),
            patch("listarr.services.radarr_service.get_tags", return_value=[]),
        ):
            response = client.get(f"/lists/edit/{lst.id}")

        assert response.status_code == 200
        assert b"List With Config" in response.data


class TestEditListPOST:
    """Tests for POST /lists/edit/<id> endpoint."""

    def test_returns_404_for_missing_list(self, client):
        """Returns 404 when list does not exist."""
        form_data = {
            "name": "Updated",
            "is_active": "y",
            "schedule_cron": "",
            "override_quality_profile": "",
            "override_root_folder": "",
            "override_tag": "",
            "override_monitored": "",
            "override_search_on_add": "",
            "override_season_folder": "",
        }
        response = client.post("/lists/edit/9999", data=form_data)
        assert response.status_code == 404

    @patch("listarr.routes.lists_routes.unschedule_list")
    @patch("listarr.routes.lists_routes.schedule_list")
    def test_updates_list_successfully(self, mock_schedule, mock_unschedule, client, db_session):
        """Valid POST updates the list and redirects."""
        lst = make_list(name="Old Name")
        db.session.add(lst)
        db.session.commit()

        form_data = {
            "name": "New Name",
            "is_active": "y",
            "schedule_cron": "",
            "override_quality_profile": "",
            "override_root_folder": "",
            "override_tag": "",
            "override_monitored": "",
            "override_search_on_add": "",
            "override_season_folder": "",
        }
        response = client.post(f"/lists/edit/{lst.id}", data=form_data, follow_redirects=True)
        assert response.status_code == 200

        updated = List.query.get(lst.id)
        assert updated.name == "New Name"

    @patch("listarr.routes.lists_routes.unschedule_list")
    @patch("listarr.routes.lists_routes.schedule_list")
    def test_updates_schedule_when_cron_provided(self, mock_schedule, mock_unschedule, client, db_session):
        """When schedule_cron is provided and list is active, schedule_list is called."""
        lst = make_list(name="Schedule Test")
        db.session.add(lst)
        db.session.commit()

        form_data = {
            "name": "Schedule Test",
            "is_active": "y",
            "schedule_cron": "0 0 * * *",
            "override_quality_profile": "",
            "override_root_folder": "",
            "override_tag": "",
            "override_monitored": "",
            "override_search_on_add": "",
            "override_season_folder": "",
        }
        response = client.post(f"/lists/edit/{lst.id}", data=form_data, follow_redirects=True)
        assert response.status_code == 200
        mock_schedule.assert_called_once()

    def test_validation_error_on_missing_name(self, client, db_session):
        """Missing name shows validation error."""
        lst = make_list(name="Valid Name")
        db.session.add(lst)
        db.session.commit()

        form_data = {
            "name": "",  # Required
            "is_active": "y",
            "schedule_cron": "",
            "override_quality_profile": "",
            "override_root_folder": "",
            "override_tag": "",
            "override_monitored": "",
            "override_search_on_add": "",
            "override_season_folder": "",
        }
        response = client.post(f"/lists/edit/{lst.id}", data=form_data)
        assert response.status_code == 200
        # Name should not have changed
        unchanged = List.query.get(lst.id)
        assert unchanged.name == "Valid Name"


# ---------------------------------------------------------------------------
# 6. POST /lists/delete/<id>
# ---------------------------------------------------------------------------


class TestDeleteList:
    """Tests for POST /lists/delete/<id> endpoint."""

    @patch("listarr.routes.lists_routes.unschedule_list")
    def test_deletes_list_successfully(self, mock_unschedule, client, db_session):
        """Deletes existing list and returns success JSON."""
        lst = make_list(name="Delete Me")
        db.session.add(lst)
        db.session.commit()
        list_id = lst.id

        response = client.post(f"/lists/delete/{list_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Delete Me" in data["message"]

        # Verify deleted
        assert List.query.get(list_id) is None

    def test_returns_404_for_missing_list(self, client):
        """Returns 404 for non-existent list."""
        response = client.post("/lists/delete/9999")
        assert response.status_code == 404

    @patch("listarr.routes.lists_routes.unschedule_list")
    def test_unschedules_before_deleting(self, mock_unschedule, client, db_session):
        """Calls unschedule_list before deleting."""
        lst = make_list(name="Scheduled Delete", schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()
        list_id = lst.id

        client.post(f"/lists/delete/{list_id}")
        mock_unschedule.assert_called_once_with(list_id)

    @patch("listarr.routes.lists_routes.unschedule_list")
    def test_delete_returns_success_message_with_list_name(self, mock_unschedule, client, db_session):
        """Delete response includes the list name in success message."""
        lst = make_list(name="Named List For Delete")
        db.session.add(lst)
        db.session.commit()
        list_id = lst.id

        response = client.post(f"/lists/delete/{list_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Named List For Delete" in data["message"]


# ---------------------------------------------------------------------------
# 7. GET /lists/wizard - Wizard page (create and edit modes)
# ---------------------------------------------------------------------------


class TestListWizard:
    """Tests for GET /lists/wizard endpoint."""

    def test_create_mode_with_preset_trending_movies(self, client):
        """Preset trending_movies sets service to radarr and is_preset=True."""
        response = client.get("/lists/wizard?preset=trending_movies")
        assert response.status_code == 200

    def test_create_mode_with_preset_trending_tv(self, client):
        """Preset trending_tv sets service to sonarr and is_preset=True."""
        response = client.get("/lists/wizard?preset=trending_tv")
        assert response.status_code == 200

    def test_create_mode_with_preset_popular_movies(self, client):
        """Preset popular_movies sets service to radarr."""
        response = client.get("/lists/wizard?preset=popular_movies")
        assert response.status_code == 200

    def test_create_mode_with_preset_top_rated_movies(self, client):
        """Preset top_rated_movies sets service to radarr."""
        response = client.get("/lists/wizard?preset=top_rated_movies")
        assert response.status_code == 200

    def test_create_mode_custom(self, client):
        """Custom preset renders wizard without preset info."""
        response = client.get("/lists/wizard?preset=custom")
        assert response.status_code == 200

    def test_create_mode_no_preset(self, client):
        """No preset parameter renders wizard in create mode."""
        response = client.get("/lists/wizard")
        assert response.status_code == 200

    def test_edit_mode_loads_existing_list(self, client, db_session):
        """Edit mode with list_id loads existing list data."""
        lst = make_list(name="Edit Me via Wizard")
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/wizard?list_id={lst.id}")
        assert response.status_code == 200
        assert b"Edit Me via Wizard" in response.data

    def test_edit_mode_returns_404_for_missing_list(self, client):
        """Edit mode with non-existent list_id returns 404."""
        response = client.get("/lists/wizard?list_id=9999")
        assert response.status_code == 404

    def test_edit_mode_with_tag_resolves_tag_name(self, client, db_session, temp_instance_path):
        """Edit mode fetches tag name when list has override_tag_id."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)

        lst = make_list(name="Tagged List")
        lst.override_tag_id = 5
        db.session.add(lst)
        db.session.commit()

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="radarr_key"),
            patch("listarr.services.radarr_service.get_tags", return_value=[{"id": 5, "label": "4k"}]),
        ):
            response = client.get(f"/lists/wizard?list_id={lst.id}")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 8. POST /lists/toggle/<id>
# ---------------------------------------------------------------------------


class TestToggleList:
    """Tests for POST /lists/toggle/<id> endpoint."""

    @patch("listarr.routes.lists_routes.unschedule_list")
    def test_toggles_active_to_inactive(self, mock_unschedule, client, db_session):
        """Active list is toggled to inactive; returns is_active=False."""
        lst = make_list(name="Active List", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.post(f"/lists/toggle/{lst.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["is_active"] is False

        updated = List.query.get(lst.id)
        assert updated.is_active is False

    @patch("listarr.routes.lists_routes.unschedule_list")
    @patch("listarr.routes.lists_routes.schedule_list")
    def test_toggles_inactive_to_active(self, mock_schedule, mock_unschedule, client, db_session):
        """Inactive list with cron is toggled to active; schedule_list called."""
        lst = make_list(name="Inactive Scheduled", is_active=False, schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()

        response = client.post(f"/lists/toggle/{lst.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["is_active"] is True

    def test_returns_404_for_missing_list(self, client):
        """Returns 404 for non-existent list."""
        response = client.post("/lists/toggle/9999")
        assert response.status_code == 404

    @patch("listarr.routes.lists_routes.unschedule_list")
    def test_toggle_returns_status_message(self, mock_unschedule, client, db_session):
        """Toggle response includes informative message."""
        lst = make_list(name="Toggle Message", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.post(f"/lists/toggle/{lst.id}")
        data = response.get_json()
        assert "message" in data


# ---------------------------------------------------------------------------
# 9. POST /lists/wizard/preview
# ---------------------------------------------------------------------------


class TestWizardPreview:
    """Tests for POST /lists/wizard/preview endpoint."""

    def test_returns_error_when_empty_json_provided(self, client):
        """Returns error dict when request body is empty JSON object."""
        # An empty dict is falsy in the route's `if not data:` check
        # The route returns {error, items:[]} instead of raising
        response = client.post("/lists/wizard/preview", json={})
        assert response.status_code == 200
        data = response.get_json()
        # Empty JSON triggers "no data" path OR tmdb not configured path
        assert "error" in data or "items" in data

    def test_returns_error_when_tmdb_not_configured(self, client):
        """Returns error when TMDB service config missing."""
        response = client.post("/lists/wizard/preview", json={"service": "radarr", "preset": "trending_movies"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["error"] == "TMDB not configured"
        assert data["items"] == []

    def test_returns_tmdb_preview_for_trending_movies(self, client, db_session, temp_instance_path):
        """Returns preview items for trending_movies preset."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("tmdb_key", instance_path=temp_instance_path)
        config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
        db.session.add(config)
        db.session.commit()

        mock_items = [
            {"id": 1, "title": "Movie 1", "release_date": "2024-01-15", "vote_average": 7.5},
            {"id": 2, "title": "Movie 2", "release_date": "2024-02-20", "vote_average": 8.0},
        ]

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="tmdb_key"),
            patch("listarr.routes.lists_routes.get_trending_movies_cached", return_value=mock_items),
        ):
            response = client.post("/lists/wizard/preview", json={"service": "radarr", "preset": "trending_movies"})

        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["title"] == "Movie 1"
        assert data["items"][0]["year"] == "2024"

    def test_returns_tmdb_preview_for_popular_tv(self, client, db_session, temp_instance_path):
        """Returns preview items for popular_tv preset."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("tmdb_key", instance_path=temp_instance_path)
        config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
        db.session.add(config)
        db.session.commit()

        mock_items = [
            {"id": 10, "name": "Show 1", "first_air_date": "2023-09-01", "vote_average": 8.5},
        ]

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="tmdb_key"),
            patch("listarr.routes.lists_routes.get_popular_tv_cached", return_value=mock_items),
        ):
            response = client.post("/lists/wizard/preview", json={"service": "sonarr", "preset": "popular_tv"})

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Show 1"

    def test_limits_preview_to_20_items(self, client, db_session, temp_instance_path):
        """Preview returns at most 20 items even when TMDB returns more."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("tmdb_key", instance_path=temp_instance_path)
        config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
        db.session.add(config)
        db.session.commit()

        mock_items = [
            {"id": i, "title": f"Movie {i}", "release_date": "2024-01-01", "vote_average": 7.0} for i in range(30)
        ]

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="tmdb_key"),
            patch("listarr.routes.lists_routes.get_trending_movies_cached", return_value=mock_items),
        ):
            response = client.post("/lists/wizard/preview", json={"service": "radarr", "preset": "trending_movies"})

        data = response.get_json()
        assert len(data["items"]) == 20

    def test_custom_discovery_with_filters(self, client, db_session, temp_instance_path):
        """Custom discovery uses filters to call discover_movies_cached."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("tmdb_key", instance_path=temp_instance_path)
        config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
        db.session.add(config)
        db.session.commit()

        mock_items = [
            {"id": 5, "title": "Filtered Movie", "release_date": "2023-06-15", "vote_average": 7.2},
        ]

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="tmdb_key"),
            patch("listarr.routes.lists_routes.discover_movies_cached", return_value=mock_items) as mock_discover,
        ):
            response = client.post(
                "/lists/wizard/preview",
                json={
                    "service": "radarr",
                    "preset": None,
                    "filters": {"genres_include": [28], "year_min": 2020},
                },
            )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["items"]) == 1
        mock_discover.assert_called_once()

    def test_handles_tmdb_api_error(self, client, db_session, temp_instance_path):
        """Returns error JSON when TMDB API raises RequestException."""
        from requests.exceptions import RequestException

        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("tmdb_key", instance_path=temp_instance_path)
        config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="tmdb_key"),
            patch(
                "listarr.routes.lists_routes.get_trending_movies_cached",
                side_effect=RequestException("Connection refused"),
            ),
        ):
            response = client.post("/lists/wizard/preview", json={"service": "radarr", "preset": "trending_movies"})

        assert response.status_code == 200
        data = response.get_json()
        assert "error" in data
        assert data["items"] == []

    def test_returns_preview_for_top_rated_movies(self, client, db_session, temp_instance_path):
        """Returns preview items for top_rated_movies preset."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("tmdb_key", instance_path=temp_instance_path)
        config = ServiceConfig(service="TMDB", api_key_encrypted=encrypted)
        db.session.add(config)
        db.session.commit()

        mock_items = [
            {"id": 99, "title": "Top Film", "release_date": "1994-10-14", "vote_average": 9.3},
        ]

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="tmdb_key"),
            patch("listarr.routes.lists_routes.get_top_rated_movies_cached", return_value=mock_items),
        ):
            response = client.post("/lists/wizard/preview", json={"service": "radarr", "preset": "top_rated_movies"})

        data = response.get_json()
        assert data["items"][0]["title"] == "Top Film"


# ---------------------------------------------------------------------------
# 10. POST /lists/wizard/submit
# ---------------------------------------------------------------------------


class TestWizardSubmit:
    """Tests for POST /lists/wizard/submit endpoint."""

    @patch("listarr.routes.lists_routes.unschedule_list")
    @patch("listarr.routes.lists_routes.schedule_list")
    def test_creates_list_via_wizard(self, mock_schedule, mock_unschedule, client, db_session):
        """No list_id in JSON creates a new list."""
        payload = {
            "name": "Wizard Created List",
            "service": "radarr",
            "preset": "trending_movies",
            "filters": {},
            "import_settings": {},
            "schedule": {"is_active": True},
        }
        response = client.post("/lists/wizard/submit", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "list_id" in data

        lst = List.query.filter_by(name="Wizard Created List").first()
        assert lst is not None
        assert lst.target_service == "RADARR"
        assert lst.tmdb_list_type == "trending_movies"

    @patch("listarr.routes.lists_routes.unschedule_list")
    @patch("listarr.routes.lists_routes.schedule_list")
    def test_updates_existing_list_via_wizard(self, mock_schedule, mock_unschedule, client, db_session):
        """list_id in JSON updates existing list."""
        lst = make_list(name="Old Wizard Name")
        db.session.add(lst)
        db.session.commit()

        payload = {
            "list_id": lst.id,
            "name": "Updated Wizard Name",
            "service": "radarr",
            "preset": "popular_movies",
            "filters": {},
            "import_settings": {},
            "schedule": {"is_active": True},
        }
        response = client.post("/lists/wizard/submit", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        updated = List.query.get(lst.id)
        assert updated.name == "Updated Wizard Name"
        assert updated.tmdb_list_type == "popular_movies"

    def test_validates_name_required(self, client, db_session):
        """Missing name returns 400."""
        payload = {
            "service": "radarr",
            "filters": {},
        }
        response = client.post("/lists/wizard/submit", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Name" in data["message"]

    def test_validates_service_required(self, client, db_session):
        """Missing service returns 400."""
        payload = {
            "name": "My List",
            "filters": {},
        }
        response = client.post("/lists/wizard/submit", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_validates_invalid_service(self, client, db_session):
        """Invalid service value returns 400."""
        payload = {
            "name": "My List",
            "service": "plex",  # Not radarr or sonarr
            "filters": {},
        }
        response = client.post("/lists/wizard/submit", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid service" in data["message"]

    def test_returns_400_when_no_json_content_type(self, client, db_session):
        """No JSON content-type causes Flask to return 4xx (415 or 400)."""
        # When no json content-type is set, Flask raises UnsupportedMediaType (415)
        # which routes through the error handler. The route itself returns 400
        # when data is None but only gets there with application/json content type.
        response = client.post("/lists/wizard/submit", json={})  # Empty JSON object - falsy
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    @patch("listarr.routes.lists_routes.unschedule_list")
    @patch("listarr.routes.lists_routes.schedule_list")
    def test_sets_discovery_type_for_custom_preset(self, mock_schedule, mock_unschedule, client, db_session):
        """Custom/None preset sets tmdb_list_type to 'discovery'."""
        payload = {
            "name": "Custom Discovery",
            "service": "radarr",
            "preset": "custom",
            "filters": {},
            "import_settings": {},
            "schedule": {"is_active": True},
        }
        response = client.post("/lists/wizard/submit", json=payload)
        data = response.get_json()
        assert data["success"] is True

        lst = List.query.filter_by(name="Custom Discovery").first()
        assert lst.tmdb_list_type == "discovery"

    @patch("listarr.routes.lists_routes.unschedule_list")
    @patch("listarr.routes.lists_routes.schedule_list")
    def test_handles_tag_creation(self, mock_schedule, mock_unschedule, client, db_session, temp_instance_path):
        """Tag name in import_settings triggers create_or_get_tag_id."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        payload = {
            "name": "Tagged List",
            "service": "radarr",
            "preset": "trending_movies",
            "filters": {},
            "import_settings": {"tag": "4k"},
            "schedule": {"is_active": True},
        }

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="radarr_key"),
            patch("listarr.services.radarr_service.create_or_get_tag_id", return_value=7) as mock_tag,
        ):
            response = client.post("/lists/wizard/submit", json=payload)

        data = response.get_json()
        assert data["success"] is True
        lst = List.query.filter_by(name="Tagged List").first()
        assert lst.override_tag_id == 7

    def test_rejects_numeric_tag_id_to_prevent_spurious_tag_creation(self, client, db_session):
        """Sending tag as an integer ID must return 400, not create a spurious tag named '45'.

        Regression test for: create.js old dropdown sent tag: 45 (integer) instead of
        "listarr-popular" (string label). wizard_submit previously converted this to str("45")
        and called create_or_get_tag_id("45"), creating a new tag literally named "45" in
        Radarr/Sonarr instead of applying the intended tag.
        """
        payload = {
            "name": "Bad Tag List",
            "service": "radarr",
            "preset": "trending_movies",
            "filters": {},
            "import_settings": {"tag": 45},  # integer ID — must be rejected
            "schedule": {"is_active": True},
        }
        response = client.post("/lists/wizard/submit", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "string" in data.get("error", "").lower()

    @patch("listarr.routes.lists_routes.unschedule_list")
    @patch("listarr.routes.lists_routes.schedule_list")
    def test_registers_schedule_after_create(self, mock_schedule, mock_unschedule, client, db_session):
        """When schedule cron set and active, schedule_list is called after creation."""
        payload = {
            "name": "Scheduled Wizard",
            "service": "radarr",
            "preset": "trending_movies",
            "filters": {},
            "import_settings": {},
            "schedule": {"cron": "0 0 * * *", "is_active": True},
        }
        response = client.post("/lists/wizard/submit", json=payload)
        data = response.get_json()
        assert data["success"] is True
        mock_schedule.assert_called_once()


# ---------------------------------------------------------------------------
# 11. GET /lists/wizard/defaults/<service>
# ---------------------------------------------------------------------------


class TestWizardDefaults:
    """Tests for GET /lists/wizard/defaults/<service> endpoint."""

    def test_returns_error_for_invalid_service(self, client):
        """Invalid service returns 400."""
        response = client.get("/lists/wizard/defaults/plex")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_returns_not_configured_when_no_config(self, client, db_session):
        """Returns configured=False when no ServiceConfig exists for radarr."""
        response = client.get("/lists/wizard/defaults/radarr")
        assert response.status_code == 200
        data = response.get_json()
        assert data["configured"] is False

    def test_returns_not_configured_for_sonarr(self, client, db_session):
        """Returns configured=False when no ServiceConfig exists for sonarr."""
        response = client.get("/lists/wizard/defaults/sonarr")
        assert response.status_code == 200
        data = response.get_json()
        assert data["configured"] is False

    def test_returns_defaults_for_radarr(self, client, db_session, temp_instance_path):
        """Returns configured=True with quality profiles, root folders, tags for radarr."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="radarr_key"),
            patch("listarr.services.radarr_service.get_quality_profiles", return_value=[{"id": 1, "name": "HD-1080p"}]),
            patch("listarr.services.radarr_service.get_root_folders", return_value=[{"path": "/movies", "id": 1}]),
            patch("listarr.services.radarr_service.get_tags", return_value=[{"id": 3, "label": "4k"}]),
        ):
            response = client.get("/lists/wizard/defaults/radarr")

        assert response.status_code == 200
        data = response.get_json()
        assert data["configured"] is True
        assert len(data["options"]["quality_profiles"]) == 1
        assert data["options"]["quality_profiles"][0]["name"] == "HD-1080p"
        assert len(data["options"]["root_folders"]) == 1
        assert len(data["options"]["tags"]) == 1

    def test_returns_defaults_for_sonarr(self, client, db_session, temp_instance_path):
        """Returns configured=True with data for sonarr."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("sonarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="SONARR",
            base_url="http://localhost:8989",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="sonarr_key"),
            patch("listarr.services.sonarr_service.get_quality_profiles", return_value=[]),
            patch("listarr.services.sonarr_service.get_root_folders", return_value=[]),
            patch("listarr.services.sonarr_service.get_tags", return_value=[]),
        ):
            response = client.get("/lists/wizard/defaults/sonarr")

        assert response.status_code == 200
        data = response.get_json()
        assert data["configured"] is True

    def test_includes_media_import_settings_defaults(self, client, db_session, temp_instance_path):
        """Returns MediaImportSettings defaults when they exist."""
        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)

        import_settings = MediaImportSettings(
            service="RADARR",
            root_folder="/movies",
            quality_profile_id=1,
            monitored=True,
            search_on_add=False,
        )
        db.session.add(import_settings)
        db.session.commit()

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="radarr_key"),
            patch("listarr.services.radarr_service.get_quality_profiles", return_value=[]),
            patch("listarr.services.radarr_service.get_root_folders", return_value=[]),
            patch("listarr.services.radarr_service.get_tags", return_value=[]),
        ):
            response = client.get("/lists/wizard/defaults/radarr")

        data = response.get_json()
        assert data["defaults"]["root_folder"] == "/movies"
        assert data["defaults"]["quality_profile_id"] == 1
        assert data["defaults"]["monitored"] is True
        assert data["defaults"]["search_on_add"] is False

    def test_handles_api_error_gracefully(self, client, db_session, temp_instance_path):
        """Returns configured=True with empty options when API call fails."""
        from requests.exceptions import RequestException

        from listarr.services.crypto_utils import encrypt_data

        encrypted = encrypt_data("radarr_key", instance_path=temp_instance_path)
        config = ServiceConfig(
            service="RADARR",
            base_url="http://localhost:7878",
            api_key_encrypted=encrypted,
        )
        db.session.add(config)
        db.session.commit()

        with (
            patch("listarr.routes.lists_routes.decrypt_data", return_value="radarr_key"),
            patch(
                "listarr.services.radarr_service.get_quality_profiles", side_effect=RequestException("Radarr offline")
            ),
        ):
            response = client.get("/lists/wizard/defaults/radarr")

        assert response.status_code == 200
        data = response.get_json()
        assert data["configured"] is True
        assert "error" in data
        assert data["options"]["quality_profiles"] == []


# ---------------------------------------------------------------------------
# 12. POST /lists/<id>/run - Trigger list import
# ---------------------------------------------------------------------------


class TestRunListImport:
    """Tests for POST /lists/<id>/run endpoint."""

    def test_returns_404_for_missing_list(self, client):
        """Returns 404 JSON when list does not exist."""
        response = client.post("/lists/9999/run")
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "not found" in data["message"]

    def test_returns_400_for_inactive_list(self, client, db_session):
        """Returns 400 when list is inactive."""
        lst = make_list(name="Inactive List", is_active=False)
        db.session.add(lst)
        db.session.commit()

        response = client.post(f"/lists/{lst.id}/run")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "not active" in data["message"]

    @patch("listarr.routes.lists_routes.submit_job")
    def test_starts_job_returns_202(self, mock_submit, client, db_session):
        """Returns 202 with job_id when job submitted successfully."""
        mock_submit.return_value = 42

        lst = make_list(name="Job List")
        db.session.add(lst)
        db.session.commit()

        response = client.post(f"/lists/{lst.id}/run")
        assert response.status_code == 202
        data = response.get_json()
        assert data["success"] is True
        assert data["job_id"] == 42
        assert data["status"] == "started"

    @patch("listarr.routes.lists_routes.submit_job")
    def test_handles_value_error_from_submit(self, mock_submit, client, db_session):
        """Returns 400 when submit_job raises ValueError."""
        mock_submit.side_effect = ValueError("Bad job")

        lst = make_list(name="ValueError List")
        db.session.add(lst)
        db.session.commit()

        response = client.post(f"/lists/{lst.id}/run")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    @patch("listarr.routes.lists_routes.submit_job")
    def test_handles_runtime_error_from_submit(self, mock_submit, client, db_session):
        """Returns 500 when submit_job raises RuntimeError."""
        mock_submit.side_effect = RuntimeError("Worker pool error")

        lst = make_list(name="RuntimeError List")
        db.session.add(lst)
        db.session.commit()

        response = client.post(f"/lists/{lst.id}/run")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False


# ---------------------------------------------------------------------------
# 13. GET /lists/<id>/status - Get job status
# ---------------------------------------------------------------------------


class TestGetListStatus:
    """Tests for GET /lists/<id>/status endpoint."""

    def test_returns_404_for_missing_list(self, client):
        """Returns 404 when list does not exist."""
        response = client.get("/lists/9999/status")
        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"]

    @patch("listarr.routes.lists_routes.get_job_status")
    def test_returns_idle_when_no_jobs(self, mock_status, client, db_session):
        """Returns idle status when get_job_status returns None."""
        mock_status.return_value = None
        lst = make_list(name="No Jobs List")
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/{lst.id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "idle"
        assert data["list_id"] == lst.id

    @patch("listarr.routes.lists_routes.get_job_status")
    def test_returns_running_status(self, mock_status, client, db_session):
        """Returns running status when job is running."""
        mock_status.return_value = {"status": "running"}
        lst = make_list(name="Running Status List")
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/{lst.id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "running"

    @patch("listarr.routes.lists_routes.get_job_status")
    def test_returns_completed_with_summary(self, mock_status, client, db_session):
        """Returns completed status with result summary."""
        mock_status.return_value = {
            "status": "completed",
            "items_found": 10,
            "items_added": 5,
            "items_skipped": 3,
            "items_failed": 2,
        }
        lst = make_list(name="Completed List")
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/{lst.id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "completed"
        assert "result" in data
        assert data["result"]["summary"]["total"] == 10
        assert data["result"]["summary"]["added_count"] == 5
        assert data["result"]["summary"]["skipped_count"] == 3
        assert data["result"]["summary"]["failed_count"] == 2

    @patch("listarr.routes.lists_routes.get_job_status")
    def test_returns_failed_with_error(self, mock_status, client, db_session):
        """Returns failed status with error message."""
        mock_status.return_value = {
            "status": "failed",
            "error_message": "TMDB API unavailable",
        }
        lst = make_list(name="Failed List")
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/{lst.id}/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "failed"
        assert data["error"] == "TMDB API unavailable"

    @patch("listarr.routes.lists_routes.get_job_status")
    def test_returns_idle_for_unknown_status(self, mock_status, client, db_session):
        """Unknown job status maps to idle."""
        mock_status.return_value = {"status": "pending"}
        lst = make_list(name="Pending List")
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/{lst.id}/status")
        data = response.get_json()
        assert data["status"] == "idle"

    @patch("listarr.routes.lists_routes.get_job_status")
    def test_includes_last_run_at_timestamp(self, mock_status, client, db_session):
        """Response includes last_run_at from list model."""
        mock_status.return_value = None
        run_time = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        lst = make_list(name="With Timestamp", last_run_at=run_time)
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/{lst.id}/status")
        data = response.get_json()
        assert data["last_run_at"] is not None
        assert "2026-01-15" in data["last_run_at"]

    @patch("listarr.routes.lists_routes.get_job_status")
    def test_last_run_at_is_none_for_never_run_list(self, mock_status, client, db_session):
        """last_run_at is None when list has never been run."""
        mock_status.return_value = None
        lst = make_list(name="Never Run")
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/{lst.id}/status")
        data = response.get_json()
        assert data["last_run_at"] is None


# ---------------------------------------------------------------------------
# Schedule API tests (migrated from test_schedule_routes.py)
# ---------------------------------------------------------------------------


def make_service_config_for_schedule(scheduler_paused=False):
    """Helper to create a ServiceConfig with scheduler_paused setting."""
    return ServiceConfig(
        service="RADARR",
        api_key_encrypted="encrypted-dummy",
        base_url="http://localhost:7878",
        scheduler_paused=scheduler_paused,
    )


class TestPauseSchedule:
    """Tests for POST /api/schedule/pause endpoint."""

    @patch("listarr.routes.lists_routes.pause_scheduler")
    def test_pauses_scheduler_successfully(self, mock_pause, client, db_session):
        """Returns success JSON when pause_scheduler succeeds."""
        response = client.post("/api/schedule/pause")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_pause.assert_called_once()

    @patch("listarr.routes.lists_routes.pause_scheduler")
    def test_handles_error_on_pause(self, mock_pause, client, db_session):
        """Returns 500 when pause_scheduler raises RuntimeError."""
        mock_pause.side_effect = RuntimeError("Scheduler not running")
        response = client.post("/api/schedule/pause")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "message" in data

    @patch("listarr.routes.lists_routes.pause_scheduler")
    def test_pause_response_format(self, mock_pause, client, db_session):
        """Pause response has correct JSON structure."""
        response = client.post("/api/schedule/pause")
        assert response.content_type == "application/json"
        data = response.get_json()
        assert isinstance(data, dict)
        assert "success" in data


class TestResumeSchedule:
    """Tests for POST /api/schedule/resume endpoint."""

    @patch("listarr.routes.lists_routes.resume_scheduler")
    def test_resumes_scheduler_successfully(self, mock_resume, client, db_session):
        """Returns success JSON when resume_scheduler succeeds."""
        response = client.post("/api/schedule/resume")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_resume.assert_called_once()

    @patch("listarr.routes.lists_routes.resume_scheduler")
    def test_handles_error_on_resume(self, mock_resume, client, db_session):
        """Returns 500 when resume_scheduler raises RuntimeError."""
        mock_resume.side_effect = RuntimeError("Cannot resume")
        response = client.post("/api/schedule/resume")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "message" in data

    @patch("listarr.routes.lists_routes.resume_scheduler")
    def test_resume_response_format(self, mock_resume, client, db_session):
        """Resume response has correct JSON structure."""
        response = client.post("/api/schedule/resume")
        assert response.content_type == "application/json"
        data = response.get_json()
        assert isinstance(data, dict)
        assert "success" in data


class TestGetScheduleStatus:
    """Tests for GET /api/schedule/status endpoint."""

    @patch("listarr.routes.lists_routes.is_list_running")
    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_returns_empty_when_no_lists(self, mock_next_run, mock_running, client, db_session):
        """Returns paused=False and empty lists when no lists exist."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        response = client.get("/api/schedule/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "paused" in data
        assert "lists" in data
        assert data["lists"] == []
        assert data["paused"] is False

    @patch("listarr.routes.lists_routes.is_list_running")
    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_returns_paused_state(self, mock_next_run, mock_running, client, db_session):
        """Returns paused=True when scheduler is paused in config."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        config = make_service_config_for_schedule(scheduler_paused=True)
        db.session.add(config)
        db.session.commit()

        response = client.get("/api/schedule/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["paused"] is True

    @patch("listarr.routes.lists_routes.is_list_running")
    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_returns_status_with_list_data(self, mock_next_run, mock_running, client, db_session):
        """Returns list data with status for each list."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="Status Test List", schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["lists"]) == 1
        list_data = data["lists"][0]
        assert list_data["name"] == "Status Test List"
        assert "status" in list_data
        assert "next_run" in list_data
        assert "has_schedule" in list_data

    @patch("listarr.routes.lists_routes.is_list_running")
    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_includes_status_html_in_response(self, mock_next_run, mock_running, client, db_session):
        """Each list entry includes rendered status_html badge."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="HTML Badge Test")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        assert len(data["lists"]) == 1
        list_data = data["lists"][0]
        assert "status_html" in list_data
        assert "<span" in list_data["status_html"]

    @patch("listarr.routes.lists_routes.is_list_running")
    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_manual_only_status_when_no_cron(self, mock_next_run, mock_running, client, db_session):
        """List without cron has status 'Manual only'."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        lst = make_list(name="Manual Only", schedule_cron=None)
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        list_data = data["lists"][0]
        assert list_data["status"] == "Manual only"
        assert list_data["has_schedule"] is False

    @patch("listarr.routes.lists_routes.is_list_running")
    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_returns_scheduled_status_for_cron_list(self, mock_next_run, mock_running, client, db_session):
        """List with cron and not paused has status 'Scheduled'."""
        from datetime import timedelta

        future_dt = datetime.now(timezone.utc) + timedelta(hours=6)
        mock_running.return_value = False
        mock_next_run.return_value = future_dt

        lst = make_list(name="Cron List", schedule_cron="0 0 * * *", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        list_data = data["lists"][0]
        assert list_data["status"] == "Scheduled"
        assert list_data["has_schedule"] is True

    @patch("listarr.routes.lists_routes.is_list_running")
    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_returns_running_status_for_active_job(self, mock_next_run, mock_running, client, db_session):
        """List with running job has status 'Running'."""
        mock_running.return_value = True
        mock_next_run.return_value = None

        lst = make_list(name="Running Now")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        list_data = data["lists"][0]
        assert list_data["status"] == "Running"

    @patch("listarr.routes.lists_routes.is_list_running")
    @patch("listarr.routes.lists_routes.get_next_run_time")
    def test_returns_paused_status_when_scheduler_paused_and_cron_set(
        self, mock_next_run, mock_running, client, db_session
    ):
        """List with cron and scheduler paused has status 'Paused'."""
        mock_running.return_value = False
        mock_next_run.return_value = None

        config = make_service_config_for_schedule(scheduler_paused=True)
        db.session.add(config)

        lst = make_list(name="Paused Scheduled", schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()

        response = client.get("/api/schedule/status")
        data = response.get_json()
        list_data = data["lists"][0]
        assert list_data["status"] == "Paused"


class TestUpdateSchedule:
    """Tests for POST /api/schedule/<list_id>/update endpoint."""

    def test_returns_404_for_missing_list(self, client, db_session):
        """Returns 404 when list does not exist."""
        response = client.post("/api/schedule/9999/update", json={"schedule_cron": "0 0 * * *"})
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    def test_returns_400_for_invalid_json(self, client, db_session):
        """Returns 400 when request body is not valid JSON."""
        lst = make_list(name="JSON Test")
        db.session.add(lst)
        db.session.commit()

        # Sending non-JSON content type
        response = client.post(
            f"/api/schedule/{lst.id}/update",
            data="not json at all",
            content_type="text/plain",
        )
        # Flask raises UnsupportedMediaType (415) which goes through error handler
        assert response.status_code in (400, 415, 500)

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.schedule_list")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_sets_valid_cron_expression(self, mock_unschedule, mock_schedule, mock_validate, client, db_session):
        """Valid cron sets schedule and returns success."""
        mock_validate.return_value = {"valid": True, "description": "Every day at midnight"}

        lst = make_list(name="Cron Update Test", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "0 0 * * *"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["schedule_cron"] == "0 0 * * *"
        assert "status" in data

        # Verify DB updated
        updated = List.query.get(lst.id)
        assert updated.schedule_cron == "0 0 * * *"

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_removes_schedule_when_empty_cron(self, mock_unschedule, mock_validate, client, db_session):
        """Empty schedule_cron removes the schedule."""
        lst = make_list(name="Remove Cron", schedule_cron="0 0 * * *", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": ""},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["schedule_cron"] == ""

        # Verify DB cleared
        updated = List.query.get(lst.id)
        assert updated.schedule_cron is None

    @patch("listarr.services.scheduler.validate_cron_expression")
    def test_returns_400_for_invalid_cron(self, mock_validate, client, db_session):
        """Returns 400 when cron expression is invalid."""
        mock_validate.return_value = {
            "valid": False,
            "error": "Invalid cron syntax",
            "description": "",
        }

        lst = make_list(name="Invalid Cron Test")
        db.session.add(lst)
        db.session.commit()

        response = client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "not-a-cron"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid cron" in data["message"]

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.schedule_list")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_response_includes_status(self, mock_unschedule, mock_schedule, mock_validate, client, db_session):
        """Response includes list status after update."""
        mock_validate.return_value = {"valid": True, "description": "Every hour"}

        lst = make_list(name="Status Response Test", is_active=True)
        db.session.add(lst)
        db.session.commit()

        response = client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "0 * * * *"},
        )
        data = response.get_json()
        assert data["success"] is True
        assert "status" in data
        assert "next_run" in data

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.schedule_list")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_schedule_list_called_when_active(self, mock_unschedule, mock_schedule, mock_validate, client, db_session):
        """schedule_list is called when list is active and cron is set."""
        mock_validate.return_value = {"valid": True, "description": "Daily"}

        lst = make_list(name="Active Schedule Call", is_active=True)
        db.session.add(lst)
        db.session.commit()

        client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "0 0 * * *"},
        )
        mock_schedule.assert_called_once_with(lst.id, "0 0 * * *")

    @patch("listarr.services.scheduler.validate_cron_expression")
    @patch("listarr.services.scheduler.unschedule_list")
    def test_unschedule_called_when_inactive_list(self, mock_unschedule, mock_validate, client, db_session):
        """unschedule_list is called when list is inactive even with cron set."""
        mock_validate.return_value = {"valid": True, "description": "Daily"}

        lst = make_list(name="Inactive With Cron", is_active=False)
        db.session.add(lst)
        db.session.commit()

        client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": "0 0 * * *"},
        )
        mock_unschedule.assert_called_once_with(lst.id)

    @patch("listarr.services.scheduler.unschedule_list")
    def test_unschedule_called_when_empty_cron(self, mock_unschedule, client, db_session):
        """unschedule_list is called when cron is removed."""
        lst = make_list(name="Unschedule Test", schedule_cron="0 0 * * *")
        db.session.add(lst)
        db.session.commit()

        client.post(
            f"/api/schedule/{lst.id}/update",
            json={"schedule_cron": ""},
        )
        mock_unschedule.assert_called_once_with(lst.id)


# ---------------------------------------------------------------------------
# Stub route tests
# ---------------------------------------------------------------------------


class TestListsCreateStub:
    """Tests for /lists/create stub route."""

    def test_lists_create_returns_200(self, client):
        """Lists create stub returns 200."""
        response = client.get("/lists/create")
        assert response.status_code == 200
        assert b"Create List" in response.data

    def test_lists_create_preset_returns_200(self, client):
        """Lists create preset stub returns 200."""
        response = client.get("/lists/create/preset")
        assert response.status_code == 200
        assert b"Preset" in response.data

    def test_lists_create_custom_returns_200(self, client):
        """Lists create custom stub returns 200."""
        response = client.get("/lists/create/custom")
        assert response.status_code == 200
        assert b"Custom" in response.data


class TestListsEditStub:
    """Tests for /lists/<id>/edit stub route."""

    def test_lists_edit_returns_200(self, client):
        """Lists edit stub returns 200."""
        response = client.get("/lists/1/edit")
        assert response.status_code == 200
        assert b"Edit List" in response.data


class TestAuthEnforcementLists:
    """
    Auth enforcement for every @login_required route in lists_routes.py
    EXCEPT /lists GET which is covered in test_auth_routes.py::TestRouteProtection.

    Per D-03 (audit every @login_required route), D-04 (HTML -> 302 /login),
    D-05 (JSON -> 401), D-06 (use app_with_auth + auth_client).

    test_user is mandatory: app_with_auth has no session-level user, so without
    it check_setup() redirects to /setup not /login (Pitfall 1).
    """

    def test_api_lists_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/api/lists", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 401

    def test_lists_create_get_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/lists/create")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_lists_create_preset_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/lists/create/preset")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_lists_create_custom_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/lists/create/custom")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_lists_id_edit_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/lists/1/edit")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_lists_edit_id_get_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/lists/edit/1")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_lists_wizard_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/lists/wizard")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_lists_create_post_returns_405_before_auth(self, auth_client, test_user):
        """POST /lists/create has no route, so method rejection happens before auth."""
        response = auth_client.post("/lists/create", json={})
        assert response.status_code == 405

    def test_lists_edit_post_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/lists/edit/1", data={})
        assert response.status_code == 302
        assert "/login" in response.location

    def test_lists_delete_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/lists/delete/1", json={})
        assert response.status_code == 401

    def test_lists_toggle_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/lists/toggle/1", json={})
        assert response.status_code == 401

    def test_lists_wizard_preview_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/lists/wizard/preview", json={})
        assert response.status_code == 401

    def test_lists_wizard_submit_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/lists/wizard/submit", json={})
        assert response.status_code == 401

    def test_lists_wizard_defaults_requires_auth(self, auth_client, test_user):
        response = auth_client.get(
            "/lists/wizard/defaults/RADARR",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 401

    def test_lists_run_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/lists/1/run", json={})
        assert response.status_code == 401

    def test_api_cron_validate_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/api/cron/validate", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 401

    def test_lists_status_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/lists/1/status", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 401

    def test_api_schedule_pause_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/api/schedule/pause", json={})
        assert response.status_code == 401

    def test_api_schedule_resume_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/api/schedule/resume", json={})
        assert response.status_code == 401

    def test_api_schedule_status_requires_auth(self, auth_client, test_user):
        response = auth_client.get("/api/schedule/status", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 401

    def test_api_schedule_update_requires_auth(self, auth_client, test_user):
        response = auth_client.post("/api/schedule/1/update", json={})
        assert response.status_code == 401


class TestCsrfProtectionLists:
    """
    CSRF rejection for every POST endpoint in lists_routes.py.

    Per D-07 (every POST), D-08 (status 400 only, no body assertion),
    D-09 (client_with_csrf + POST without token).

    LOGIN_DISABLED=True in app_with_csrf, so requests pass @login_required
    and reach the CSRF check.
    """

    def test_lists_create_post_returns_405_before_csrf(self, client_with_csrf):
        """POST /lists/create has no route, so method rejection happens before CSRF."""
        response = client_with_csrf.post("/lists/create", json={})
        assert response.status_code == 405

    def test_lists_edit_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/lists/edit/1", data={})
        assert response.status_code == 400

    def test_lists_delete_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/lists/delete/1", json={})
        assert response.status_code == 400

    def test_lists_toggle_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/lists/toggle/1", json={})
        assert response.status_code == 400

    def test_lists_wizard_preview_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/lists/wizard/preview", json={})
        assert response.status_code == 400

    def test_lists_wizard_submit_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/lists/wizard/submit", json={})
        assert response.status_code == 400

    def test_lists_run_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/lists/1/run", json={})
        assert response.status_code == 400

    def test_api_schedule_pause_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/api/schedule/pause", json={})
        assert response.status_code == 400

    def test_api_schedule_resume_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/api/schedule/resume", json={})
        assert response.status_code == 400

    def test_api_schedule_update_rejects_no_csrf(self, client_with_csrf):
        response = client_with_csrf.post("/api/schedule/1/update", json={})
        assert response.status_code == 400


class TestWizardAndEditCoverage:
    """
    TEST-03 and TEST-04 coverage closure for list_wizard, wizard_preview,
    and edit_list bodies.
    """

    def test_list_wizard_top_rated_movies_preset(self, client):
        response = client.get("/lists/wizard?preset=top_rated_movies")
        assert response.status_code == 200
        assert b"top_rated_movies" in response.data

    def test_list_wizard_top_rated_tv_preset(self, client):
        response = client.get("/lists/wizard?preset=top_rated_tv")
        assert response.status_code == 200
        assert b"top_rated_tv" in response.data

    def test_list_wizard_with_region(self, client):
        response = client.get("/lists/wizard?preset=top_rated_movies&region=US")
        assert response.status_code == 200

    def test_list_wizard_default_returns_200(self, client):
        response = client.get("/lists/wizard")
        assert response.status_code == 200

    @patch("listarr.routes.lists_routes.decrypt_data", return_value="tmdb-key")
    @patch("listarr.routes.lists_routes.get_top_rated_movies_cached")
    def test_wizard_preview_top_rated_movies(self, mock_cache, mock_decrypt, client, db_session):
        db.session.add(ServiceConfig(service="TMDB", api_key_encrypted="encrypted"))
        db.session.commit()
        mock_cache.return_value = [
            {
                "id": 1,
                "title": "Test Movie",
                "release_date": "2024-01-01",
                "vote_average": 8.6,
            }
        ]

        response = client.post(
            "/lists/wizard/preview",
            json={"service": "radarr", "preset": "top_rated_movies", "filters": {}},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["items"][0]["title"] == "Test Movie"
        mock_cache.assert_called_once_with("tmdb-key")

    @patch("listarr.routes.lists_routes.decrypt_data", return_value="tmdb-key")
    @patch("listarr.routes.lists_routes.get_top_rated_tv_cached")
    def test_wizard_preview_top_rated_tv(self, mock_cache, mock_decrypt, client, db_session):
        db.session.add(ServiceConfig(service="TMDB", api_key_encrypted="encrypted"))
        db.session.commit()
        mock_cache.return_value = [
            {
                "id": 10,
                "name": "Test Show",
                "first_air_date": "2023-02-03",
                "vote_average": 9.1,
            }
        ]

        response = client.post(
            "/lists/wizard/preview",
            json={"service": "sonarr", "preset": "top_rated_tv", "filters": {}},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["items"][0]["title"] == "Test Show"
        mock_cache.assert_called_once_with("tmdb-key")

    def test_edit_list_legacy_limit_migration(self, client, db_session):
        lst = List(
            name="Legacy Limit",
            target_service="RADARR",
            tmdb_list_type="trending_movies",
            filters_json={"limit": 10},
            is_active=True,
        )
        db.session.add(lst)
        db.session.commit()

        response = client.get(f"/lists/{lst.id}/edit")

        assert response.status_code == 200
        assert b"Edit List" in response.data
