from functools import wraps

from flask import render_template, request, session, redirect, url_for, jsonify

from app import app
from app.wrapper import Public, Private
from app.forms import LoginForm, RegisterForm

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

@app.route('/_add_to_cart')
def add_to_cart():
    ticket_type = request.args.get('ticket_type')
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(ticket_type)
    print(session)
    return jsonify(result=session['cart'][-1])

@app.route('/')
def index():
    """Homepage."""
    standings = pub.list_table_rows()
    prize_pool = 0
    for row in standings:
        prize_pool += row['points']
    upcoming_events = pub.list_events(when='upcoming')
    print(session)
    return render_template(
        'index.html',
        standings=standings,
        prize_pool=prize_pool,
        upcoming_events=upcoming_events
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
    login_form = LoginForm(prefix='login_form')
    register_form = RegisterForm(prefix='register_form')
    if login_form.validate_on_submit():
        token = pub.get_token(
            email=request.form['login_form-email'],
            password=request.form['login_form-password']
        )
        session['token'] = token['token']
        return redirect(url_for('account'))
    if register_form.validate_on_submit():
        email = request.form['register_form-email']
        password = request.form['register_form-password']
        name = request.form['register_form-first_name'] + ' ' + \
               request.form['register_form-last_name']
        user = pub.create_user(email=email, password=password, name=name)
        token = pub.get_token(email=email, password=password)
        session['token'] = token['token']
        return redirect(url_for('account'))
    return render_template(
        'sign_in.html',
        login_form=login_form,
        register_form=register_form
    )

@login_required
@app.route('/sign-out')
def sign_out():
    """Sign-out page."""
    session.clear()
    return redirect(url_for('index'))

@app.route('/account')
@login_required
def account():
    account = Private(session['token']).get_account()
    past_tickets = Private(session['token']).list_tickets(when='past')
    upcoming_tickets = Private(session['token']).list_tickets(when='upcoming')
    return render_template(
        'account.html',
        account=account,
        past_tickets=past_tickets,
        upcoming_tickets=upcoming_tickets
    )

@app.route('/cart')
def cart():
    """Cart page."""
    return render_template('cart.html')

@app.route('/checkout')
def checkout():
    """Checkout page."""
    return render_template('checkout.html')

@app.route('/ticket/<code>')
def ticket(code):
    """Ticket page."""
    return render_template('ticket.html')

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
    event = pub.get_event(id)
    return render_template('event.html', event=event)
