from flask import Flask, render_template
from wrapper import *

app = Flask(__name__)

@app.route('/')
def index():
    """Homepage."""
    standings = list_table_rows()
    upcoming_events = list_events(filter='upcoming')
    return render_template(
        'index.html', standings=standings, upcoming_events=upcoming_events
    )
