from datetime import datetime, timezone
from urllib.parse import urlparse

from cryptography.fernet import InvalidToken
from flask import (
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from requests.exceptions import RequestException
from sqlalchemy.exc import IntegrityError, OperationalError

from listarr import db
from listarr.forms.auth_forms import ChangePasswordForm
from listarr.forms.settings_forms import REGION_CHOICES
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
from listarr.services.tmdb_service import validate_tmdb_api_key

# ---------------------------------------------------------------------------
# Helpers (TMDB)
# ---------------------------------------------------------------------------


def _test_and_update_tmdb_status(api_key):
    """Test TMDB API key and update database with results."""
    test_result = validate_tmdb_api_key(api_key)
    test_timestamp = datetime.now(timezone.utc)
    test_status = "success" if test_result else "failed"

    try:
        tmdb_service = ServiceConfig.query.filter_by(service="TMDB").first()
        if tmdb_service:
            tmdb_service.last_tested_at = test_timestamp
            tmdb_service.last_test_status = test_status
            db.session.commit()
    except OperationalError as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating TMDB test status: {e}", exc_info=True)

    return test_result, test_timestamp, test_status


# ---------------------------------------------------------------------------
# Helpers (service config / arr services)
# ---------------------------------------------------------------------------


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


def _resolve_api_key(service_name):
    """Return the stored decrypted API key for a service, or None."""
    cfg = ServiceConfig.query.filter_by(service=service_name).first()
    if cfg and cfg.api_key_encrypted:
        try:
            return decrypt_data(cfg.api_key_encrypted, instance_path=current_app.instance_path)
        except (ValueError, InvalidToken):
            return None
    return None


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


# ---------------------------------------------------------------------------
# Redirects
# ---------------------------------------------------------------------------


@bp.route("/config", methods=["GET"])
def config_redirect():
    """301 redirect to /settings — /config page removed in v2."""
    return redirect(url_for("main.settings_page"), code=301)


# ---------------------------------------------------------------------------
# Settings page (stub — Phase 3 implements real forms)
# ---------------------------------------------------------------------------


@bp.route("/settings")
@login_required
def settings_page():
    """Settings page with per-service configuration state."""

    def _service_state(service_name):
        cfg = ServiceConfig.query.filter_by(service=service_name).first()
        if not cfg or not cfg.api_key_encrypted:
            return {
                "configured": False,
                "base_url": None,
                "key_last4": None,
                "last_tested_at": None,
                "last_test_status": None,
            }
        try:
            key = decrypt_data(cfg.api_key_encrypted, instance_path=current_app.instance_path)
            key_last4 = key[-4:] if len(key) >= 4 else key
        except (ValueError, InvalidToken):
            key_last4 = "????"
        return {
            "configured": True,
            "base_url": cfg.base_url,
            "key_last4": key_last4,
            "last_tested_at": cfg.last_tested_at,
            "last_test_status": cfg.last_test_status,
        }

    tmdb_cfg = ServiceConfig.query.filter_by(service="TMDB").first()
    return render_template(
        "settings.html",
        radarr=_service_state("RADARR"),
        sonarr=_service_state("SONARR"),
        tmdb=_service_state("TMDB"),
        tmdb_region=tmdb_cfg.tmdb_region if tmdb_cfg else None,
        region_choices=REGION_CHOICES,
        change_password_form=ChangePasswordForm(),
    )


# ---------------------------------------------------------------------------
# Connection save endpoints (AJAX, JSON)
# ---------------------------------------------------------------------------


@bp.route("/api/settings/<service>/connection", methods=["POST"])
@login_required
def save_service_connection(service):
    """Save Radarr or Sonarr connection credentials."""
    service_upper = service.upper()
    if service_upper not in ("RADARR", "SONARR"):
        return jsonify({"success": False, "message": "Invalid service. Must be 'radarr' or 'sonarr'."}), 400

    data = request.json or {}
    base_url = (data.get("base_url") or "").strip()
    api_key = (data.get("api_key") or "").strip()
    force_save = data.get("force_save", False)

    if not base_url:
        return jsonify({"success": False, "message": "URL and API key are required."}), 400

    if not api_key:
        api_key = _resolve_api_key(service_upper) or ""
        if not api_key:
            return jsonify({"success": False, "message": "API key is required."}), 400

    if not _is_valid_url(base_url):
        return jsonify({"success": False, "message": "Invalid URL format. Please enter a valid URL."}), 400

    label = service_upper.capitalize()
    test_timestamp = None
    test_status = None

    if not force_save:
        test_result, test_timestamp, test_status = _test_and_update_service_status(service_upper, base_url, api_key)
        if not test_result:
            return jsonify(
                {
                    "success": False,
                    "test_failed": True,
                    "message": "Connection test failed. Save anyway?",
                }
            )

    try:
        enc_key = encrypt_data(api_key, instance_path=current_app.instance_path)
        service_config = ServiceConfig.query.filter_by(service=service_upper).first()

        if not service_config:
            service_config = ServiceConfig(
                service=service_upper,
                base_url=base_url,
                api_key_encrypted=enc_key,
                last_tested_at=test_timestamp,
                last_test_status=test_status,
            )
            db.session.add(service_config)
        else:
            service_config.base_url = base_url
            service_config.api_key_encrypted = enc_key
            service_config.last_tested_at = test_timestamp
            service_config.last_test_status = test_status

        db.session.commit()
        return jsonify({"success": True, "message": f"{label} connection saved.", "key_last4": api_key[-4:]})
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving {service_upper} configuration: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to save configuration. Please try again."}), 500


@bp.route("/api/settings/tmdb", methods=["POST"])
@login_required
def save_tmdb_settings():
    """Save TMDB API key and region."""
    data = request.json or {}
    api_key = (data.get("api_key") or "").strip()
    region = (data.get("region") or "").strip()
    force_save = data.get("force_save", False)

    if not api_key:
        api_key = _resolve_api_key("TMDB") or ""
        if not api_key:
            return jsonify({"success": False, "message": "API key is required."}), 400

    test_timestamp = None
    test_status = None

    if not force_save:
        test_result, test_timestamp, test_status = _test_and_update_tmdb_status(api_key)
        if not test_result:
            return jsonify(
                {
                    "success": False,
                    "test_failed": True,
                    "message": "Connection test failed. Save anyway?",
                }
            )

    try:
        enc_key = encrypt_data(api_key, instance_path=current_app.instance_path)
        tmdb_config = ServiceConfig.query.filter_by(service="TMDB").first()

        if not tmdb_config:
            tmdb_config = ServiceConfig(
                service="TMDB",
                api_key_encrypted=enc_key,
                tmdb_region=region or None,
                last_tested_at=test_timestamp,
                last_test_status=test_status,
            )
            db.session.add(tmdb_config)
        else:
            tmdb_config.api_key_encrypted = enc_key
            tmdb_config.tmdb_region = region or None
            tmdb_config.last_tested_at = test_timestamp
            tmdb_config.last_test_status = test_status

        db.session.commit()
        return jsonify({"success": True, "message": "TMDB settings saved.", "key_last4": api_key[-4:]})
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving TMDB configuration: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to save configuration. Please try again."}), 500


# ---------------------------------------------------------------------------
# TMDB endpoints
# ---------------------------------------------------------------------------


@bp.route("/settings/test_tmdb_api", methods=["POST"])
@login_required
def test_tmdb_api():
    api_key = (request.json.get("api_key") or "").strip()
    if not api_key:
        api_key = _resolve_api_key("TMDB") or ""
        if not api_key:
            return jsonify({"success": False, "message": "API key cannot be empty."})

    test_result, test_timestamp, test_status = _test_and_update_tmdb_status(api_key)

    return jsonify(
        {
            "success": test_result,
            "message": "TMDB API Key is valid." if test_result else "Invalid TMDB API Key.",
            "timestamp": test_timestamp.isoformat(),
        }
    )


# ---------------------------------------------------------------------------
# Account endpoint
# ---------------------------------------------------------------------------


@bp.route("/settings/change-password", methods=["POST"])
@login_required
def change_password():
    """AJAX endpoint for password change."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            return jsonify({"success": False, "message": "Current password is incorrect"}), 400

        current_user.set_password(form.new_password.data)
        db.session.commit()
        return jsonify({"success": True, "message": "Password changed successfully"})

    errors = []
    for field, field_errors in form.errors.items():
        for error in field_errors:
            errors.append(error)
    return jsonify({"success": False, "message": errors[0] if errors else "Validation failed"}), 400


# ---------------------------------------------------------------------------
# Config API handlers (migrated from config_routes.py, URLs at /api/settings/*)
# ---------------------------------------------------------------------------


@bp.route("/api/settings/test_radarr_api", methods=["POST"])
@login_required
def test_radarr_api():
    base_url = request.json.get("base_url", "")
    api_key = (request.json.get("api_key") or "").strip()
    if not api_key:
        api_key = _resolve_api_key("RADARR") or ""
    return _test_service_api("RADARR", base_url, api_key)


@bp.route("/api/settings/test_sonarr_api", methods=["POST"])
@login_required
def test_sonarr_api():
    base_url = request.json.get("base_url", "")
    api_key = (request.json.get("api_key") or "").strip()
    if not api_key:
        api_key = _resolve_api_key("SONARR") or ""
    return _test_service_api("SONARR", base_url, api_key)


@bp.route("/api/settings/<service>/quality-profiles", methods=["GET"])
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


@bp.route("/api/settings/<service>/root-folders", methods=["GET"])
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


@bp.route("/api/settings/<service>/import-settings", methods=["GET"])
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


@bp.route("/api/settings/<service>/import-settings", methods=["POST"])
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
