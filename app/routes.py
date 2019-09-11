from functools import wraps
from decimal import Decimal
from hashlib import sha256
from datetime import date, datetime

from flask import render_template, request, session, redirect, url_for, jsonify
import stripe

from app import app
from app.wrapper import Public, Private
from app.superuser import Superuser
from app.forms import LoginForm, RegisterForm, EmailForm, PasswordForm

stripe_test_keys = {
  'secret_key': 'sk_test_0fUt8V7Fw8sbW7mgBkt5e3Gl',
  'publishable_key': 'pk_test_4QJqyITTSyRkqahvU1EQ3idM'
}

stripe_live_keys = {
  'secret_key': 'sk_live_ND2BnntF0wajbzHPzdQGW9Tr',
  'publishable_key': 'pk_live_MHlS4I7NN4fGQKiR3JUfSMnZ'
}

stripe.api_key = stripe_live_keys['secret_key']
pub = Public()
su = Superuser()


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

@app.route('/_vote')
def vote():
    code = request.args.get('code')
    tally = request.args.get('tally')
    ticket = Private(session['token']).vote_ticket(code, tally)
    return jsonify(result=ticket)


########## Error pages ##########

@app.errorhandler(403)
def page_not_found(e):
    code = 403
    message = 'Forbidden'
    return render_template('oops.html', code=code, message=message), 403

@app.errorhandler(404)
def page_not_found(e):
    code = 404
    message = 'Not Found'
    return render_template('oops.html', code=code, message=message), 404

@app.errorhandler(410)
def page_not_found(e):
    code = 410
    message = 'Gone'
    return render_template('oops.html', code=code, message=message), 410

@app.errorhandler(500)
def page_not_found(e):
    code = 500
    message = 'Internal Server Error'
    return render_template('oops.html', code=code, message=message), 500

########## URL routes ##########

@app.route('/')
def index():
    """Homepage."""
    standings = pub.list_table_rows()
    prize_pool = 0
    for row in standings:
        if row['points']:
            prize_pool += (row['points'] / 10)
    upcoming_events = pub.list_events(when='upcoming')
    print(session)
    return render_template(
        'index.html',
        standings=standings,
        prize_pool=prize_pool,
        upcoming_events=upcoming_events
    )

@app.route('/social/<platform>')
def social(platform):
    """Social media links."""
    if platform == 'facebook':
        return redirect('https://www.facebook.com/livemusicleague')
    elif platform == 'instagram':
        return redirect('https://www.instagram.com/livemusicleague')
    elif platform == 'twitter':
        return redirect('https://www.twitter.com/livemusicleague')
    else:
        return redirect(url_for('contact'))

@app.route('/about')
def about():
    """About us page."""
    return render_template('about.html')

@app.route('/list/<category>')
def lists(category):
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

@app.route('/verify', methods=['GET', 'POST'])
@app.route('/verify/<error>', methods=['GET', 'POST'])
def verify(error=None):
    """Email verification page."""
    form = EmailForm()
    if form.validate_on_submit():
        secret_hash = su.create_secret(request.form['email'])
        session['email'] = request.form['email']
        session['secret_hash'] = secret_hash['secret_hash']
        return render_template('check_emails.html')
    return render_template('verify.html', form=form, error=error)

@app.route('/reset/<secret_code>', methods=['GET', 'POST'])
def reset(secret_code):
    """Password reset page."""
    if 'secret_hash' in session:
        if sha256(secret_code.encode()).hexdigest() == session['secret_hash']:
            form = PasswordForm()
            if form.validate_on_submit():
                password = su.manage_password(
                    session['email'], request.form['password']
                )
                session.pop('email')
                session.pop('secret_hash')
                return redirect(url_for('sign_in'))
            return render_template('reset.html', form=form)
        else:
            error = '''
                    The email link is invalid or has expired.
                    Please try again.
                    '''
            return redirect(url_for('verify', error=error))
    else:
        error = 'The email link is invalid or has expired. Please try again.'
        return redirect(url_for('verify', error=error))

@app.route('/account')
@login_required
def account():
    account = Private(session['token']).get_account()
    if isinstance(account, int):
        session.clear()
        return redirect(url_for('sign_in'))
    past_tickets = []
    upcoming_tickets = []
    for ticket in Private(session['token']).list_tickets(when='past'):
        ticket['lineup'] = pub.list_tallies(event_id=ticket['event_id'])
        past_tickets.append(ticket)
    for ticket in Private(session['token']).list_tickets(when='upcoming'):
        ticket['lineup'] = pub.list_tallies(event_id=ticket['event_id'])
        upcoming_tickets.append(ticket)
    if account['is_artist']:
        past_events = pub.list_tallies(when='past', slug=account['slug'])
        upcoming_events = pub.list_tallies(
            when='upcoming', slug=account['slug']
        )
    else:
        past_events = None
        upcoming_events = None
    return render_template(
        'account.html',
        account=account,
        past_tickets=past_tickets,
        upcoming_tickets=upcoming_tickets,
        past_events=past_events,
        upcoming_events=upcoming_events
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
    cart = load_cart()
    cart_total = calculate_cart_total(cart)
    login_form = LoginForm(prefix='login_form')
    register_form = RegisterForm(prefix='register_form')
    if 'token' in session:
        account = Private(session['token']).get_account()
        amount = int(float(cart_total)) * 100
        customer = stripe.Customer.create(email=account['email'])
        intent = stripe.PaymentIntent.create(
            amount=amount,
            customer=customer.id,
            description='Ticket purchase',
            currency='gbp',
            confirmation_method='manual',
        )
        return render_template(
            'checkout.html',
            account=account,
            cart=cart,
            cart_total=cart_total,
            intent=intent,
            login_form=login_form,
            register_form=register_form
        )
    else:
        account = None
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
    )

