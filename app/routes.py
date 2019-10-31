from functools import wraps
from decimal import Decimal
from hashlib import sha256
from datetime import date, datetime
from operator import itemgetter
import os

from flask import render_template, request, session, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import stripe
import phonenumbers

from app import app
from app.wrapper import Public, Private
from app.superuser import Superuser
from app.forms import LoginForm, RegisterUserForm, \
                      RegisterArtistPromoterForm, EmailForm, PasswordForm, \
                      VenueForm, EventForm
from app.keys import STRIPE_TEST_KEYS, STRIPE_LIVE_KEYS

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

stripe.api_key = STRIPE_LIVE_KEYS['secret_key']
pub = Public()
su = Superuser()


########## Helper functions ##########

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.context_processor
def inject_cart_quantities():
    """Puts cart quantities in base.html."""
    cart_quantities = 0
    if 'cart' in session:
        for item in session['cart']:
            cart_quantities += item['quantity']
    return dict(cart_quantities=cart_quantities)

@app.context_processor
def inject_is_promoter():
    """Puts is_promoter in base.html."""
    if 'token' in session:
        account = Private(session['token']).get_account()['json']
        status = Private(session['token']).get_account()['status']
        if not str(status).startswith('2'):
            is_promoter = False
        else:
            if account['is_promoter'] and account['is_verified']:
                is_promoter = True
            else:
                is_promoter = False
    else:
        is_promoter = False
    return dict(is_promoter=is_promoter)

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
            ticket_type = pub.get_ticket_type(item['ticket_type'])['json']
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

def sign_in_or_register(method, form, phone=None, image=None):
    if method == 'login':
        token = pub.get_token(
            email=form['login_form-email'],
            password=form['login_form-password']
        )
    if method == 'register_artist_promoter':
        group = request.form['register_artist_promoter_form-group']
        email = form['register_artist_promoter_form-email']
        password = form['register_artist_promoter_form-password']
        name = form['register_artist_promoter_form-name']
        description = form['register_artist_promoter_form-description']
        facebook = form['register_artist_promoter_form-facebook']
        instagram = form['register_artist_promoter_form-instagram']
        soundcloud = form['register_artist_promoter_form-soundcloud']
        spotify = form['register_artist_promoter_form-spotify']
        twitter = form['register_artist_promoter_form-twitter']
        website = form['register_artist_promoter_form-website']
        youtube = form['register_artist_promoter_form-youtube']
        if group == 'artist':
            user = pub.create_artist(
                email=email, password=password, name=name, phone=phone,
                description=description, facebook=facebook,
                instagram=instagram, soundcloud=soundcloud, spotify=spotify,
                twitter=twitter, website=website, youtube=youtube, image=image
            )
        if group == 'promoter':
            user = pub.create_promoter(
                email=email, password=password, name=name, phone=phone,
                description=description, facebook=facebook,
                instagram=instagram, soundcloud=soundcloud, spotify=spotify,
                twitter=twitter, website=website, youtube=youtube, image=image
            )
        token = pub.get_token(email=email, password=password)
    if method == 'register_user':
        email = form['register_user_form-email']
        password = form['register_user_form-password']
        name = form['register_user_form-first_name'] + ' ' + \
               form['register_user_form-last_name']
        user = pub.create_user(email=email, password=password, name=name)
        token = pub.get_token(email=email, password=password)
    return token

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_path(image):
    """Creates a file path from an image."""
    if image and allowed_file(image.filename):
        path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            secure_filename(image.filename)
        )
        image.save(path)
    else:
        path = None
    return path


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
    ticket = Private(session['token']).vote_ticket(code, tally)['json']
    return jsonify(result=ticket)


########## Error pages ##########

@app.errorhandler(403)
def forbidden(e):
    code = 403
    message = 'Forbidden'
    return render_template('oops.html', code=code, message=message), 403

@app.errorhandler(404)
def not_found(e):
    code = 404
    message = 'Not Found'
    return render_template('oops.html', code=code, message=message), 404

@app.errorhandler(410)
def gone(e):
    code = 410
    message = 'Gone'
    return render_template('oops.html', code=code, message=message), 410

@app.errorhandler(500)
def internal_server_error(e):
    code = 500
    message = 'Internal Server Error'
    return render_template('oops.html', code=code, message=message), 500


