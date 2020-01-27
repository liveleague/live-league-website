from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, StringField, PasswordField, SubmitField, \
                    IntegerField, RadioField, TextAreaField, SelectField, \
                    DateField
from wtforms.fields.html5 import URLField
from wtforms_components import TimeField
from wtforms.validators import Email, DataRequired, url, Optional

from app.phonefield import COUNTRY_CODES


class LoginForm(FlaskForm):
    register = BooleanField()
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField()


class RegisterUserForm(FlaskForm):
    email = StringField('Email *', validators=[DataRequired(), Email()])
    password = PasswordField('Password *', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm password')
    first_name = StringField('First Name *', validators=[DataRequired()])
    last_name = StringField('Last Name *', validators=[DataRequired()])
    submit = SubmitField()


class RegisterArtistPromoterForm(FlaskForm):
    group = RadioField(
        'Label', choices=[
            ('artist', 'Artist'),
            ('promoter', 'Promoter'),
            ('neither', 'Neither')
        ]
    )
    email = StringField('Email *', validators=[DataRequired(), Email()])
    password = PasswordField('Password *', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm password')
    name = StringField('Name *', validators=[DataRequired()])
    country_code = SelectField('Phone Country *', choices=COUNTRY_CODES)
    phone = StringField('Phone Number *', validators=[DataRequired()])
    submit = SubmitField()

    # Optional fields
    description = TextAreaField('Description')
    facebook = URLField('Facebook', validators=[url(), Optional()])
    instagram = URLField('Instagram', validators=[url(), Optional()])
    soundcloud = URLField('Soundcloud', validators=[url(), Optional()])
    spotify = URLField('Spotify', validators=[url(), Optional()])
    twitter = URLField('Twitter', validators=[url(), Optional()])
    website = URLField('Website', validators=[url(), Optional()])
    youtube = URLField('Youtube', validators=[url(), Optional()])
    image = FileField('Profile Picture')


class EmailForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField()


class PasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField()


class VenueForm(FlaskForm):
    name = StringField('Name *', validators=[DataRequired()])
    description = TextAreaField('Description')
    address_city = StringField('City *', validators=[DataRequired()])
    address_country = SelectField('Country *', choices=COUNTRY_CODES)
    address_line1 = StringField(
        'Address Line 1 *', validators=[DataRequired()]
    )
    address_line2 = StringField('Address Line 2')
    address_state = StringField('County')
    address_zip = StringField('Postcode *', validators=[DataRequired()])
    google_maps = StringField('Google Maps')
    image = FileField('Profile Picture')
    submit = SubmitField()


class EventForm(FlaskForm):
    name = StringField('Name *', validators=[DataRequired()])
    description = TextAreaField('Description')
    start_date = DateField('Start date *', validators=[DataRequired()])
    start_time = TimeField('Start time *', validators=[DataRequired()])
    end_date = DateField('End date *', validators=[DataRequired()])
    end_time = TimeField('End time *', validators=[DataRequired()])
    image = FileField('Profile Picture')
    submit = SubmitField()
