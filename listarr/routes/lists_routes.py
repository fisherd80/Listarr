from flask import render_template, flash, request, redirect, url_for, current_app
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
