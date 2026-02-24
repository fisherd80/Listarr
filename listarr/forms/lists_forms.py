from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import DataRequired, Length

# Cron schedule presets - must match wizard options in list_wizard.html
SCHEDULE_CHOICES = [
    ("", "Manual only"),
    ("0 * * * *", "Every hour"),
    ("0 */6 * * *", "Every 6 hours"),
    ("0 0 * * *", "Daily (midnight)"),
    ("0 0 * * SUN", "Weekly (Sunday midnight)"),
]

# Tri-state choices for Yes/No/Default
TRI_STATE_CHOICES = [
    ("", "Use Default"),
    ("1", "Yes"),
    ("0", "No"),
]


class ListForm(FlaskForm):
    """Form for editing list settings (not type/filters)."""

    name = StringField(label="Name", validators=[DataRequired(), Length(max=100)])

    is_active = BooleanField(label="Active", default=True)

    schedule_cron = SelectField(label="Schedule", choices=SCHEDULE_CHOICES, validators=[])

    # Import settings - choices populated dynamically in route
    override_quality_profile = SelectField(label="Quality Profile", choices=[("", "Use Default")], validators=[])

    override_root_folder = SelectField(label="Root Folder", choices=[("", "Use Default")], validators=[])

    override_tag = StringField(label="Tag", validators=[])

    override_monitored = SelectField(label="Monitored", choices=TRI_STATE_CHOICES, validators=[])

    override_search_on_add = SelectField(label="Search on Add", choices=TRI_STATE_CHOICES, validators=[])

    override_season_folder = SelectField(
        label="Season Folder",
        choices=TRI_STATE_CHOICES,
        validators=[],
        validate_choice=False,  # Don't validate choice - field only rendered for Sonarr
    )
