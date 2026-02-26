from flask import redirect, render_template, url_for
from flask_login import login_required

from listarr import db
from listarr.forms.lists_forms import ListForm
from listarr.models.lists_model import List
from listarr.routes import bp
from listarr.services.scheduler import get_next_run_time
from listarr.utils.time_utils import format_relative_time


@bp.route("/")
@login_required
def dashboard_page():
    lists = db.session.query(List).all()

    # Compute next run time for each list
    for list_obj in lists:
        if list_obj.schedule_cron and list_obj.is_active:
            next_run = get_next_run_time(list_obj.id)
            list_obj.next_run_formatted = format_relative_time(next_run)
        else:
            list_obj.next_run_formatted = None

    form = ListForm()
    return render_template("lists.html", lists=lists, form=form)


@bp.route("/dashboard")
def dashboard_redirect():
    return redirect(url_for("main.lists_page"), code=301)
