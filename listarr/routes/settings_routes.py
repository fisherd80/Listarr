from datetime import datetime, timezone

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

from listarr import db
from listarr.forms.settings_forms import TmdbApiForm
from listarr.models.service_config_model import ServiceConfig
from listarr.routes import bp
from listarr.services.crypto_utils import decrypt_data, encrypt_data
from listarr.services.tmdb_service import validate_tmdb_api_key


# ----------------------
# Helper Functions
# ----------------------
def _test_and_update_tmdb_status(api_key):
    """
    Tests TMDB API key and updates the database with test results.

    Args:
        api_key (str): The TMDB API key to test

    Returns:
        tuple: (test_result: bool, timestamp: datetime, status: str)
    """
    test_result = validate_tmdb_api_key(api_key)
    test_timestamp = datetime.now(timezone.utc)
    test_status = "success" if test_result else "failed"

    # Update test status in database if service config exists
    try:
        tmdb_service = ServiceConfig.query.filter_by(service="TMDB").first()
        if tmdb_service:
            tmdb_service.last_tested_at = test_timestamp
            tmdb_service.last_test_status = test_status
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating TMDB test status: {e}", exc_info=True)

    return test_result, test_timestamp, test_status


# ----------------------
# Settings Page Route
# ----------------------
@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    tmdb_api_form = TmdbApiForm()

    if request.method == "POST":
        api_key = tmdb_api_form.tmdb_api.data.strip()

        # Save API Key Button
        if "save_api_key" in request.form:
            if not api_key:
                flash("API Key cannot be empty.", "warning")
            else:
                # Test the API key using helper function
                test_result, test_timestamp, test_status = _test_and_update_tmdb_status(api_key)

                if not test_result:
                    flash("Invalid TMDB API Key. Please check and try again.", "error")
                else:
                    try:
                        enc_key = encrypt_data(api_key, instance_path=current_app.instance_path)

                        tmdb_service = ServiceConfig.query.filter_by(service="TMDB").first()
                        if not tmdb_service:
                            tmdb_service = ServiceConfig(
                                service="TMDB",
                                api_key_encrypted=enc_key,
                                last_tested_at=test_timestamp,
                                last_test_status=test_status,
                            )
                            db.session.add(tmdb_service)
                        else:
                            tmdb_service.api_key_encrypted = enc_key
                            tmdb_service.last_tested_at = test_timestamp
                            tmdb_service.last_test_status = test_status
                        # Save region setting
                        tmdb_service.tmdb_region = tmdb_api_form.tmdb_region.data or None
                        db.session.commit()
                        flash("TMDB API Key saved successfully.", "success")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error saving TMDB configuration: {e}", exc_info=True)
                        flash(
                            "Failed to save TMDB configuration. Please try again.",
                            "error",
                        )

            return redirect(url_for("main.settings_page"))

    # Populate form with existing key and region for GET requests
    existing = ServiceConfig.query.filter_by(service="TMDB").first()
    if existing and existing.api_key_encrypted:
        try:
            tmdb_api_form.tmdb_api.data = decrypt_data(
                existing.api_key_encrypted, instance_path=current_app.instance_path
            )
        except (ValueError, Exception) as e:
            current_app.logger.error(f"Error decrypting TMDB API key: {e}", exc_info=True)
            tmdb_api_form.tmdb_api.data = ""
            flash(
                "Unable to decrypt stored API key. Please re-enter your TMDB API key.",
                "warning",
            )
    if existing:
        tmdb_api_form.tmdb_region.data = existing.tmdb_region or ""

    # Pass last test data to template
    last_test_at = existing.last_tested_at if existing else None
    last_test_status = existing.last_test_status if existing else None

    return render_template(
        "settings.html",
        tmdb_api_form=tmdb_api_form,
        last_test_at=last_test_at,
        last_test_status=last_test_status,
    )


# ----------------------
# Test TMDB API Key Route (AJAX)
# ----------------------
@bp.route("/settings/test_tmdb_api", methods=["POST"])
@login_required
def test_tmdb_api():
    api_key = request.json.get("api_key", "")
    if not api_key:
        return jsonify({"success": False, "message": "API key cannot be empty."})

    # Use helper function to test and update status
    test_result, test_timestamp, test_status = _test_and_update_tmdb_status(api_key)

    return jsonify(
        {
            "success": test_result,
            "message": "TMDB API Key is valid." if test_result else "Invalid TMDB API Key.",
            "timestamp": test_timestamp.isoformat(),
        }
    )
