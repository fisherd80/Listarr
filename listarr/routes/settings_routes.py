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
from listarr.models.app_config_model import get_app_config
from listarr.models.lists_model import List
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
from listarr.services.sonarr_service import MONITOR_MODE_TOKENS, normalize_monitor_mode
from listarr.services.tmdb_service import validate_tmdb_api_key
from listarr.utils.time_utils import (
    coerce_zone,
    get_app_timezone,
    get_app_timezone_state,
    invalidate_app_timezone_memo,
)
from listarr.utils.timezones import CURATED_TIMEZONES, curated_zone_keys

TIMEZONE_INVALID_MESSAGE = "Unknown or invalid timezone. Nothing was saved."

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
                "api_key": None,
                "last_tested_at": None,
                "last_test_status": None,
            }
        try:
            key = decrypt_data(cfg.api_key_encrypted, instance_path=current_app.instance_path)
        except (ValueError, InvalidToken):
            key = None
        return {
            "configured": True,
            "base_url": cfg.base_url,
            "api_key": key,
            "last_tested_at": cfg.last_tested_at,
            "last_test_status": cfg.last_test_status,
        }

    tmdb_cfg = ServiceConfig.query.filter_by(service="TMDB").first()
    # IN-04: one timezone object in the context. The template reads tz.configured /
    # tz.fallback so the two halves can no longer drift apart.
    tz_state = get_app_timezone_state()
    configured_tz = tz_state["configured"]
    # IN-05: 24-hour and locale-independent. %p renders empty under some locales, and
    # the JS preview that replaces this a second later is hour12:false.
    # IN-07: no zone label. strftime("%Z") gives the tzdb abbreviation (BST), while Intl
    # with timeZoneName:'short' gives whatever the browser locale prefers (GMT+1) — so
    # the value visibly changed one second after load, which is the flicker IN-05 set out
    # to remove. The zone is already named in the select right above this.
    server_rendered_preview = datetime.now(get_app_timezone()).strftime("%H:%M:%S")
    timezone_is_curated = not configured_tz or configured_tz in curated_zone_keys()

    return render_template(
        "settings.html",
        radarr=_service_state("RADARR"),
        sonarr=_service_state("SONARR"),
        tmdb=_service_state("TMDB"),
        tmdb_region=tmdb_cfg.tmdb_region if tmdb_cfg else None,
        region_choices=REGION_CHOICES,
        tz=tz_state,
        curated_timezones=CURATED_TIMEZONES,
        server_rendered_preview=server_rendered_preview,
        timezone_is_curated=timezone_is_curated,
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
        return jsonify({"success": True, "message": f"{label} connection saved."})
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
        return jsonify({"success": True, "message": "TMDB settings saved."})
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving TMDB configuration: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to save configuration. Please try again."}), 500


def _validate_timezone(value):
    """Return (stored_value, error). An empty string means "System default" (NULL).

    IN-01: validation is delegated to time_utils.coerce_zone so there is exactly one
    copy of the ZoneInfo-based check. coerce_zone also type-checks, so a non-string
    can no longer raise TypeError out of here.
    """
    if value == "":
        return None, None

    if coerce_zone(value) is None:
        return None, TIMEZONE_INVALID_MESSAGE

    return value, None


@bp.route("/api/settings/general", methods=["POST"])
@login_required
def save_general_settings():
    """Save application-wide settings."""
    data = request.json or {}

    # WR-02: an absent key means "no setting supplied", not "reset to System default".
    # Clearing the timezone requires an explicit empty string (or null).
    if "timezone" not in data:
        return jsonify({"success": False, "message": "No settings supplied."}), 400

    raw = data["timezone"]

    if raw is None or raw == "":
        submitted = ""
    elif not isinstance(raw, str):
        return jsonify({"success": False, "message": TIMEZONE_INVALID_MESSAGE}), 400
    else:
        submitted = raw.strip()
        # IN-06: raw is a non-empty string here, so stripping to nothing means the payload
        # was whitespace. Treating that as "clear the setting" contradicts the rule above
        # that clearing requires an explicit empty string.
        if not submitted:
            current_app.logger.info("Rejected whitespace-only application timezone")
            return jsonify({"success": False, "message": TIMEZONE_INVALID_MESSAGE}), 400

    stored, error = _validate_timezone(submitted)
    if error:
        current_app.logger.info("Rejected invalid application timezone")
        return jsonify({"success": False, "message": error}), 400

    try:
        cfg = get_app_config()
        cfg.timezone = stored
        db.session.commit()
        invalidate_app_timezone_memo()

        # WR-04: read the authoritative post-save state once. The page was rendered
        # against the *previous* zone, so the client needs the new effective zone (for
        # window.APP_TZ and every timestamp it drives) and the unresolvable flag (for the
        # fallback banner) handed back to it.
        tz_state = get_app_timezone_state()
        effective_tz = tz_state["resolved"]

        scheduler_worker = False
        reschedule_error = False
        n_ok = 0
        n_fail = 0
        # IN-03: lists this worker rescheduled (n_rescheduled) and lists another worker
        # still has to pick up (n_pending) are different facts and get different fields.
        n_pending = 0
        try:
            from listarr.services import scheduler as sched

            # WR-06: use the module's intentional predicate rather than reaching into
            # its private singleton.
            scheduler_worker = sched.is_scheduler_worker()
            if scheduler_worker:
                # WR-08: a deliberate save is a recovery action. Clear any quarantine so
                # every list gets a genuine fresh attempt and the user sees a current
                # diagnosis, rather than inheriting a verdict from an earlier zone.
                sched.reset_reschedule_state()
                n_ok, n_fail = sched.reschedule_all_lists(effective_tz)
            else:
                n_pending = List.query.filter(
                    List.schedule_cron.isnot(None),
                    List.is_active == True,  # noqa: E712
                ).count()
        except Exception as e:
            # IN-02: the timezone is saved, but rescheduling did not happen. Report that
            # explicitly instead of letting n_rescheduled == 0 read as "nothing to do".
            current_app.logger.error(f"Error rescheduling lists after timezone save: {e}", exc_info=True)
            n_ok, n_fail, n_pending = 0, 0, 0
            reschedule_error = True

        return jsonify(
            {
                "success": True,
                "message": "Timezone saved.",
                "scheduler_worker": scheduler_worker,
                "n_rescheduled": n_ok,
                "n_failed": n_fail,
                "n_pending": n_pending,
                "reschedule_error": reschedule_error,
                "effective_tz": effective_tz,
                "unresolvable": tz_state["unresolvable"],
            }
        )
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving general settings: {e}", exc_info=True)
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


@bp.route("/api/service-status", methods=["GET"])
@login_required
def service_status():
    """Return the last-known connection status for Radarr and Sonarr.

    Reads last_test_status from ServiceConfig — no live API call is made,
    so this endpoint is fast and safe to poll on every page load.

    Returns JSON::

        {
          "radarr": "success" | "failed" | null,
          "sonarr": "success" | "failed" | null
        }

    ``null`` means the service has never been tested or is not configured.
    """

    def _status_for(service_name):
        cfg = ServiceConfig.query.filter_by(service=service_name).first()
        if cfg is None:
            return None
        return cfg.last_test_status  # "success", "failed", or None

    return jsonify(
        {
            "radarr": _status_for("RADARR"),
            "sonarr": _status_for("SONARR"),
        }
    )


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
        settings_dict["monitor_mode"] = normalize_monitor_mode(import_settings.sonarr_monitor_mode)

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

    # IN-03: the browser always sends genuine JSON booleans, but a non-browser client
    # could POST the string "false", which is truthy and would (a) slip past the
    # `is None` guards and (b) persist as a non-bool. Reject anything that is not a
    # real boolean so `bool(...)` at storage time is never load-bearing.
    if not isinstance(monitored, bool):
        return jsonify({"success": False, "message": "Monitor option must be true or false."}), 400

    if not isinstance(search_on_add, bool):
        return jsonify({"success": False, "message": "Search on Add option must be true or false."}), 400

    season_folder = None
    monitor_mode = None
    if service_upper == "SONARR":
        season_folder = data.get("season_folder")
        if season_folder is None:
            return jsonify({"success": False, "message": "Season Folder option is required."}), 400

        monitor_mode = data.get("monitor_mode")
        if monitor_mode is None:
            return jsonify({"success": False, "message": "Monitor Mode option is required."}), 400
        if monitor_mode not in MONITOR_MODE_TOKENS:
            return jsonify({"success": False, "message": "Monitor Mode option is invalid."}), 400

        # D-06 reconciliation deliberately does NOT happen here. The Import Default row
        # stores the user's raw choice verbatim, exactly like the per-list override
        # (see CR-01 / lists_routes.py). resolve_import_settings applies D-06 at import
        # time; the settings API only reflects the stored choice, it never mutates it.
        # Coercing monitor_mode to "none" on save (former IN-02 fix) silently destroyed a
        # saved "All episodes" default whenever "Monitor" was toggled to No (WR-01).

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
                import_settings.sonarr_monitor_mode = monitor_mode
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
                import_settings.sonarr_monitor_mode = monitor_mode
            db.session.add(import_settings)

        db.session.commit()

        return jsonify({"success": True, "message": f"{service.capitalize()} import settings saved successfully."})
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving import settings: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to save settings. Please try again."}), 500
