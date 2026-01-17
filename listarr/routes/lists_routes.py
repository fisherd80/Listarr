from flask import render_template, flash, request, redirect, url_for, current_app, jsonify
from datetime import datetime, timezone
from listarr.routes import bp
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.forms.lists_forms import ListForm
from listarr.services.crypto_utils import decrypt_data
from listarr.services.tmdb_service import (
    get_trending_movies,
    get_trending_tv,
    get_popular_movies,
    get_popular_tv,
    discover_movies,
    discover_tv,
)
from listarr import db

@bp.route("/lists")
def lists_page():
    lists = db.session.query(List).all()
    form = ListForm()
    return render_template("lists.html", lists=lists, form=form)

@bp.route("/lists/create", methods=["POST"])
def create_list():
    form = ListForm()

    if form.validate_on_submit():
        try:
            new_list = List(
                name=form.name.data,
                target_service=form.target_service.data,
                tmdb_list_type=form.tmdb_list_type.data,
                filters_json=form.filters_json.data or "{}",
                is_active=form.is_active.data,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_list)
            db.session.commit()
            flash(f"List '{new_list.name}' created successfully!", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating list: {e}", exc_info=True)
            flash("Error creating list. Please try again.", "error")
    else:
        flash("Please correct the errors in the form.", "error")

    return redirect(url_for("main.lists_page"))

@bp.route("/lists/edit/<int:list_id>", methods=["GET", "POST"])
def edit_list(list_id):
    list_obj = List.query.get_or_404(list_id)
    form = ListForm(obj=list_obj)

    if request.method == "POST" and form.validate_on_submit():
        try:
            list_obj.name = form.name.data
            list_obj.target_service = form.target_service.data
            list_obj.tmdb_list_type = form.tmdb_list_type.data
            list_obj.is_active = form.is_active.data
            list_obj.filters_json = form.filters_json.data or "{}"

            db.session.commit()
            flash(f"List '{list_obj.name}' updated successfully!", "success")
            return redirect(url_for("main.lists_page"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating list: {e}", exc_info=True)
            flash("Error updating list. Please try again.", "error")

    return render_template("edit_list.html", form=form, list=list_obj)

@bp.route("/lists/delete/<int:list_id>", methods=["POST"])
def delete_list(list_id):
    list_obj = List.query.get_or_404(list_id)

    try:
        list_name = list_obj.name
        db.session.delete(list_obj)
        db.session.commit()
        flash(f"List '{list_name}' deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting list: {e}", exc_info=True)
        flash("Error deleting list. Please try again.", "error")

    return redirect(url_for("main.lists_page"))

@bp.route("/lists/wizard")
def list_wizard():
    """
    Wizard route for creating lists via presets or custom configuration.

    Query parameters:
        preset: string (trending_movies, trending_tv, popular_movies, popular_tv, custom, or None)
        service: string (radarr, sonarr, or None)
        list_id: int (for edit mode)
    """
    preset = request.args.get("preset")
    service = request.args.get("service")
    list_id = request.args.get("list_id", type=int)

    # Edit mode - load existing list
    if list_id:
        list_obj = List.query.get_or_404(list_id)

        # Determine if it's a preset or custom list
        is_preset = list_obj.tmdb_list_type not in ["discovery", "custom"]
        preset_value = list_obj.tmdb_list_type if is_preset else None

        # Build existing list data for JavaScript
        existing_list = {
            "id": list_obj.id,
            "name": list_obj.name,
            "service": list_obj.target_service.lower(),
            "preset": preset_value,
            "tmdb_list_type": list_obj.tmdb_list_type,
            "is_preset": is_preset,
            "filters": list_obj.filters_json or {},
            "limit": list_obj.limit or 20,
            "import_settings": {
                "quality_profile_id": list_obj.override_quality_profile,
                "root_folder": list_obj.override_root_folder,
                "tag_id": list_obj.override_tag_id,
                "monitored": True if list_obj.override_monitored == 1 else (False if list_obj.override_monitored == 0 else None),
                "search_on_add": True if list_obj.override_search_on_add == 1 else (False if list_obj.override_search_on_add == 0 else None),
                "season_folder": True if list_obj.override_season_folder == 1 else (False if list_obj.override_season_folder == 0 else None),
            },
            "schedule": {
                "cron": list_obj.schedule_cron,
                "is_active": list_obj.is_active,
            },
        }

        return render_template(
            "list_wizard.html",
            preset=preset_value,
            service=list_obj.target_service.lower(),
            is_preset=is_preset,
            list_id=list_id,
            edit_mode=True,
            existing_list=existing_list,
        )

    # Create mode - determine wizard mode based on preset
    is_preset = False

    if preset in ["trending_movies", "popular_movies"]:
        # Movie presets always use Radarr
        service = "radarr"
        is_preset = True
    elif preset in ["trending_tv", "popular_tv"]:
        # TV presets always use Sonarr
        service = "sonarr"
        is_preset = True
    elif preset == "custom" or preset is None:
        # Custom mode - service comes from param or will be selected in step 1
        is_preset = False
        # Keep service as-is from query param (may be None)

    return render_template(
        "list_wizard.html",
        preset=preset,
        service=service,
        is_preset=is_preset,
        list_id=list_id,
        edit_mode=False,
        existing_list=None,
    )


@bp.route("/lists/toggle/<int:list_id>", methods=["POST"])
def toggle_list(list_id):
    list_obj = List.query.get_or_404(list_id)

    try:
        # Toggle the is_active field
        list_obj.is_active = not list_obj.is_active
        db.session.commit()

        status_text = "enabled" if list_obj.is_active else "disabled"

        return jsonify({
            "success": True,
            "is_active": list_obj.is_active,
            "message": f"List {status_text}"
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling list: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Error toggling list. Please try again."
        }), 500


@bp.route("/lists/wizard/preview", methods=["POST"])
def wizard_preview():
    """
    TMDB preview endpoint for the list creation wizard.

    Fetches a sample of TMDB results based on preset or custom filters.
    Returns up to 5 items for preview display.

    Request JSON:
        service: string (radarr or sonarr)
        preset: string (trending_movies, trending_tv, popular_movies, popular_tv, or None)
        filters: object (genre_ids, year_min, year_max, rating_min)

    Returns JSON:
        items: array of preview items with id, title, year, rating
        error: string (if TMDB not configured or API error)
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided", "items": []})

    service = data.get("service")  # radarr or sonarr
    preset = data.get("preset")  # preset name or None
    filters = data.get("filters", {})

    # Get TMDB API key from settings
    tmdb_config = ServiceConfig.query.filter_by(service="TMDB").first()
    if not tmdb_config or not tmdb_config.api_key_encrypted:
        return jsonify({"error": "TMDB not configured", "items": []})

    try:
        api_key = decrypt_data(tmdb_config.api_key_encrypted)
    except Exception as e:
        current_app.logger.error(f"Error decrypting TMDB API key: {e}", exc_info=True)
        return jsonify({"error": "Failed to decrypt TMDB API key", "items": []})

    # Fetch based on preset or filters
    items = []
    try:
        if preset == "trending_movies":
            items = get_trending_movies(api_key)
        elif preset == "trending_tv":
            items = get_trending_tv(api_key)
        elif preset == "popular_movies":
            items = get_popular_movies(api_key)
        elif preset == "popular_tv":
            items = get_popular_tv(api_key)
        else:
            # Custom discovery with filters
            tmdb_filters = {}

            # Genre filter
            if filters.get("genre_ids"):
                tmdb_filters["with_genres"] = ",".join(map(str, filters["genre_ids"]))

            # Year range filters
            if filters.get("year_min"):
                if service == "radarr":
                    tmdb_filters["primary_release_date.gte"] = f"{filters['year_min']}-01-01"
                else:
                    tmdb_filters["first_air_date.gte"] = f"{filters['year_min']}-01-01"

            if filters.get("year_max"):
                if service == "radarr":
                    tmdb_filters["primary_release_date.lte"] = f"{filters['year_max']}-12-31"
                else:
                    tmdb_filters["first_air_date.lte"] = f"{filters['year_max']}-12-31"

            # Rating filter
            if filters.get("rating_min"):
                tmdb_filters["vote_average.gte"] = filters["rating_min"]

            # Fetch based on service type
            if service == "radarr":
                items = discover_movies(api_key, tmdb_filters)
            else:
                items = discover_tv(api_key, tmdb_filters)

    except Exception as e:
        current_app.logger.error(f"Error fetching TMDB preview: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch preview from TMDB", "items": []})

    # Return first 5 items for preview
    # tmdbv3api returns AsObj with 'results' attribute containing the actual items
    # Both the response and .results are AsObj, so convert to list before slicing
    if hasattr(items, 'results') and items.results:
        items_list = list(items.results)[:5]
    else:
        items_list = []

    preview_items = []
    for item in items_list:
        # tmdbv3api returns AsObj - access as dict to get raw values
        # AsObj supports dict-like access via __getitem__
        try:
            # Try dict-style access first (more reliable for AsObj)
            item_id = item["id"] if "id" in item else None
            title = item.get("title") or item.get("name") or "Unknown"
            release_date = item.get("release_date") or item.get("first_air_date") or ""
            vote_average = item.get("vote_average")
        except (TypeError, KeyError):
            # Fallback to attribute access
            item_id = getattr(item, "id", None)
            title = getattr(item, "title", None) or getattr(item, "name", None) or "Unknown"
            release_date = getattr(item, "release_date", None) or getattr(item, "first_air_date", None) or ""
            vote_average = getattr(item, "vote_average", None)

        year = release_date[:4] if release_date else None

        preview_items.append({
            "id": item_id,
            "title": title,
            "year": year,
            "rating": round(vote_average, 1) if vote_average else None,
        })

    return jsonify({"items": preview_items})


@bp.route("/lists/wizard/submit", methods=["POST"])
def wizard_submit():
    """
    Handle wizard form submission for creating or updating lists.

    Request JSON:
        list_id: int (None for create, ID for edit)
        name: string (required)
        service: string (radarr or sonarr)
        preset: string (trending_movies, trending_tv, popular_movies, popular_tv, or None/custom)
        filters: object (genre_ids, year_min, year_max, rating_min, limit)
        import_settings: object (quality_profile_id, root_folder, tag_id, monitored, search_on_add)
        schedule: object (cron, is_active)

    Returns JSON:
        success: bool
        list_id: int (ID of created/updated list)
        error: string (if success is false)
    """
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    # Extract wizard data
    list_id = data.get("list_id")  # None for create, ID for edit
    name = data.get("name")
    service = data.get("service")  # radarr or sonarr
    preset = data.get("preset")    # preset name or None/custom
    filters = data.get("filters", {})
    import_settings = data.get("import_settings", {})
    schedule = data.get("schedule", {})

    # Validation
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    if not service or service not in ["radarr", "sonarr"]:
        return jsonify({"success": False, "error": "Invalid service"}), 400

    # Determine tmdb_list_type
    if preset and preset not in ["custom", ""]:
        tmdb_list_type = preset  # trending_movies, popular_tv, etc.
    else:
        tmdb_list_type = "discovery"

    # Build filters_json
    filters_json = {
        "genre_ids": filters.get("genre_ids", []),
        "year_min": filters.get("year_min"),
        "year_max": filters.get("year_max"),
        "rating_min": filters.get("rating_min"),
    }

    try:
        if list_id:
            # Edit mode
            list_obj = List.query.get_or_404(list_id)
            list_obj.name = name
            list_obj.target_service = service.upper()
            list_obj.tmdb_list_type = tmdb_list_type
            list_obj.filters_json = filters_json
            list_obj.limit = filters.get("limit", 20)
            list_obj.override_quality_profile = import_settings.get("quality_profile_id")
            list_obj.override_root_folder = import_settings.get("root_folder")
            list_obj.override_tag_id = import_settings.get("tag_id")
            list_obj.override_monitored = 1 if import_settings.get("monitored") else (0 if import_settings.get("monitored") is False else None)
            list_obj.override_search_on_add = 1 if import_settings.get("search_on_add") else (0 if import_settings.get("search_on_add") is False else None)
            list_obj.override_season_folder = 1 if import_settings.get("season_folder") else (0 if import_settings.get("season_folder") is False else None)
            list_obj.schedule_cron = schedule.get("cron")
            list_obj.is_active = schedule.get("is_active", True)
        else:
            # Create mode
            list_obj = List(
                name=name,
                target_service=service.upper(),
                tmdb_list_type=tmdb_list_type,
                filters_json=filters_json,
                limit=filters.get("limit", 20),
                override_quality_profile=import_settings.get("quality_profile_id"),
                override_root_folder=import_settings.get("root_folder"),
                override_tag_id=import_settings.get("tag_id"),
                override_monitored=1 if import_settings.get("monitored") else (0 if import_settings.get("monitored") is False else None),
                override_search_on_add=1 if import_settings.get("search_on_add") else (0 if import_settings.get("search_on_add") is False else None),
                override_season_folder=1 if import_settings.get("season_folder") else (0 if import_settings.get("season_folder") is False else None),
                schedule_cron=schedule.get("cron"),
                is_active=schedule.get("is_active", True),
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(list_obj)

        db.session.commit()
        return jsonify({"success": True, "list_id": list_obj.id})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving list: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/lists/wizard/defaults/<service>")
def wizard_defaults(service):
    """
    Get import settings defaults and available options for a service.

    Returns JSON with:
        - configured: bool - whether service is configured
        - defaults: dict - current MediaImportSettings defaults for this service
        - options: dict - available quality profiles, root folders, and tags

    Args:
        service: string (radarr or sonarr)
    """
    from listarr.models.service_config_model import MediaImportSettings

    # Validate service
    if service not in ["radarr", "sonarr"]:
        return jsonify({"error": "Invalid service"}), 400

    service_upper = service.upper()

    # Get service config (API key, URL)
    config = ServiceConfig.query.filter_by(service=service_upper).first()
    if not config or not config.api_key_encrypted:
        return jsonify({"error": f"{service.title()} not configured", "configured": False})

    # Get current defaults from MediaImportSettings
    import_settings = MediaImportSettings.query.filter_by(service=service_upper).first()

    # Decrypt API key and get base URL
    try:
        api_key = decrypt_data(config.api_key_encrypted)
    except Exception as e:
        current_app.logger.error(f"Error decrypting {service} API key: {e}", exc_info=True)
        return jsonify({"error": f"Failed to decrypt {service.title()} API key", "configured": False})

    base_url = config.base_url

    # Get available options from service API
    try:
        if service == "radarr":
            from listarr.services.radarr_service import get_quality_profiles, get_root_folders, get_tags
        else:
            from listarr.services.sonarr_service import get_quality_profiles, get_root_folders, get_tags

        quality_profiles = get_quality_profiles(base_url, api_key)
        root_folders = get_root_folders(base_url, api_key)
        tags = get_tags(base_url, api_key)
    except Exception as e:
        current_app.logger.error(f"Error fetching {service} options: {e}", exc_info=True)
        # Return partial data - service is configured but options fetch failed
        return jsonify({
            "configured": True,
            "error": f"Failed to fetch options from {service.title()}",
            "defaults": {
                "root_folder": import_settings.root_folder if import_settings else None,
                "quality_profile_id": import_settings.quality_profile_id if import_settings else None,
                "monitored": import_settings.monitored if import_settings else True,
                "search_on_add": import_settings.search_on_add if import_settings else True,
                "tag_id": import_settings.default_tag_id if import_settings else None,
            },
            "options": {
                "quality_profiles": [],
                "root_folders": [],
                "tags": [],
            }
        })

    # Season folder default - only relevant for Sonarr
    season_folder_default = True  # Sonarr default
    if import_settings and hasattr(import_settings, 'season_folder') and import_settings.season_folder is not None:
        season_folder_default = import_settings.season_folder

    return jsonify({
        "configured": True,
        "defaults": {
            "root_folder": import_settings.root_folder if import_settings else None,
            "quality_profile_id": import_settings.quality_profile_id if import_settings else None,
            "monitored": import_settings.monitored if import_settings else True,
            "search_on_add": import_settings.search_on_add if import_settings else True,
            "tag_id": import_settings.default_tag_id if import_settings else None,
            "season_folder": season_folder_default if service == "sonarr" else None,
        },
        "options": {
            "quality_profiles": [{"id": p["id"], "name": p["name"]} for p in quality_profiles],
            "root_folders": [{"path": f["path"], "id": f.get("id")} for f in root_folders],
            "tags": [{"id": t["id"], "label": t["label"]} for t in tags],
        }
    })