########## URL routes ##########

@app.route('/')
def index():
    """Homepage."""
    standings = pub.list_table_rows()
    prize_pool = pub.get_prizes()['json']['total']
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
    register_artist_promoter_form = RegisterArtistPromoterForm(
        prefix='register_artist_promoter_form'
    )
    register_user_form = RegisterUserForm(prefix='register_user_form')
    groups = ["I'm an artist", "I'm a promoter", "I just like to party"]
    errors = None
    page = None
    if login_form.validate_on_submit():
        token = sign_in_or_register(method='login', form=request.form)
        if not str(token['status']).startswith('2'):
            errors = token['json'].values()
        else:
            session['token'] = token['json']['token']
            return redirect(url_for('account'))
    if register_artist_promoter_form.validate_on_submit():
        country_code = request.form[
            'register_artist_promoter_form-country_code'
        ]
        phone = request.form['register_artist_promoter_form-phone']
        try:
            phone = phonenumbers.parse(phone, country_code)
            if phonenumbers.is_possible_number(phone) and \
            phonenumbers.is_valid_number(phone):
                phone = phonenumbers.format_number(
                    phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
            valid_phone = True
        except phonenumbers.NumberParseException:
            errors = [['The phone number entered is not valid.']]
            valid_phone = False
        if valid_phone:
            image = request.files['register_artist_promoter_form-image']
            path = image_to_path(image)
            token = sign_in_or_register(
                method='register_artist_promoter',
                form=request.form,
                phone=phone,
                image=path
            )
            if not str(token['status']).startswith('2'):
                errors = token['json'].values()
            else:
                if image:
                    os.remove(path)
                session['token'] = token['json']['token']
                return redirect(url_for('account'))
    if register_user_form.validate_on_submit():
        token = sign_in_or_register(method='register_user', form=request.form)
        if not str(token['status']).startswith('2'):
            errors = token['json'].values()
        else:
            session['token'] = token['json']['token']
            return redirect(url_for('account'))
    if 'login_form-register' in request.form:
        if request.form['register_artist_promoter_form-group'] == 'artist':
            page = 'register_artist'
        elif request.form['register_artist_promoter_form-group'] == 'promoter':
            page = 'register_promoter'
        elif request.form['register_artist_promoter_form-group'] == 'neither':
            page = 'register_user'
    else:
        page = 'login'
    return render_template(
        'sign_in.html',
        login_form=login_form,
        register_artist_promoter_form=register_artist_promoter_form,
        register_user_form=register_user_form,
        groups=groups,
        errors=errors,
        page=page
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

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page."""
    account = Private(session['token']).get_account()['json']
    status = Private(session['token']).get_account()['status']
    if not str(status).startswith('2'):
        return redirect(url_for('sign_in'))
    else:
        if not account['is_promoter'] or not account['is_verified']:
            return redirect(url_for('account'))
    events = sorted(
        pub.list_events(promoter=account['slug']),
        key=itemgetter('start_date'),
        reverse=True
    )
    event_ids = []
    tallies = []
    for event in events:
        event_ids.append(event['id'])
    all_tallies = pub.list_tallies()
    for tally in all_tallies:
        if tally['event_id'] in event_ids:
            tallies.append(tally)
    '''
    for tally in tallies:
    '''
    return render_template(
        'dashboard.html',
        account=account,
        events=events,
        tallies=tallies
    )

@app.route('/create/<category>', methods=['GET', 'POST'])
@app.route('/create/<category>/<int:event_id>', methods=['GET', 'POST'])
@login_required
def create(category, event_id=None):
    """Create page."""
    account = Private(session['token']).get_account()['json']
    status = Private(session['token']).get_account()['status']
    messages = []
    if not str(status).startswith('2'):
        return redirect(url_for('sign_in'))
    else:
        if not account['is_promoter'] or not account['is_verified']:
            return redirect(url_for('account'))
    if category == 'artist':
        form = RegisterArtistPromoterForm()
        if request.method == 'POST':
            country_code = request.form[
                'country_code'
            ]
            phone = request.form['phone']
            valid_phone = False
            if phone:
                try:
                    phone = phonenumbers.parse(phone, country_code)
                    if phonenumbers.is_possible_number(phone) and \
                    phonenumbers.is_valid_number(phone):
                        phone = phonenumbers.format_number(
                            phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                        )
                    valid_phone = True
                except phonenumbers.NumberParseException:
                    messages.append('The phone number entered is not valid.')
                    valid_phone = False
            if not phone or (phone and valid_phone):
                email = request.form['email']
                name = request.form['name']
                description = request.form['description']
                facebook = request.form['facebook']
                instagram = request.form['instagram']
                soundcloud = request.form['soundcloud']
                spotify = request.form['spotify']
                twitter = request.form['twitter']
                website = request.form['website']
                youtube = request.form['youtube']
                image = request.files['image']
                path = image_to_path(image)
                artist = pub.invite_artist(
                    email=email, name=name, phone=phone,
                    description=description, facebook=facebook,
                    instagram=instagram, soundcloud=soundcloud,
                    spotify=spotify, twitter=twitter, website=website,
                    youtube=youtube, image=path
                )
                if str(artist['status']).startswith('2'):
                    messages.append('Artist created successfully.')
                else:
                    messages.append(artist['json'].values())
        return render_template(
            'create_artist.html', form=form, messages=messages
        )
    if category == 'venue':
        form = VenueForm()
        if form.validate_on_submit():
            name = request.form['name']
            description = request.form['description']
            address_line1 = request.form['address_line1']
            address_line2 = request.form['address_line2']
            address_zip = request.form['address_zip']
            address_state = request.form['address_state']
            address_city = request.form['address_city']
            address_state = request.form['address_state']
            address_country = request.form['address_country']
            google_maps = request.form['google_maps']
            image = request.files['image']
            path = image_to_path(image)
            venue = Private(session['token']).create_venue(
                name=name, description=description,
                address_line1=address_line1, address_line2=address_line2,
                address_zip=address_zip, address_city=address_city,
                address_state=address_state, address_country=address_country,
                google_maps=google_maps, image=path
            )
            if str(venue['status']).startswith('2'):
                messages.append('Venue created successfully.')
            else:
                messages.append(venue['json'].values())
        return render_template(
            'create_venue.html', form=form, messages=messages
        )
    if category == 'event':
        form = EventForm()
        venues = pub.list_venues()['json']
        artists = pub.list_artists()['json']
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            venue = request.form['venue-select']
            start_date = request.form['start_date']
            start_time = request.form['start_time']
            end_date = request.form['end_date']
            end_time = request.form['end_time']
            image = request.files['image']
            path = image_to_path(image)
            event = Private(session['token']).create_event(
                name=name, venue=venue, start_date=start_date,
                start_time=start_time, end_date=end_date, end_time=end_time,
                description=description, image=path
            )
            if str(event['status']).startswith('2'):
                messages.append('Event created successfully.')
            else:
                messages.append(event['json'].values())
        return render_template(
            'create_event.html',
            form=form,
            venues=venues,
            artists=artists,
            messages=messages
        )
    if category == 'ticket':
        account = Private(session['token']).get_account()['json']
        if event_id:
            events = [pub.get_event(id=event_id)]
        else:
            events = pub.list_events(
                promoter=account['slug'], when='current_and_upcoming'
            )
        if request.method == 'POST':
            event = request.form['event-select']
            ticket_type = request.form['type-select']
            quantity = int(request.form['quantity-input'])
            vote = request.form['vote-select']
            if event == 'None':
                messages.append('Please select an event.')
            if ticket_type == 'None':
                messages.append('Please select a ticket type.')
            if event != 'None' and ticket_type != 'None':
                tickets_remaining = pub.get_ticket_type(
                    ticket_type
                )['json']['tickets_remaining']
                if tickets_remaining >= quantity:
                    count = 0
                    while count < quantity:
                        ticket = Private(
                            session['token']
                        ).create_ticket(ticket_type)['json']
                        if vote != 'None':
                            ticket = Private(
                                session['token']
                            ).vote_ticket(ticket['code'], vote)['json']
                            messages.append(
                                f'Ticket "{ticket["code"]}" created - vote has been cast.'
                            )
                        else:
                            messages.append(
                                f'Ticket "{ticket["code"]}" created.'
                            )
                        count += 1
                else:
                    messages.append(
                        '''
                        There aren't enough tickets of this type left.
                        Please add more and try again.
                        '''
                    )
        return render_template(
            'create_ticket.html',
            event_id=event_id,
            events=events,
            messages=messages
        )

@app.route('/edit/<category>', methods=['GET', 'POST'])
@app.route('/edit/<category>/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit(category, event_id=None):
    """Edit page."""
    account = Private(session['token']).get_account()['json']
    status = Private(session['token']).get_account()['status']
    messages = []
    if not str(status).startswith('2'):
        return redirect(url_for('sign_in'))
    if category == 'event':
        if not account['is_promoter'] or not account['is_verified']:
            return redirect(url_for('account'))
        else:
            form = EventForm()
            if event_id:
                events = [pub.get_event(id=event_id)]
            else:
                events = pub.list_events(
                    promoter=account['slug'], when='current_and_upcoming'
                )
            venues = pub.list_venues()['json']
            artists = pub.list_artists()['json']
            if request.method == 'POST':
                event = request.form['event-select']
                name = request.form['name']
                description = request.form['description']
                venue = request.form['venue-select']
                start_date = request.form['start_date']
                start_time = request.form['start_time']
                end_date = request.form['end_date']
                end_time = request.form['end_time']
                image = request.files['image']
                path = image_to_path(image)
                event = Private(session['token']).edit_event(
                    event=event, name=name, venue=venue, start_date=start_date,
                    start_time=start_time, end_date=end_date,
                    end_time=end_time, description=description, image=path
                )
                if str(event['status']).startswith('2'):
                    messages.append('Event edited successfully.')
                else:
                    messages.append(event['json'].values())
            return render_template(
                'edit_event.html',
                events=events,
                venues=venues,
                artists=artists,
                form=form,
                messages=messages
            )

@app.route('/account')
@login_required
def account():
    """Account page."""
    account = Private(session['token']).get_account()['json']
    status = Private(session['token']).get_account()['status']
    if not str(status).startswith('2'):
        session.clear()
        return redirect(url_for('sign_in'))
    past_tickets = []
    upcoming_tickets = []
    if not account['is_promoter']:
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
    register_form = RegisterUserForm(prefix='register_user_form')
    if 'token' in session:
        account = Private(session['token']).get_account()['json']
        status = Private(session['token']).get_account()['status']
        if not str(status).startswith('2'):
            session.pop('token', None)
            return redirect(url_for('sign_in'))
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
            register_form=register_form,
        )
    else:
        account = None
    errors = None
    if login_form.validate_on_submit():
        token = sign_in_or_register(method='login', form=request.form)
        if not str(token['status']).startswith('2'):
            errors = token['json'].values()
        else:
            session['token'] = token['json']['token']
            return redirect(url_for('checkout'))
    if register_form.validate_on_submit():
        token = sign_in_or_register(method='register_user', form=request.form)
        if not str(token['status']).startswith('2'):
            errors = token['json'].values()
        else:
            session['token'] = token['json']['token']
            return redirect(url_for('checkout'))
    return render_template(
        'checkout.html',
        account=account,
        cart=cart,
        cart_total=cart_total,
        login_form=login_form,
        register_form=register_form,
        errors=errors
    )

@app.route('/charge/<intent_id>', methods=['GET', 'POST'])
def charge(intent_id):
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
        account = Private(session['token']).get_account()['json']
        status = Private(session['token']).get_account()['status']
        if not str(status).startswith('2'):
            session.pop('token', None)
            return redirect(url_for('sign_in'))
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
    else:
        return render_template('error.html')

@app.route('/artist/<slug>')
def artist(slug):
    """Artist's public profile."""
    artist = pub.get_artist(slug)['json']
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
    promoter = pub.get_promoter(slug)['json']
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
    venue = pub.get_venue(slug)['json']
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
        account = Private(session['token']).get_account()['json']
        ticket = Private(session['token']).get_ticket(code)
    else:
        account = None
        ticket = pub.get_ticket(code)

    if not str(ticket['status']).startswith('2'):
        return redirect(url_for('index'))
    else:
        ticket = ticket['json']
        price = pub.get_ticket_type(
            ticket['ticket_type_slug']
        )['json']['price']
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

        if not str(ticket['status']).startswith('2'):
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
