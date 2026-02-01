from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired


class RadarrAPIForm(FlaskForm):
    radarr_url = StringField(label="URL / IP Address", validators=[DataRequired()])

    radarr_api = StringField(label="API Key", validators=[DataRequired()])


class SonarrAPIForm(FlaskForm):
    sonarr_url = StringField(label="URL / IP Address", validators=[DataRequired()])

    sonarr_api = StringField(label="API Key", validators=[DataRequired()])
