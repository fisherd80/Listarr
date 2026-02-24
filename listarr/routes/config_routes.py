from datetime import datetime, timezone
from urllib.parse import urlparse

from cryptography.fernet import InvalidToken
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from requests.exceptions import RequestException
from sqlalchemy.exc import IntegrityError, OperationalError

from listarr import db
from listarr.forms.config_forms import RadarrAPIForm, SonarrAPIForm
from listarr.models.service_config_model import MediaImportSettings, ServiceConfig
from listarr.routes import bp
from listarr.services.arr_service import (
    create_or_get_tag_id,
    get_quality_profiles,
    get_root_folders,
    get_tags,
    validate_api_key,
)
from listarr.services.crypto_utils import decrypt_data, encrypt_data
from listarr.services.dashboard_cache import refresh_dashboard_cache


def _is_valid_url(url):
    """Check if url has valid scheme and netloc."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except (ValueError, TypeError):
        return False


def _test_and_update_service_status(service, base_url, api_key):
    """Test API connection and update database with results."""
    test_result = validate_api_key(base_url, api_key)
    test_timestamp = datetime.now(timezone.utc)
    test_status = "success" if test_result else "failed"

    try:
        service_config = ServiceConfig.query.filter_by(service=service).first()
        if service_config:
            service_config.last_tested_at = test_timestamp
            service_config.last_test_status = test_status
            db.session.commit()
    except OperationalError as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating {service} test status: {e}", exc_info=True)

    return test_result, test_timestamp, test_status


def _save_service_config(service, form_url_field, form_api_field):
    """Save service API config from form POST data."""
    service_upper = service.upper()
    url_data = form_url_field.data.strip()
    api_data = form_api_field.data.strip()

    if not url_data or not api_data:
        flash("URL and API Key cannot be empty.", "warning")
        return

    if not _is_valid_url(url_data):
        flash("Invalid URL format. Please enter a valid URL.", "warning")
        return

    test_result, test_timestamp, test_status = _test_and_update_service_status(service_upper, url_data, api_data)

    if not test_result:
        flash(f"Invalid {service} URL or API Key. Please check and try again.", "error")
        return

    try:
        enc_key = encrypt_data(api_data, instance_path=current_app.instance_path)
        service_config = ServiceConfig.query.filter_by(service=service_upper).first()

        if not service_config:
            service_config = ServiceConfig(
                service=service_upper,
                base_url=url_data,
                api_key_encrypted=enc_key,
                last_tested_at=test_timestamp,
                last_test_status=test_status,
            )
            db.session.add(service_config)
        else:
            service_config.base_url = url_data
            service_config.api_key_encrypted = enc_key
            service_config.last_tested_at = test_timestamp
            service_config.last_test_status = test_status

        db.session.commit()

        # Refresh dashboard cache to reflect newly configured service
        try:
            refresh_dashboard_cache()
            current_app.logger.info(f"Dashboard cache refreshed after {service} configuration")
        except (OperationalError, RequestException) as cache_error:
            current_app.logger.error(
                f"Error refreshing dashboard cache after {service} save: {cache_error}", exc_info=True
            )
            # Don't fail the save if cache refresh fails, just log it

        flash(f"{service} URL and API Key saved successfully.", "success")
    except (IntegrityError, OperationalError, ValueError, RuntimeError, OSError) as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving {service} configuration: {e}", exc_info=True)
        flash(f"Failed to save {service} configuration. Please try again.", "error")


@bp.route("/config", methods=["GET", "POST"])
@login_required
def config_page():
    radarr_api_form = RadarrAPIForm()
    sonarr_api_form = SonarrAPIForm()

    if request.method == "POST":
        if "save_radarr_api" in request.form:
            _save_service_config("Radarr", radarr_api_form.radarr_url, radarr_api_form.radarr_api)

        if "save_sonarr_api" in request.form:
            _save_service_config("Sonarr", sonarr_api_form.sonarr_url, sonarr_api_form.sonarr_api)

        return redirect(url_for("main.config_page"))

    # Populate Radarr form with existing key for GET requests
    radarr_existing = ServiceConfig.query.filter_by(service="RADARR").first()
    if radarr_existing and radarr_existing.api_key_encrypted:
        radarr_api_form.radarr_url.data = radarr_existing.base_url
        try:
            radarr_api_form.radarr_api.data = decrypt_data(
                radarr_existing.api_key_encrypted,
                instance_path=current_app.instance_path,
            )
        except (ValueError, InvalidToken) as e:
            current_app.logger.error(f"Error decrypting Radarr API key: {e}", exc_info=True)
            radarr_api_form.radarr_api.data = ""
            flash("Unable to decrypt stored Radarr API key. Please re-enter your Radarr API key.", "warning")

    last_radarr_test_at = radarr_existing.last_tested_at if radarr_existing else None
    last_radarr_test_status = radarr_existing.last_test_status if radarr_existing else None
    radarr_configured = bool(radarr_existing and radarr_existing.base_url and radarr_existing.api_key_encrypted)

    # Populate Sonarr form with existing key for GET requests
    sonarr_existing = ServiceConfig.query.filter_by(service="SONARR").first()
    if sonarr_existing and sonarr_existing.api_key_encrypted:
        sonarr_api_form.sonarr_url.data = sonarr_existing.base_url
        try:
            sonarr_api_form.sonarr_api.data = decrypt_data(
                sonarr_existing.api_key_encrypted,
                instance_path=current_app.instance_path,
            )
        except (ValueError, InvalidToken) as e:
            current_app.logger.error(f"Error decrypting Sonarr API key: {e}", exc_info=True)
            sonarr_api_form.sonarr_api.data = ""
            flash("Unable to decrypt stored Sonarr API key. Please re-enter your Sonarr API key.", "warning")

    last_sonarr_test_at = sonarr_existing.last_tested_at if sonarr_existing else None
    last_sonarr_test_status = sonarr_existing.last_test_status if sonarr_existing else None
    sonarr_configured = bool(sonarr_existing and sonarr_existing.base_url and sonarr_existing.api_key_encrypted)

    return render_template(
        "config.html",
        radarr_api_form=radarr_api_form,
        last_radarr_test_at=last_radarr_test_at,
        last_radarr_test_status=last_radarr_test_status,
        radarr_configured=radarr_configured,
        sonarr_api_form=sonarr_api_form,
        last_sonarr_test_at=last_sonarr_test_at,
        last_sonarr_test_status=last_sonarr_test_status,
        sonarr_configured=sonarr_configured,
    )


def _test_service_api(service_upper, base_url, api_key):
    """Handle test connection logic for any service."""
    if not base_url or not api_key:
        return jsonify({"success": False, "message": "URL and API key cannot be empty."})

    if not _is_valid_url(base_url):
        return jsonify({"success": False, "message": "Invalid URL format. Please enter a valid URL."})

    test_result, test_timestamp, test_status = _test_and_update_service_status(service_upper, base_url, api_key)
    label = "Radarr" if service_upper == "RADARR" else "Sonarr"

    return jsonify(
        {
            "success": test_result,
            "message": f"{label} connection successful." if test_result else f"Invalid {label} URL or API Key.",
            "timestamp": test_timestamp.isoformat(),
        }
    )


@bp.route("/config/test_radarr_api", methods=["POST"])
@login_required
def test_radarr_api():
    return _test_service_api("RADARR", request.json.get("base_url", ""), request.json.get("api_key", ""))


@bp.route("/config/test_sonarr_api", methods=["POST"])
@login_required
def test_sonarr_api():
    return _test_service_api("SONARR", request.json.get("base_url", ""), request.json.get("api_key", ""))


@bp.route("/config/<service>/quality-profiles", methods=["GET"])
@login_required
def fetch_quality_profiles_route(service):
    """Fetch quality profiles from configured service."""
    service_upper = service.upper()
    if service_upper not in ("RADARR", "SONARR"):
        return jsonify({"success": False, "message": "Invalid service."}), 400

    service_config = ServiceConfig.query.filter_by(service=service_upper).first()
    if not service_config or not service_config.api_key_encrypted:
        return jsonify({"success": False, "message": f"{service.capitalize()} not configured."}), 400

    try:
        api_key = decrypt_data(service_config.api_key_encrypted, instance_path=current_app.instance_path)
        profiles = get_quality_profiles(service_config.base_url, api_key)

        if not profiles:
            return jsonify({"success": False, "message": "Failed to fetch quality profiles."}), 500

        return jsonify({"success": True, "profiles": profiles})
    except ValueError as e:
        current_app.logger.error(f"Decryption error fetching {service} quality profiles: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to decrypt API key."}), 500
    except RequestException as e:
        current_app.logger.error(f"Error fetching {service} quality profiles: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to fetch quality profiles."}), 500


@bp.route("/config/<service>/root-folders", methods=["GET"])
@login_required
def fetch_root_folders_route(service):
    """Fetch root folders from configured service."""
    service_upper = service.upper()
    if service_upper not in ("RADARR", "SONARR"):
        return jsonify({"success": False, "message": "Invalid service."}), 400

    service_config = ServiceConfig.query.filter_by(service=service_upper).first()
    if not service_config or not service_config.api_key_encrypted:
        return jsonify({"success": False, "message": f"{service.capitalize()} not configured."}), 400

    try:
        api_key = decrypt_data(service_config.api_key_encrypted, instance_path=current_app.instance_path)
        folders = get_root_folders(service_config.base_url, api_key)

        if not folders:
            return jsonify({"success": False, "message": "Failed to fetch root folders."}), 500

        return jsonify({"success": True, "folders": folders})
    except ValueError as e:
        current_app.logger.error(f"Decryption error fetching {service} root folders: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to decrypt API key."}), 500
    except RequestException as e:
        current_app.logger.error(f"Error fetching {service} root folders: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to fetch root folders."}), 500


@bp.route("/config/<service>/import-settings", methods=["GET"])
@login_required
def fetch_import_settings(service):
    """Fetch saved import settings for service from database."""
    service_upper = service.upper()
    if service_upper not in ("RADARR", "SONARR"):
        return jsonify({"success": False, "message": "Invalid service."}), 400

    import_settings = MediaImportSettings.query.filter_by(service=service_upper).first()
    if not import_settings:
        return jsonify({"success": True, "settings": None})

    service_config = ServiceConfig.query.filter_by(service=service_upper).first()
    root_folder_id = None
    tag_label = None

    if service_config and service_config.api_key_encrypted:
        try:
            api_key = decrypt_data(service_config.api_key_encrypted, instance_path=current_app.instance_path)
            base_url = service_config.base_url

            if import_settings.root_folder:
                folders = get_root_folders(base_url, api_key)
                for folder in folders:
                    if folder.get("path") == import_settings.root_folder:
                        root_folder_id = folder.get("id")
                        break

            if import_settings.default_tag_id:
                tags = get_tags(base_url, api_key)
                for tag in tags:
                    if tag.get("id") == import_settings.default_tag_id:
                        tag_label = tag.get("label")
                        break
        except RequestException as e:
            current_app.logger.error(f"Error fetching {service} data: {e}", exc_info=True)

    settings_dict = {
        "root_folder_id": root_folder_id,
        "quality_profile_id": import_settings.quality_profile_id,
        "monitored": import_settings.monitored,
        "search_on_add": import_settings.search_on_add,
        "tag_label": tag_label,
    }

    if service_upper == "SONARR":
        settings_dict["season_folder"] = import_settings.season_folder

    return jsonify({"success": True, "settings": settings_dict})


@bp.route("/config/<service>/import-settings", methods=["POST"])
@login_required
def save_import_settings(service):
    """Save import settings for service to database."""
    service_upper = service.upper()
    if service_upper not in ("RADARR", "SONARR"):
        return jsonify({"success": False, "message": "Invalid service."}), 400

    data = request.json
    root_folder_id = data.get("root_folder_id")
    quality_profile_id = data.get("quality_profile_id")
    monitored = data.get("monitored")
    search_on_add = data.get("search_on_add")
    tag_label = data.get("tag_label")

    if not root_folder_id or not quality_profile_id:
        return jsonify({"success": False, "message": "Root Folder and Quality Profile are required."}), 400

    if monitored is None:
        return jsonify({"success": False, "message": "Monitor option is required."}), 400

    if search_on_add is None:
        return jsonify({"success": False, "message": "Search on Add option is required."}), 400

    season_folder = None
    if service_upper == "SONARR":
        season_folder = data.get("season_folder")
        if season_folder is None:
            return jsonify({"success": False, "message": "Season Folder option is required."}), 400

    service_config = ServiceConfig.query.filter_by(service=service_upper).first()
    if not service_config or not service_config.api_key_encrypted:
        return jsonify({"success": False, "message": f"{service.capitalize()} not configured."}), 400

    try:
        api_key = decrypt_data(service_config.api_key_encrypted, instance_path=current_app.instance_path)
        base_url = service_config.base_url
    except (ValueError, InvalidToken) as e:
        current_app.logger.error(f"Error decrypting {service} API key: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to decrypt API key"}), 500

    try:
        folders = get_root_folders(base_url, api_key)
        root_folder_path = None
        for folder in folders:
            if str(folder.get("id")) == str(root_folder_id):
                root_folder_path = folder.get("path")
                break

        if not root_folder_path:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Root folder ID {root_folder_id} not found in {service.capitalize()}",
                    }
                ),
                400,
            )
    except RequestException as e:
        current_app.logger.error(f"Error fetching root folders from {service}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to fetch root folders"}), 500

    tag_id = None
    if tag_label and tag_label.strip():
        try:
            tag_id = create_or_get_tag_id(base_url, api_key, tag_label.strip())
            if tag_id is None:
                return (
                    jsonify({"success": False, "message": f"Failed to create/find tag in {service.capitalize()}"}),
                    500,
                )
        except RequestException as e:
            current_app.logger.error(f"Error handling tag for {service}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Failed to process tag"}), 500

    try:
        import_settings = MediaImportSettings.query.filter_by(service=service_upper).first()

        if import_settings:
            import_settings.root_folder = root_folder_path
            import_settings.quality_profile_id = int(quality_profile_id)
            import_settings.monitored = bool(monitored)
            import_settings.search_on_add = bool(search_on_add)
            import_settings.default_tag_id = tag_id
            if service_upper == "SONARR":
                import_settings.season_folder = bool(season_folder)
        else:
            import_settings = MediaImportSettings(
                service=service_upper,
                root_folder=root_folder_path,
                quality_profile_id=int(quality_profile_id),
                monitored=bool(monitored),
                search_on_add=bool(search_on_add),
                default_tag_id=tag_id,
            )
            if service_upper == "SONARR":
                import_settings.season_folder = bool(season_folder)
            db.session.add(import_settings)

        db.session.commit()

        return jsonify({"success": True, "message": f"{service.capitalize()} import settings saved successfully."})
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving import settings: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to save settings. Please try again."}), 500
