from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

class TmdbApiForm(FlaskForm):
    tmdb_api=StringField(
        label='TMDB API Key',
        validators=[DataRequired()]
    )
