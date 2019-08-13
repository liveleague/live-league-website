from flask import Flask, render_template
from wrapper import *

app = Flask(__name__)

@app.route('/')
def index():
    """Homepage."""
    standings = list_table_rows()
    upcoming_events = list_events(when='upcoming')
    return render_template(
        'index.html', standings=standings, upcoming_events=upcoming_events
    )

@app.route('/artist/<slug>')
def artist(slug):
    """Artist's public profile."""
    artist = get_artist(slug)
    past_events = list_tallies(when='past', slug=slug)
    print(past_events)
    upcoming_events = list_tallies(when='upcoming', slug=slug)
    return render_template('artist.html', artist=artist)

@app.route('/promoter/<slug>')
def promoter(slug):
    """Promoter's public profile."""
    return render_template('promoter.html')

@app.route('/venue/<slug>')
def venue(slug):
    """Venue page."""
    return render_template('venue.html')

@app.route('/<id>')
def event(id):
    """Event page."""
    return render_template('event.html')