@app.route('/charge/<intent_id>', methods=['POST'])
def charge(intent_id):
    try:
        payment_method = stripe.PaymentMethod.create(
          type='card',
          card={'token': request.form['stripeToken']}
        )
        intent = stripe.PaymentIntent.modify(
            intent_id,
            payment_method=payment_method.id,
            save_payment_method=True
        )
        intent = stripe.PaymentIntent.confirm(intent_id)
        if intent.status == 'succeeded':
            account = Private(session['token']).get_account()
            credit = Decimal(account['credit']) + (Decimal(intent.amount) / 100)
            new_credit = su.manage_credit(account['id'], credit)
            for item in session['cart']:
                quantity = 0
                while quantity < item['quantity']:
                    ticket = Private(
                        session['token']
                    ).create_ticket(item['ticket_type'])
                    quantity += 1
            session.pop('cart', None)
            return redirect(url_for('account'))
    except stripe.error.StripeError as e:
        body = e.json_body
        err  = body.get('error', {})
        print("Status is: %s" % e.http_status)
        print("Type is: %s" % err.get('type'))
        print("Code is: %s" % err.get('code'))
        print("Param is: %s" % err.get('param'))
        print("Message is: %s" % err.get('message'))
        return render_template('error.html')

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

@app.route('/<int:id>')
def event(id):
    """Event page."""
    event = pub.get_event(id)
    if event['end_date'] < str(date.today()) or \
    (event['end_date'] == str(date.today()) and \
    event['end_time'] < str(datetime.now().time())):
        past = True
    else:
        past = False
    tickets = None
    for ticket_type in event['ticket_types']:
        if ticket_type['tickets_remaining'] > 0:
            tickets = True
    return render_template(
        'event.html', event=event, past=past, tickets=tickets
    )

@app.route('/<code>', methods=['GET', 'POST'])
def ticket(code):
    """Ticket page."""
    if 'token' in session:
        account = Private(session['token']).get_account()
        ticket = Private(session['token']).get_ticket(code)
    else:
        account = None
        ticket = pub.get_ticket(code)

    if isinstance(ticket, int):
        return redirect(url_for('index'))
    else:
        price = pub.get_ticket_type(ticket['ticket_type_slug'])['price']
        lineup = pub.list_tallies(event_id=ticket['event_id'])
        form = EmailForm()
        if form.validate_on_submit():
            user = pub.user_exists(request.form['email'])
            if user['exists']:
                session['email'] = request.form['email']
                return redirect(url_for('ticket_sign_in', code=code))
            else:
                temporary_user = pub.create_temporary_user(
                    request.form['email']
                )
                if 'password' in temporary_user:
                    token = pub.get_token(
                        email=temporary_user['email'],
                        password=temporary_user['password']
                    )
                    session['token'] = token['token']
                    return redirect(url_for('ticket', code=code))

        return render_template(
            'ticket.html',
            account=account,
            ticket=ticket,
            price=price,
            lineup=lineup,
            form=form
        )

@app.route('/<code>/sign-in', methods=['GET', 'POST'])
def ticket_sign_in(code):
    """Ticket password page."""
    if 'email' not in session:
        return redirect(url_for('ticket', code=code))
    else:
        if 'token' in session:
            account = Private(session['token']).get_account()
            ticket = Private(session['token']).get_ticket(code)
        else:
            account = None
            ticket = pub.get_ticket(code)

        if isinstance(ticket, int):
            return redirect(url_for('index'))
        else:
            price = pub.get_ticket_type(ticket['ticket_type_slug'])['price']
            lineup = pub.list_tallies(event_id=ticket['event_id'])
            form = PasswordForm()
            if form.validate_on_submit():
                token = pub.get_token(
                    email=session['email'],
                    password=request.form['password']
                )
                session.pop('email')
                session['token'] = token['token']
                return redirect(url_for('ticket', code=code))

            return render_template(
                'ticket_sign_in.html',
                account=account,
                ticket=ticket,
                price=price,
                lineup=lineup,
                form=form
            )

@app.route('/contact')
def contact():
    """Contact page."""
    return render_template('contact.html')
