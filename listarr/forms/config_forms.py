from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import URL, DataRequired, Length


class RadarrAPIForm(FlaskForm):
    radarr_url = StringField(
        label="URL / IP Address",
        validators=[
            DataRequired(),
            URL(require_tld=False, message="Invalid URL format. Include http:// or https://"),
        ],
    )

    radarr_api = StringField(
        label="API Key",
        validators=[DataRequired(), Length(min=1, max=100, message="API key must be 1-100 characters")],
    )


class SonarrAPIForm(FlaskForm):
    sonarr_url = StringField(
        label="URL / IP Address",
        validators=[
            DataRequired(),
            URL(require_tld=False, message="Invalid URL format. Include http:// or https://"),
        ],
    )

    sonarr_api = StringField(
        label="API Key",
        validators=[DataRequired(), Length(min=1, max=100, message="API key must be 1-100 characters")],
    )
