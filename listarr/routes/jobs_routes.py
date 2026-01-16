from flask import render_template
from listarr.routes import bp

@bp.route("/jobs")
def jobs_page():
    return render_template("jobs.html")
