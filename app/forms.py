
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

# Form used during user registration
class RegistrationForm(FlaskForm):
    # Field for the username with validation for required input and length
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=100)])
    
    # Field for email input, must be a valid email format
    email = StringField('Email', validators=[DataRequired(), Email()])
    
    # Password field with a minimum length requirement
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    
    # Field to confirm password entry (must match the first one)
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

# Form used for user login
class LoginForm(FlaskForm):
    # Username input field with basic validation
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=100)])
    
    # Password field, required
    password = PasswordField('Password', validators=[DataRequired()])
    
    # Submit button to log in
    submit = SubmitField('Login')

# Placeholder for file upload form (can be extended with fields later)
class UploadForm(FlaskForm):
    pass

