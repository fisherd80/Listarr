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
        list_id: int (for edit mode - future use)
    """
    preset = request.args.get("preset")
    service = request.args.get("service")
    list_id = request.args.get("list_id", type=int)

    # Determine wizard mode based on preset
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
    # Convert to list first - tmdbv3api returns AsObj which doesn't support slicing
    items_list = list(items) if items else []
    preview_items = []
    for item in items_list[:5]:
        # Handle both movie and TV show objects
        title = getattr(item, "title", None) or getattr(item, "name", None) or "Unknown"
        release_date = getattr(item, "release_date", None) or getattr(item, "first_air_date", None) or ""
        year = release_date[:4] if release_date else None
        vote_average = getattr(item, "vote_average", None)

        preview_items.append({
            "id": getattr(item, "id", None),
            "title": title,
            "year": year,
            "rating": round(vote_average, 1) if vote_average else None,
        })

    return jsonify({"items": preview_items})
