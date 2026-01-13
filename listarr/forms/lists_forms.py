from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, HiddenField, BooleanField
from wtforms.validators import DataRequired, Length

class ListForm(FlaskForm):
    name = StringField(
        label="Name",
        validators=[DataRequired(), Length(max=100)]
    )

    target_service = SelectField(
        label="Target Service",
        choices=[("RADARR", "Radarr"), ("SONARR", "Sonarr")],
        validators=[DataRequired()]
    )

    tmdb_list_type = SelectField(
        label="TMDB List Type",
        choices=[
            ("trending_movies", "Trending Movies"),
            ("popular_movies", "Popular Movies"),
            ("trending_tv", "Trending TV Shows"),
            ("popular_tv", "Popular TV Shows")
        ],
        validators=[DataRequired()]
    )

    filters_json = HiddenField(default="{}")

    is_active = BooleanField(label="Active", default=True)
