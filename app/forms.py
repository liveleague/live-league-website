from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, PasswordField, SubmitField, \
                    IntegerField
from wtforms.validators import Email, DataRequired, EqualTo


class LoginForm(FlaskForm):
    register = BooleanField()
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField()


class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        EqualTo('confirm', message='Passwords must match.')
    ])
    confirm = PasswordField('Confirm Password')
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    submit = SubmitField()


class AddressForm(FlaskForm):
    address_line1 = StringField('Address Line 1', validators=[DataRequired()])
    address_line2 = StringField('Address Line 2')
    address_zip = StringField('Postcode', validators=[DataRequired()])
