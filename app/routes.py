from functools import wraps
from decimal import Decimal

from flask import render_template, request, session, redirect, url_for, jsonify
import stripe

from app import app
from app.wrapper import Public, Private
from app.forms import LoginForm, RegisterForm, AddressForm

stripe_keys = {
  'secret_key': 'sk_test_FVPFR9bPlCAkzQNEM4tfPUHC',
  'publishable_key': 'pk_test_ZVBSjZUloB7yZkku3XtHO7el'
}

stripe.api_key = stripe_keys['secret_key']
pub = Public()


########## Helper functions ##########

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.context_processor
def inject_cart_quantities():
    cart_quantities = 0
    if 'cart' in session:
        for item in session['cart']:
            cart_quantities += item['quantity']
    return dict(cart_quantities=cart_quantities)

def login_required(f):
    """Checks that a user is signed in."""
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'token' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('sign_in'))
    return wrap

def load_cart():
    """Fetches the ticket information for a cart (session list)."""
    cart = []
    if 'cart' in session:
        for item in session['cart']:
            ticket_type = pub.get_ticket_type(item['ticket_type'])
            ticket_type['price'] = Decimal(ticket_type['price'])
            ticket_type['quantity'] = item['quantity']
            id = ticket_type['slug'].split('-')[0]
            ticket_type['event'] = pub.get_event(id)['name']
            cart.append(ticket_type)
    return cart

def calculate_cart_total(cart):
    """Calculates the total value of a cart."""
    cart_total = 0
    for item in cart:
        cart_total += (item['quantity'] * item['price'])
    return cart_total

def sign_in_or_register(method, form):
    if method == 'login':
        token = pub.get_token(
            email=form['login_form-email'],
            password=form['login_form-password']
        )
        session['token'] = token['token']
    if method == 'register':
        email = form['register_form-email']
        password = form['register_form-password']
        name = form['register_form-first_name'] + ' ' + \
               form['register_form-last_name']
        user = pub.create_user(email=email, password=password, name=name)
        token = pub.get_token(email=email, password=password)
        session['token'] = token['token']


########## AJAX functions ##########

@app.route('/_add_to_cart')
def add_to_cart():
    ticket_type = request.args.get('ticket_type')
    quantity = int(request.args.get('quantity'))
    if 'cart' not in session:
        session['cart'] = []
    already_in_cart = False
    for item in session['cart']:
        if item['ticket_type'] == ticket_type:
            item['quantity'] += quantity
            already_in_cart = True
    cart_item = {'ticket_type': ticket_type, 'quantity': quantity}
    if not already_in_cart:
        session['cart'].append(cart_item)
    return jsonify(result=cart_item)

@app.route('/_remove_from_cart')
def remove_from_cart():
    ticket_type = request.args.get('ticket_type')
    for item in session['cart']:
        if item['ticket_type'] == ticket_type:
            session['cart'].remove(item)
    return jsonify(result=session['cart'])


########## URL routes ##########

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

@app.route('/sign-in/', methods=['GET', 'POST'])
def sign_in():
    """Sign-in/registration page."""
    login_form = LoginForm(prefix='login_form')
    register_form = RegisterForm(prefix='register_form')
    if login_form.validate_on_submit():
        sign_in_or_register(method='login', form=request.form)
        return redirect(url_for('account'))
    if register_form.validate_on_submit():
        sign_in_or_register(method='register', form=request.form)
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
    cart = load_cart()
    cart_total = calculate_cart_total(cart)
    return render_template('cart.html', cart=cart, cart_total=cart_total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Checkout page."""
    if 'token' in session:
        account = Private(session['token']).get_account()
    else:
        account = None
    cart = load_cart()
    cart_total = calculate_cart_total(cart)
    login_form = LoginForm(prefix='login_form')
    register_form = RegisterForm(prefix='register_form')
    if login_form.validate_on_submit():
        sign_in_or_register(method='login', form=request.form)
        return redirect(url_for('checkout'))
    if register_form.validate_on_submit():
        sign_in_or_register(method='register', form=request.form)
        return redirect(url_for('checkout'))
    return render_template(
        'checkout.html',
        account=account,
        cart=cart,
        cart_total=cart_total,
        login_form=login_form,
        register_form=register_form,
        key=stripe_keys['publishable_key']
    )

@app.route('/charge/<email>/<total>', methods=['POST'])
def charge(email, total):
    try:
        amount = int(float(total)) * 100    # amount in pence
        customer = stripe.Customer.create(
            email=email
        )
        stripe.PaymentIntent.create(
            amount=amount,
            customer=customer.id,
            description='Ticket purchase',
            currency='gbp',
        )
        session.pop('cart', None)
        return render_template('charge.html', amount=amount)
    except stripe.error.StripeError as e:
        body = e.json_body
        err  = body.get('error', {})
        print("Status is: %s" % e.http_status)
        print("Type is: %s" % err.get('type'))
        print("Code is: %s" % err.get('code'))
        # param is '' in this case
        print("Param is: %s" % err.get('param'))
        print("Message is: %s" % err.get('message'))
        return render_template('error.html')

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
