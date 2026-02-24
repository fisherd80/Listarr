from flask_wtf import FlaskForm
from wtforms import SelectField, StringField
from wtforms.validators import DataRequired

# Top 5 most common regions first, then extended list (sorted alphabetically)
REGION_CHOICES = [
    ("", "Worldwide (No filter)"),
    # Top 5 most common regions
    ("US", "United States"),
    ("GB", "United Kingdom"),
    ("CA", "Canada"),
    ("AU", "Australia"),
    ("DE", "Germany"),
    # Extended list (alphabetically sorted by country name)
    ("AR", "Argentina"),
    ("AT", "Austria"),
    ("BE", "Belgium"),
    ("BR", "Brazil"),
    ("CH", "Switzerland"),
    ("ES", "Spain"),
    ("FR", "France"),
    ("IN", "India"),
    ("IT", "Italy"),
    ("JP", "Japan"),
    ("KR", "South Korea"),
    ("MX", "Mexico"),
    ("NL", "Netherlands"),
    ("NZ", "New Zealand"),
    ("PL", "Poland"),
    ("PT", "Portugal"),
    ("RU", "Russia"),
    ("SE", "Sweden"),
    ("ZA", "South Africa"),
]


class TmdbApiForm(FlaskForm):
    tmdb_api = StringField(label="TMDB API Key", validators=[DataRequired()])
    tmdb_region = SelectField("Region", choices=REGION_CHOICES)
