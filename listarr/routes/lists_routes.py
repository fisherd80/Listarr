from flask import render_template, flash, request, redirect, url_for, current_app, jsonify
from datetime import datetime, timezone
from listarr.routes import bp
from listarr.models.lists_model import List
from listarr.forms.lists_forms import ListForm
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
    """Wizard route for creating lists via presets or custom configuration."""
    preset = request.args.get("preset")
    service = request.args.get("service")
    # Placeholder - will be expanded in 02-02
    return f"Wizard placeholder: preset={preset}, service={service}"


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
