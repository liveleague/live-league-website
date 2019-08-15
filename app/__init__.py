from flask import Flask

from config import Config
from filters import format_date, format_time

app = Flask(__name__)
app.config.from_object(Config)
app.jinja_env.filters['date'] = format_date
app.jinja_env.filters['time'] = format_time

from app import routes
