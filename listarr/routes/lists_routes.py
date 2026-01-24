from flask import render_template, flash, request, redirect, url_for, current_app, jsonify
from datetime import datetime, timezone
from listarr.routes import bp
from listarr import csrf
from listarr.models.lists_model import List
from listarr.models.service_config_model import ServiceConfig
from listarr.forms.lists_forms import ListForm
from listarr.services.crypto_utils import decrypt_data
from listarr.services.import_service import import_list
from listarr.services.tmdb_cache import (
    get_trending_movies_cached,
    get_trending_tv_cached,
    get_popular_movies_cached,
    get_popular_tv_cached,
    discover_movies_cached,
    discover_tv_cached,
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
    service_type = list_obj.target_service  # RADARR or SONARR

    # Get service config for fetching options
    config = ServiceConfig.query.filter_by(service=service_type).first()

    # Initialize form
    form = ListForm()

    # Build choices for dropdowns (quality profile and root folder only, not tags)
    quality_profile_choices = [("", "Use Default")]
    root_folder_choices = [("", "Use Default")]

    if config and config.api_key_encrypted:
        try:
            api_key = decrypt_data(config.api_key_encrypted)
            base_url = config.base_url

            # Import correct service module
            if service_type == "RADARR":
                from listarr.services.radarr_service import get_quality_profiles, get_root_folders, get_tags
            else:
                from listarr.services.sonarr_service import get_quality_profiles, get_root_folders, get_tags

            # Fetch options from service API
            quality_profiles = get_quality_profiles(base_url, api_key)
            root_folders = get_root_folders(base_url, api_key)
            tags = get_tags(base_url, api_key)

            # Build choices
            quality_profile_choices.extend(
                [(str(p["id"]), p["name"]) for p in quality_profiles]
            )
            root_folder_choices.extend(
                [(f["path"], f["path"]) for f in root_folders]
            )
        except Exception as e:
            current_app.logger.error(f"Error fetching {service_type} options: {e}", exc_info=True)
            flash(f"Could not load {service_type} options. Some dropdowns may be empty.", "warning")

    # Set form choices
    form.override_quality_profile.choices = quality_profile_choices
    form.override_root_folder.choices = root_folder_choices

    if request.method == "POST" and form.validate_on_submit():
        try:
            list_obj.name = form.name.data
            list_obj.is_active = form.is_active.data
            list_obj.schedule_cron = form.schedule_cron.data or None

            # Handle quality profile (store as int or None)
            qp_value = form.override_quality_profile.data
            list_obj.override_quality_profile = int(qp_value) if qp_value else None

            # Handle root folder (store as string or None)
            list_obj.override_root_folder = form.override_root_folder.data or None

            # Handle tag - use create_or_get_tag_id to normalize and create if needed
            tag_name = form.override_tag.data
            if tag_name and tag_name.strip():
                if config and config.api_key_encrypted:
                    api_key = decrypt_data(config.api_key_encrypted)
                    base_url = config.base_url

                    # Import correct service module
                    if service_type == "RADARR":
                        from listarr.services.radarr_service import create_or_get_tag_id
                    else:
                        from listarr.services.sonarr_service import create_or_get_tag_id

                    list_obj.override_tag_id = create_or_get_tag_id(base_url, api_key, tag_name.strip())
                else:
                    flash("Service not configured. Cannot create/verify tag.", "warning")
                    list_obj.override_tag_id = None
            else:
                list_obj.override_tag_id = None

            # Handle tri-state fields (store as 1, 0, or None)
            monitored_value = form.override_monitored.data
            list_obj.override_monitored = int(monitored_value) if monitored_value else None

            search_value = form.override_search_on_add.data
            list_obj.override_search_on_add = int(search_value) if search_value else None

            season_value = form.override_season_folder.data
            list_obj.override_season_folder = int(season_value) if season_value else None

            db.session.commit()
            flash(f"List '{list_obj.name}' updated successfully!", "success")
            return redirect(url_for("main.lists_page"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating list: {e}", exc_info=True)
            flash("Error updating list. Please try again.", "error")
    else:
        # Pre-populate form with current values (GET request)
        form.name.data = list_obj.name
        form.is_active.data = list_obj.is_active
        form.schedule_cron.data = list_obj.schedule_cron or ""

        # Convert stored values to form values
        form.override_quality_profile.data = str(list_obj.override_quality_profile) if list_obj.override_quality_profile else ""
        form.override_root_folder.data = list_obj.override_root_folder or ""

        # Convert tag_id to tag name for display
        if list_obj.override_tag_id and config and config.api_key_encrypted:
            try:
                api_key = decrypt_data(config.api_key_encrypted)
                base_url = config.base_url

                # Import correct service module
                if service_type == "RADARR":
                    from listarr.services.radarr_service import get_tags
                else:
                    from listarr.services.sonarr_service import get_tags

                tags = get_tags(base_url, api_key)
                tag = next((t for t in tags if t["id"] == list_obj.override_tag_id), None)
                form.override_tag.data = tag["label"] if tag else ""
            except Exception as e:
                current_app.logger.error(f"Error fetching tag name: {e}", exc_info=True)
                form.override_tag.data = ""
        else:
            form.override_tag.data = ""

        # Tri-state fields: None -> "", 1 -> "1", 0 -> "0"
        form.override_monitored.data = str(list_obj.override_monitored) if list_obj.override_monitored is not None else ""
        form.override_search_on_add.data = str(list_obj.override_search_on_add) if list_obj.override_search_on_add is not None else ""
        form.override_season_folder.data = str(list_obj.override_season_folder) if list_obj.override_season_folder is not None else ""

    return render_template("edit_list.html", form=form, list=list_obj, service_type=service_type)

@bp.route("/lists/delete/<int:list_id>", methods=["POST"])
def delete_list(list_id):
    """
    Delete a list via AJAX.

    Returns JSON:
        success: bool
        message: string
    """
    list_obj = List.query.get_or_404(list_id)

    try:
        list_name = list_obj.name
        db.session.delete(list_obj)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"List '{list_name}' deleted successfully!"
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting list: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Error deleting list. Please try again."
        }), 500

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

        # Get tag name from tag_id
        tag_name = None
        if list_obj.override_tag_id:
            config = ServiceConfig.query.filter_by(service=list_obj.target_service).first()
            if config and config.api_key_encrypted:
                try:
                    api_key = decrypt_data(config.api_key_encrypted)
                    base_url = config.base_url

                    # Import correct service module
                    if list_obj.target_service == "RADARR":
                        from listarr.services.radarr_service import get_tags
                    else:
                        from listarr.services.sonarr_service import get_tags

                    tags = get_tags(base_url, api_key)
                    tag = next((t for t in tags if t["id"] == list_obj.override_tag_id), None)
                    tag_name = tag["label"] if tag else None
                except Exception as e:
                    current_app.logger.error(f"Error fetching tag name for list wizard: {e}", exc_info=True)

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
                "tag": tag_name,
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
        filters: object (genres_include, genres_exclude, language, year_min, year_max, rating_min)

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
            items = get_trending_movies_cached(api_key)
        elif preset == "trending_tv":
            items = get_trending_tv_cached(api_key)
        elif preset == "popular_movies":
            items = get_popular_movies_cached(api_key)
        elif preset == "popular_tv":
            items = get_popular_tv_cached(api_key)
        else:
            # Custom discovery with filters
            tmdb_filters = {}

            # Genre include filter (new format)
            if filters.get("genres_include"):
                tmdb_filters["with_genres"] = ",".join(map(str, filters["genres_include"]))
            # Backward compatibility for old format
            elif filters.get("genre_ids"):
                tmdb_filters["with_genres"] = ",".join(map(str, filters["genre_ids"]))

            # Genre exclude filter (new format)
            if filters.get("genres_exclude"):
                tmdb_filters["without_genres"] = ",".join(map(str, filters["genres_exclude"]))

            # Language filter
            if filters.get("language"):
                tmdb_filters["with_original_language"] = filters["language"]

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
                items = discover_movies_cached(api_key, tmdb_filters)
            else:
                items = discover_tv_cached(api_key, tmdb_filters)

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
        filters: object (genres_include, genres_exclude, language, year_min, year_max, rating_min, limit)
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

    # Build filters_json with new format
    filters_json = {
        "genres_include": filters.get("genres_include", []),
        "genres_exclude": filters.get("genres_exclude", []),
        "language": filters.get("language"),
        "year_min": filters.get("year_min"),
        "year_max": filters.get("year_max"),
        "rating_min": filters.get("rating_min"),
    }

    # Handle tag - create or get tag_id from tag name
    tag_id = None
    tag_name = import_settings.get("tag")
    if tag_name and tag_name.strip():
        # Get service config
        service_upper = service.upper()
        config = ServiceConfig.query.filter_by(service=service_upper).first()
        if config and config.api_key_encrypted:
            try:
                api_key = decrypt_data(config.api_key_encrypted)
                base_url = config.base_url

                # Import correct service module
                if service == "radarr":
                    from listarr.services.radarr_service import create_or_get_tag_id
                else:
                    from listarr.services.sonarr_service import create_or_get_tag_id

                tag_id = create_or_get_tag_id(base_url, api_key, tag_name.strip())
            except Exception as e:
                current_app.logger.error(f"Error creating/getting tag: {e}", exc_info=True)
                return jsonify({"success": False, "error": f"Failed to create/get tag: {str(e)}"}), 500

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
            list_obj.override_tag_id = tag_id
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
                override_tag_id=tag_id,
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
        - defaults: dict - current MediaImportSettings defaults for this service (includes tag_id for default tag)
        - options: dict - available quality profiles, root folders, and tags (tags used to resolve default tag name)

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


@bp.route("/lists/debug/cache-stats", methods=["GET"])
def cache_stats():
    """
    Debug endpoint for TMDB cache statistics.

    Returns JSON with cache sizes, max sizes, and TTLs for each cache type.
    Intended for development/debugging - shows cache hit/miss effectiveness.
    """
    from listarr.services.tmdb_cache import get_cache_stats
    return jsonify(get_cache_stats())


@bp.route("/lists/<int:list_id>/run", methods=["POST"])
@csrf.exempt
def run_list_import(list_id):
    """
    Manually trigger import for a list.
    Returns JSON with import results.

    Returns:
        JSON response with:
        - success: bool
        - list_id: int
        - list_name: string
        - result: ImportResult.to_dict()
        OR
        - success: false
        - error: string
    """
    # Fetch list by ID
    list_obj = List.query.get(list_id)
    if not list_obj:
        return jsonify({
            "success": False,
            "error": f"List with ID {list_id} not found"
        }), 404

    # Check if list is active
    if not list_obj.is_active:
        return jsonify({
            "success": False,
            "error": f"List '{list_obj.name}' is not active"
        }), 400

    try:
        # Run the import
        result = import_list(list_id)

        # Update last_run_at timestamp
        list_obj.last_run_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "list_id": list_id,
            "list_name": list_obj.name,
            "result": result.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Error running import for list {list_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
