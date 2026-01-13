from flask import render_template
from listarr.routes import bp
from listarr.models.lists_model import List
from listarr import db

@bp.route("/lists")
def lists_page():
    lists = db.session.query(List).all()
    return render_template("lists.html", lists=lists)
