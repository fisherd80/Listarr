from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class SetupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters"),
            EqualTo("password_confirm", message="Passwords must match"),
        ],
    )
    password_confirm = PasswordField("Confirm Password", validators=[DataRequired()])
    submit = SubmitField("Create Account")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters"),
            EqualTo("new_password_confirm", message="Passwords must match"),
        ],
    )
    new_password_confirm = PasswordField("Confirm New Password", validators=[DataRequired()])
    submit = SubmitField("Change Password")
