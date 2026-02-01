from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from listarr import db
from listarr.forms.config_forms import RadarrAPIForm, SonarrAPIForm
from listarr.models.service_config_model import MediaImportSettings, ServiceConfig
from listarr.routes import bp
from listarr.services.crypto_utils import decrypt_data, encrypt_data
from listarr.services.radarr_service import (
    create_or_get_tag_id as radarr_create_or_get_tag_id,
)
from listarr.services.radarr_service import (
    get_quality_profiles as get_radarr_quality_profiles,
)
from listarr.services.radarr_service import get_root_folders as get_radarr_root_folders
from listarr.services.radarr_service import get_tags as get_radarr_tags
from listarr.services.radarr_service import validate_radarr_api_key
from listarr.services.sonarr_service import (
    create_or_get_tag_id as sonarr_create_or_get_tag_id,
)
from listarr.services.sonarr_service import (
    get_quality_profiles as get_sonarr_quality_profiles,
)
from listarr.services.sonarr_service import get_root_folders as get_sonarr_root_folders
from listarr.services.sonarr_service import get_tags as get_sonarr_tags
from listarr.services.sonarr_service import validate_sonarr_api_key


# ----------------------
# Helper Functions
# ----------------------
def _is_valid_url(url):
    """
    Validates if a string is a valid URL.

    Args:
        url (str): URL string to validate

    Returns:
        bool: True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def _test_and_update_radarr_status(base_url, api_key):
    """
    Tests Radarr API connection and updates the database with test results.

    Args:
        base_url (str): The Radarr base URL
        api_key (str): The Radarr API key to test

    Returns:
        tuple: (test_result: bool, timestamp: datetime, status: str)
    """
    test_result = validate_radarr_api_key(base_url, api_key)
    test_timestamp = datetime.now(timezone.utc)
    test_status = "success" if test_result else "failed"

    # Update test status in database if service config exists
    try:
        radarr_service = ServiceConfig.query.filter_by(service="RADARR").first()
        if radarr_service:
            radarr_service.last_tested_at = test_timestamp
            radarr_service.last_test_status = test_status
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error updating Radarr test status: {e}", exc_info=True
        )

    return test_result, test_timestamp, test_status


def _test_and_update_sonarr_status(base_url, api_key):
    """
    Tests Sonarr API connection and updates the database with test results.

    Args:
        base_url (str): The Sonarr base URL
        api_key (str): The Sonarr API key to test

    Returns:
        tuple: (test_result: bool, timestamp: datetime, status: str)
    """
    test_result = validate_sonarr_api_key(base_url, api_key)
    test_timestamp = datetime.now(timezone.utc)
    test_status = "success" if test_result else "failed"

    # Update test status in database if service config exists
    try:
        sonarr_service = ServiceConfig.query.filter_by(service="SONARR").first()
        if sonarr_service:
            sonarr_service.last_tested_at = test_timestamp
            sonarr_service.last_test_status = test_status
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error updating Sonarr test status: {e}", exc_info=True
        )

    return test_result, test_timestamp, test_status


@bp.route("/config", methods=["GET", "POST"])
def config_page():
    radarr_api_form = RadarrAPIForm()
    sonarr_api_form = SonarrAPIForm()

    if request.method == "POST":
        if "save_radarr_api" in request.form:
            radarr_url_data = radarr_api_form.radarr_url.data.strip()
            radarr_api_data = radarr_api_form.radarr_api.data.strip()

            if not radarr_url_data or not radarr_api_data:
                flash("URL and API Key cannot be empty.", "warning")
            elif not _is_valid_url(radarr_url_data):
                flash(
                    "Invalid URL format. Please enter a valid URL (e.g., http://localhost:7878).",
                    "warning",
                )
            else:
                # Test the API connection using helper function
                (
                    test_result,
                    test_timestamp,
                    test_status,
                ) = _test_and_update_radarr_status(radarr_url_data, radarr_api_data)

                if not test_result:
                    flash(
                        "Invalid Radarr URL or API Key. Please check and try again.",
                        "error",
                    )
                else:
                    try:
                        # Encrypt the API key
                        enc_key = encrypt_data(radarr_api_data, instance_path=current_app.instance_path)

                        radarr_service = ServiceConfig.query.filter_by(
                            service="RADARR"
                        ).first()
                        if not radarr_service:
                            radarr_service = ServiceConfig(
                                service="RADARR",
                                base_url=radarr_url_data,
                                api_key_encrypted=enc_key,
                                last_tested_at=test_timestamp,
                                last_test_status=test_status,
                            )
                            db.session.add(radarr_service)
                        else:
                            radarr_service.base_url = radarr_url_data
                            radarr_service.api_key_encrypted = enc_key
                            radarr_service.last_tested_at = test_timestamp
                            radarr_service.last_test_status = test_status

                        db.session.commit()
                        flash("Radarr URL and API Key saved successfully.", "success")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error saving Radarr configuration: {e}", exc_info=True)
                        flash(
                            "Failed to save Radarr configuration. Please try again.",
                            "error",
                        )

        if "save_sonarr_api" in request.form:
            sonarr_url_data = sonarr_api_form.sonarr_url.data.strip()
            sonarr_api_data = sonarr_api_form.sonarr_api.data.strip()

            if not sonarr_url_data or not sonarr_api_data:
                flash("URL and API Key cannot be empty.", "warning")
            elif not _is_valid_url(sonarr_url_data):
                flash(
                    "Invalid URL format. Please enter a valid URL (e.g., http://localhost:8989).",
                    "warning",
                )
            else:
                # Test the API connection using helper function
                (
                    test_result,
                    test_timestamp,
                    test_status,
                ) = _test_and_update_sonarr_status(sonarr_url_data, sonarr_api_data)

                if not test_result:
                    flash(
                        "Invalid Sonarr URL or API Key. Please check and try again.",
                        "error",
                    )
                else:
                    try:
                        # Encrypt the API key
                        enc_key = encrypt_data(sonarr_api_data, instance_path=current_app.instance_path)

                        sonarr_service = ServiceConfig.query.filter_by(
                            service="SONARR"
                        ).first()
                        if not sonarr_service:
                            sonarr_service = ServiceConfig(
                                service="SONARR",
                                base_url=sonarr_url_data,
                                api_key_encrypted=enc_key,
                                last_tested_at=test_timestamp,
                                last_test_status=test_status,
                            )
                            db.session.add(sonarr_service)
                        else:
                            sonarr_service.base_url = sonarr_url_data
                            sonarr_service.api_key_encrypted = enc_key
                            sonarr_service.last_tested_at = test_timestamp
                            sonarr_service.last_test_status = test_status

                        db.session.commit()
                        flash("Sonarr URL and API Key saved successfully.", "success")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error saving Sonarr configuration: {e}", exc_info=True)
                        flash(
                            "Failed to save Sonarr configuration. Please try again.",
                            "error",
                        )

        return redirect(url_for("main.config_page"))

    # Populate form with existing key for GET requests
    radarr_existing = ServiceConfig.query.filter_by(service="RADARR").first()
    if radarr_existing and radarr_existing.api_key_encrypted:
        radarr_api_form.radarr_url.data = radarr_existing.base_url
        try:
            radarr_api_form.radarr_api.data = decrypt_data(
                radarr_existing.api_key_encrypted,
                instance_path=current_app.instance_path,
            )
        except (ValueError, Exception) as e:
            current_app.logger.error(f"Error decrypting Radarr API key: {e}", exc_info=True)
            radarr_api_form.radarr_api.data = ""
            flash(
                "Unable to decrypt stored Radarr API key. Please re-enter your Radarr API key.",
                "warning",
            )

    # Pass last test data to template
    last_radarr_test_at = radarr_existing.last_tested_at if radarr_existing else None
    last_radarr_test_status = (
        radarr_existing.last_test_status if radarr_existing else None
    )

    # Check if Radarr is properly configured (has URL and API key saved)
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
        except (ValueError, Exception) as e:
            current_app.logger.error(f"Error decrypting Sonarr API key: {e}", exc_info=True)
            sonarr_api_form.sonarr_api.data = ""
            flash(
                "Unable to decrypt stored Sonarr API key. Please re-enter your Sonarr API key.",
                "warning",
            )

    # Pass Sonarr last test data to template
    last_sonarr_test_at = sonarr_existing.last_tested_at if sonarr_existing else None
    last_sonarr_test_status = (
        sonarr_existing.last_test_status if sonarr_existing else None
    )

    # Check if Sonarr is properly configured (has URL and API key saved)
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


# ----------------------
# Test Radarr API Route (AJAX)
# ----------------------
@bp.route("/config/test_radarr_api", methods=["POST"])
def test_radarr_api():
    base_url = request.json.get("base_url", "")
    api_key = request.json.get("api_key", "")

    if not base_url or not api_key:
        return jsonify(
            {"success": False, "message": "URL and API key cannot be empty."}
        )

    if not _is_valid_url(base_url):
        return jsonify(
            {
                "success": False,
                "message": "Invalid URL format. Please enter a valid URL (e.g., http://localhost:7878).",
            }
        )

    # Use helper function to test and update status
    test_result, test_timestamp, test_status = _test_and_update_radarr_status(
        base_url, api_key
    )

    return jsonify(
        {
            "success": test_result,
            "message": "Radarr connection successful." if test_result else "Invalid Radarr URL or API Key.",
            "timestamp": test_timestamp.isoformat(),
        }
    )


# ----------------------
# Test Sonarr API Route (AJAX)
# ----------------------
@bp.route("/config/test_sonarr_api", methods=["POST"])
def test_sonarr_api():
    base_url = request.json.get("base_url", "")
    api_key = request.json.get("api_key", "")

    if not base_url or not api_key:
        return jsonify(
            {"success": False, "message": "URL and API key cannot be empty."}
        )

    if not _is_valid_url(base_url):
        return jsonify(
            {
                "success": False,
                "message": "Invalid URL format. Please enter a valid URL (e.g., http://localhost:8989).",
            }
        )

    # Use helper function to test and update status
    test_result, test_timestamp, test_status = _test_and_update_sonarr_status(
        base_url, api_key
    )

    return jsonify(
        {
            "success": test_result,
            "message": "Sonarr connection successful." if test_result else "Invalid Sonarr URL or API Key.",
            "timestamp": test_timestamp.isoformat(),
        }
    )


# ----------------------
# Fetch Radarr Quality Profiles (AJAX)
# ----------------------
@bp.route("/config/radarr/quality-profiles", methods=["GET"])
def fetch_radarr_quality_profiles():
    """
    Fetches quality profiles from configured Radarr instance.
    Returns JSON list of quality profiles.
    """
    radarr_service = ServiceConfig.query.filter_by(service="RADARR").first()

    if not radarr_service or not radarr_service.api_key_encrypted:
        return jsonify({"success": False, "message": "Radarr not configured."}), 400

    try:
        # Decrypt API key
        api_key = decrypt_data(
            radarr_service.api_key_encrypted, instance_path=current_app.instance_path
        )
        base_url = radarr_service.base_url

        # Fetch quality profiles
        profiles = get_radarr_quality_profiles(base_url, api_key)

        if not profiles:
            return (
                jsonify({"success": False, "message": "Failed to fetch quality profiles."}),
                500,
            )

        return jsonify({"success": True, "profiles": profiles})
    except ValueError as e:
        # Handle decryption errors
        current_app.logger.error(
            f"Decryption error fetching Radarr quality profiles: {e}", exc_info=True
        )
        return jsonify({"success": False, "message": "Failed to decrypt API key."}), 500
    except Exception as e:
        current_app.logger.error(f"Error fetching Radarr quality profiles: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "Failed to fetch quality profiles."}),
            500,
        )


# ----------------------
# Fetch Radarr Root Folders (AJAX)
# ----------------------
@bp.route("/config/radarr/root-folders", methods=["GET"])
def fetch_radarr_root_folders():
    """
    Fetches root folders from configured Radarr instance.
    Returns JSON list of root folders.
    """
    radarr_service = ServiceConfig.query.filter_by(service="RADARR").first()

    if not radarr_service or not radarr_service.api_key_encrypted:
        return jsonify({"success": False, "message": "Radarr not configured."}), 400

    try:
        # Decrypt API key
        api_key = decrypt_data(
            radarr_service.api_key_encrypted, instance_path=current_app.instance_path
        )
        base_url = radarr_service.base_url

        # Fetch root folders
        folders = get_radarr_root_folders(base_url, api_key)

        if not folders:
            return (
                jsonify({"success": False, "message": "Failed to fetch root folders."}),
                500,
            )

        return jsonify({"success": True, "folders": folders})
    except ValueError as e:
        # Handle decryption errors
        current_app.logger.error(
            f"Decryption error fetching Radarr root folders: {e}", exc_info=True
        )
        return jsonify({"success": False, "message": "Failed to decrypt API key."}), 500
    except Exception as e:
        current_app.logger.error(f"Error fetching Radarr root folders: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "Failed to fetch root folders."}),
            500,
        )


# ----------------------
# Fetch Radarr Import Settings (AJAX)
# ----------------------
@bp.route("/config/radarr/import-settings", methods=["GET"])
def fetch_radarr_import_settings():
    """
    Fetches saved import settings for Radarr from the database.
    Returns JSON with root_folder_id, quality_profile_id, monitored, search_on_add, and tag_label.
    Note: root_folder is stored as path, but we return the ID for frontend dropdown selection.
    """
    import_settings = MediaImportSettings.query.filter_by(service="RADARR").first()

    if not import_settings:
        return jsonify({"success": True, "settings": None})

    # Get Radarr service config for API calls
    radarr_service = ServiceConfig.query.filter_by(service="RADARR").first()
    root_folder_id = None
    tag_label = None

    if radarr_service and radarr_service.api_key_encrypted:
        try:
            api_key = decrypt_data(
                radarr_service.api_key_encrypted,
                instance_path=current_app.instance_path,
            )
            base_url = radarr_service.base_url

            # Look up root folder ID from stored path
            if import_settings.root_folder:
                folders = get_radarr_root_folders(base_url, api_key)
                for folder in folders:
                    if folder.get("path") == import_settings.root_folder:
                        root_folder_id = folder.get("id")
                        break

            # Get tag label if tag ID exists
            if import_settings.default_tag_id:
                tags = get_radarr_tags(base_url, api_key)
                for tag in tags:
                    if tag.get("id") == import_settings.default_tag_id:
                        tag_label = tag.get("label")
                        break
        except Exception as e:
            current_app.logger.error(f"Error fetching Radarr data: {e}", exc_info=True)

    return jsonify(
        {
            "success": True,
            "settings": {
                "root_folder_id": root_folder_id,
                "quality_profile_id": import_settings.quality_profile_id,
                "monitored": import_settings.monitored,
                "search_on_add": import_settings.search_on_add,
                "tag_label": tag_label,
            },
        }
    )


# ----------------------
# Save Radarr Import Settings (AJAX)
# ----------------------
@bp.route("/config/radarr/import-settings", methods=["POST"])
def save_radarr_import_settings():
    """
    Saves import settings for Radarr to the database.
    Expects JSON with root_folder_id, quality_profile_id, monitored, search_on_add, and tag_label.
    Stores the actual root folder path (not ID) for use by import service.
    """
    data = request.json
    root_folder_id = data.get("root_folder_id")
    quality_profile_id = data.get("quality_profile_id")
    monitored = data.get("monitored")
    search_on_add = data.get("search_on_add")
    tag_label = data.get("tag_label")

    # Validate inputs
    if not root_folder_id or not quality_profile_id:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Root Folder and Quality Profile are required.",
                }
            ),
            400,
        )

    if monitored is None:
        return (
            jsonify({"success": False, "message": "Monitor option is required."}),
            400,
        )

    if search_on_add is None:
        return (
            jsonify({"success": False, "message": "Search on Add option is required."}),
            400,
        )

    # Get Radarr service config (needed for root folder lookup and tag handling)
    radarr_config = ServiceConfig.query.filter_by(service="RADARR").first()
    if not radarr_config or not radarr_config.api_key_encrypted:
        return jsonify({"success": False, "message": "Radarr not configured."}), 400

    try:
        api_key = decrypt_data(
            radarr_config.api_key_encrypted, instance_path=current_app.instance_path
        )
        base_url = radarr_config.base_url
    except Exception as e:
        current_app.logger.error(f"Error decrypting Radarr API key: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to decrypt API key"}), 500

    # Look up root folder path from ID
    try:
        folders = get_radarr_root_folders(base_url, api_key)
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
                        "message": f"Root folder ID {root_folder_id} not found in Radarr",
                    }
                ),
                400,
            )
    except Exception as e:
        current_app.logger.error(f"Error fetching root folders from Radarr: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "Failed to fetch root folders"}),
            500,
        )

    # Handle tag creation/lookup
    tag_id = None
    if tag_label and tag_label.strip():
        try:
            tag_id = radarr_create_or_get_tag_id(base_url, api_key, tag_label.strip())
            if tag_id is None:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Failed to create/find tag in Radarr",
                        }
                    ),
                    500,
                )
        except Exception as e:
            current_app.logger.error(
                f"Error handling tag for Radarr: {e}", exc_info=True
            )
            return jsonify({"success": False, "message": "Failed to process tag"}), 500

    try:
        # Check if settings already exist for Radarr
        import_settings = MediaImportSettings.query.filter_by(service="RADARR").first()

        if import_settings:
            # Update existing settings
            import_settings.root_folder = root_folder_path
            import_settings.quality_profile_id = int(quality_profile_id)
            import_settings.monitored = bool(monitored)
            import_settings.search_on_add = bool(search_on_add)
            import_settings.default_tag_id = tag_id
        else:
            # Create new settings
            import_settings = MediaImportSettings(
                service="RADARR",
                root_folder=root_folder_path,
                quality_profile_id=int(quality_profile_id),
                monitored=bool(monitored),
                search_on_add=bool(search_on_add),
                default_tag_id=tag_id,
            )
            db.session.add(import_settings)

        db.session.commit()

        return jsonify(
            {"success": True, "message": "Radarr import settings saved successfully."}
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"success": False, "message": f"Failed to save settings: {str(e)}"}),
            500,
        )


# ----------------------
# Fetch Sonarr Quality Profiles (AJAX)
# ----------------------
@bp.route("/config/sonarr/quality-profiles", methods=["GET"])
def fetch_sonarr_quality_profiles():
    """
    Fetches quality profiles from configured Sonarr instance.
    Returns JSON list of quality profiles.
    """
    sonarr_service = ServiceConfig.query.filter_by(service="SONARR").first()

    if not sonarr_service or not sonarr_service.api_key_encrypted:
        return jsonify({"success": False, "message": "Sonarr not configured."}), 400

    try:
        # Decrypt API key
        api_key = decrypt_data(
            sonarr_service.api_key_encrypted, instance_path=current_app.instance_path
        )
        base_url = sonarr_service.base_url

        # Fetch quality profiles
        profiles = get_sonarr_quality_profiles(base_url, api_key)

        if not profiles:
            return (
                jsonify({"success": False, "message": "Failed to fetch quality profiles."}),
                500,
            )

        return jsonify({"success": True, "profiles": profiles})
    except ValueError as e:
        # Handle decryption errors
        current_app.logger.error(
            f"Decryption error fetching Sonarr quality profiles: {e}", exc_info=True
        )
        return jsonify({"success": False, "message": "Failed to decrypt API key."}), 500
    except Exception as e:
        current_app.logger.error(f"Error fetching Sonarr quality profiles: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "Failed to fetch quality profiles."}),
            500,
        )


# ----------------------
# Fetch Sonarr Root Folders (AJAX)
# ----------------------
@bp.route("/config/sonarr/root-folders", methods=["GET"])
def fetch_sonarr_root_folders():
    """
    Fetches root folders from configured Sonarr instance.
    Returns JSON list of root folders.
    """
    sonarr_service = ServiceConfig.query.filter_by(service="SONARR").first()

    if not sonarr_service or not sonarr_service.api_key_encrypted:
        return jsonify({"success": False, "message": "Sonarr not configured."}), 400

    try:
        # Decrypt API key
        api_key = decrypt_data(
            sonarr_service.api_key_encrypted, instance_path=current_app.instance_path
        )
        base_url = sonarr_service.base_url

        # Fetch root folders
        folders = get_sonarr_root_folders(base_url, api_key)

        if not folders:
            return (
                jsonify({"success": False, "message": "Failed to fetch root folders."}),
                500,
            )

        return jsonify({"success": True, "folders": folders})
    except ValueError as e:
        # Handle decryption errors
        current_app.logger.error(
            f"Decryption error fetching Sonarr root folders: {e}", exc_info=True
        )
        return jsonify({"success": False, "message": "Failed to decrypt API key."}), 500
    except Exception as e:
        current_app.logger.error(f"Error fetching Sonarr root folders: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "Failed to fetch root folders."}),
            500,
        )


# ----------------------
# Fetch Sonarr Import Settings (AJAX)
# ----------------------
@bp.route("/config/sonarr/import-settings", methods=["GET"])
def fetch_sonarr_import_settings():
    """
    Fetches saved import settings for Sonarr from the database.
    Returns JSON with root_folder_id, quality_profile_id, monitored, season_folder, search_on_add, and tag_label.
    Note: root_folder is stored as path, but we return the ID for frontend dropdown selection.
    """
    import_settings = MediaImportSettings.query.filter_by(service="SONARR").first()

    if not import_settings:
        return jsonify({"success": True, "settings": None})

    # Get Sonarr service config for API calls
    sonarr_service = ServiceConfig.query.filter_by(service="SONARR").first()
    root_folder_id = None
    tag_label = None

    if sonarr_service and sonarr_service.api_key_encrypted:
        try:
            api_key = decrypt_data(
                sonarr_service.api_key_encrypted,
                instance_path=current_app.instance_path,
            )
            base_url = sonarr_service.base_url

            # Look up root folder ID from stored path
            if import_settings.root_folder:
                folders = get_sonarr_root_folders(base_url, api_key)
                for folder in folders:
                    if folder.get("path") == import_settings.root_folder:
                        root_folder_id = folder.get("id")
                        break

            # Get tag label if tag ID exists
            if import_settings.default_tag_id:
                tags = get_sonarr_tags(base_url, api_key)
                for tag in tags:
                    if tag.get("id") == import_settings.default_tag_id:
                        tag_label = tag.get("label")
                        break
        except Exception as e:
            current_app.logger.error(f"Error fetching Sonarr data: {e}", exc_info=True)

    return jsonify(
        {
            "success": True,
            "settings": {
                "root_folder_id": root_folder_id,
                "quality_profile_id": import_settings.quality_profile_id,
                "monitored": import_settings.monitored,
                "season_folder": import_settings.season_folder,
                "search_on_add": import_settings.search_on_add,
                "tag_label": tag_label,
            },
        }
    )


# ----------------------
# Save Sonarr Import Settings (AJAX)
# ----------------------
@bp.route("/config/sonarr/import-settings", methods=["POST"])
def save_sonarr_import_settings():
    """
    Saves import settings for Sonarr to the database.
    Expects JSON with root_folder_id, quality_profile_id, monitored, season_folder, search_on_add, and tag_label.
    Stores the actual root folder path (not ID) for use by import service.
    """
    data = request.json
    root_folder_id = data.get("root_folder_id")
    quality_profile_id = data.get("quality_profile_id")
    monitored = data.get("monitored")
    season_folder = data.get("season_folder")
    search_on_add = data.get("search_on_add")
    tag_label = data.get("tag_label")

    # Validate inputs
    if not root_folder_id or not quality_profile_id:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Root Folder and Quality Profile are required.",
                }
            ),
            400,
        )

    if monitored is None:
        return (
            jsonify({"success": False, "message": "Monitor option is required."}),
            400,
        )

    if season_folder is None:
        return (
            jsonify({"success": False, "message": "Season Folder option is required."}),
            400,
        )

    if search_on_add is None:
        return (
            jsonify({"success": False, "message": "Search on Add option is required."}),
            400,
        )

    # Get Sonarr service config (needed for root folder lookup and tag handling)
    sonarr_config = ServiceConfig.query.filter_by(service="SONARR").first()
    if not sonarr_config or not sonarr_config.api_key_encrypted:
        return jsonify({"success": False, "message": "Sonarr not configured."}), 400

    try:
        api_key = decrypt_data(
            sonarr_config.api_key_encrypted, instance_path=current_app.instance_path
        )
        base_url = sonarr_config.base_url
    except Exception as e:
        current_app.logger.error(f"Error decrypting Sonarr API key: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to decrypt API key"}), 500

    # Look up root folder path from ID
    try:
        folders = get_sonarr_root_folders(base_url, api_key)
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
                        "message": f"Root folder ID {root_folder_id} not found in Sonarr",
                    }
                ),
                400,
            )
    except Exception as e:
        current_app.logger.error(f"Error fetching root folders from Sonarr: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "Failed to fetch root folders"}),
            500,
        )

    # Handle tag creation/lookup
    tag_id = None
    if tag_label and tag_label.strip():
        try:
            tag_id = sonarr_create_or_get_tag_id(base_url, api_key, tag_label.strip())
            if tag_id is None:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Failed to create/find tag in Sonarr",
                        }
                    ),
                    500,
                )
        except Exception as e:
            current_app.logger.error(
                f"Error handling tag for Sonarr: {e}", exc_info=True
            )
            return jsonify({"success": False, "message": "Failed to process tag"}), 500

    try:
        # Check if settings already exist for Sonarr
        import_settings = MediaImportSettings.query.filter_by(service="SONARR").first()

        if import_settings:
            # Update existing settings
            import_settings.root_folder = root_folder_path
            import_settings.quality_profile_id = int(quality_profile_id)
            import_settings.monitored = bool(monitored)
            import_settings.season_folder = bool(season_folder)
            import_settings.search_on_add = bool(search_on_add)
            import_settings.default_tag_id = tag_id
        else:
            # Create new settings
            import_settings = MediaImportSettings(
                service="SONARR",
                root_folder=root_folder_path,
                quality_profile_id=int(quality_profile_id),
                monitored=bool(monitored),
                season_folder=bool(season_folder),
                search_on_add=bool(search_on_add),
                default_tag_id=tag_id,
            )
            db.session.add(import_settings)

        db.session.commit()

        return jsonify(
            {"success": True, "message": "Sonarr import settings saved successfully."}
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"success": False, "message": f"Failed to save settings: {str(e)}"}),
            500,
        )
