from functools import wraps

from flask import render_template, request, session

from app import app
from app.wrapper import Public
from app.forms import LoginForm

pub = Public()

@app.before_request
def make_session_permanent():
    session.permanent = True

def login_required(f):
    """Checks that a user is signed in."""
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'token' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('sign_in'))
    return wrap

@app.route('/')
def index():
    """Homepage."""
    standings = pub.list_table_rows()
    upcoming_events = pub.list_events(when='upcoming')
    print(session)
    return render_template(
        'index.html', standings=standings, upcoming_events=upcoming_events
    )

@app.route('/about')
def about():
    """About us page."""
    return render_template('about.html')

@app.route('/list/<category>')
def list(category):
    """List all public objects in the database."""
    if category == 'events':
        data = pub.list_events()
        return render_template(
            'list_events.html', category=category, data=data
        )

@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    """Sign-in/registration page."""
    form = LoginForm()
    if form.validate_on_submit():
        token = pub.get_token(
            email=request.form['email'], password=request.form['password']
        )
        session['token'] = token['token']
        return redirect('account.html')
    return render_template('sign_in.html', form=form)

@app.route('/account')
@login_required
def account():
    return render_template('account.html')

@app.route('/checkout')
def checkout():
    """Checkout page."""
    return render_template('checkout.html')

@app.route('/artist/<slug>')
def artist(slug):
    """Artist's public profile."""
    artist = pub.get_artist(slug)
    past_events = pub.list_tallies(when='past', slug=slug)
    upcoming_events = pub.list_tallies(when='upcoming', slug=slug)
    return render_template(
        'artist.html',
        artist=artist,
        past_events=past_events,
        upcoming_events=upcoming_events
    )

@app.route('/promoter/<slug>')
def promoter(slug):
    """Promoter's public profile."""
    promoter = pub.get_promoter(slug)
    past_events = pub.list_events(promoter=slug, when='past')
    upcoming_events = pub.list_events(promoter=slug, when='upcoming')
    return render_template(
        'promoter.html',
        promoter=promoter,
        past_events=past_events,
        upcoming_events=upcoming_events
    )

@app.route('/venue/<slug>')
def venue(slug):
    """Venue page."""
    venue = pub.get_venue(slug)
    past_events = pub.list_events(venue=slug, when='past')
    upcoming_events = pub.list_events(venue=slug, when='upcoming')
    return render_template(
        'venue.html',
        venue=venue,
        past_events=past_events,
        upcoming_events=upcoming_events
    )

@app.route('/id/<id>')
def event(id):
    """Event page."""
    print('test')
    event = pub.get_event(id)
    return render_template('event.html', event=event)
