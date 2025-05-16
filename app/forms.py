from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from .models import User
from flask_wtf.file import FileField, FileAllowed # For profile picture
from flask_login import current_user # To access current user in validators

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=20)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8)
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered.')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken.')


class LoginForm(FlaskForm):
    identifier = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class UpdateProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    profile_picture = FileField('Update Profile Picture (JPG, PNG, GIF - Max 2MB)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ]) # This field is optional, so no DataRequired()
    submit_profile = SubmitField('Update Profile')

    def validate_username(self, username_field):
        # Check if the submitted username is different from the current user's username
        if username_field.data != current_user.username:
            # If it's different, then check if this new username is already taken by ANOTHER user
            user = User.query.filter_by(username=username_field.data).first()
            if user: # A user with this new username already exists
                raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email_field):
        # Check if the submitted email is different from the current user's email
        if email_field.data != current_user.email:
            # If it's different, then check if this new email is already registered by ANOTHER user
            user = User.query.filter_by(email=email_field.data).first()
            if user: # An account with this new email already exists
                raise ValidationError('That email is already registered. Please choose a different one.')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField('Confirm New Password', 
                                         validators=[DataRequired(), EqualTo('new_password', message='New passwords must match.')])
    submit_password = SubmitField('Change Password')