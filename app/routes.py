from functools import wraps
from decimal import Decimal
from hashlib import sha256
from datetime import date, datetime
from operator import itemgetter
import os
import json
import time

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

if os.environ.get('FLASK_ENV') == 'development':
    stripe.api_key = STRIPE_TEST_KEYS['secret_key']
    CLIENT_ID = 'ca_GKn0d7PHnhqAuTBEdAGx2fwMl4ooviU7'
else:
    stripe.api_key = STRIPE_LIVE_KEYS['secret_key']
    CLIENT_ID = 'ca_GKn0ZjPHVrd0U8kCOXg66DDj5uykj1Do'

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
            event_id = ticket_type['slug'].split('-')[0]
            ticket_type['event'] = pub.get_event(event_id)['name']
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
        address_country = request.form[
            'register_artist_promoter_form-country_code'
        ]
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
                address_country=address_country, description=description,
                facebook=facebook, instagram=instagram, soundcloud=soundcloud,
                spotify=spotify, twitter=twitter, website=website,
                youtube=youtube, image=image
            )
        if group == 'promoter':
            user = pub.create_promoter(
                email=email, password=password, name=name, phone=phone,
                address_country=address_country, description=description,
                facebook=facebook, instagram=instagram, soundcloud=soundcloud,
                spotify=spotify, twitter=twitter, website=website,
                youtube=youtube, image=image
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

def append_to_events(slug, event_id=None):
    """Appends tickets sold information to event dictionary."""
    if event_id:
        events = [pub.get_event(event_id=event_id)]
    else:
        events = pub.list_events(
            promoter=slug, when='upcoming'
        )
    tickets = Private(session['token']).list_tickets(owner=slug)
    for event in events:
        event['tickets_sold'] = []
        for tally in event['lineup']:
            for ticket_type in event['ticket_types']:
                votes = 0
                if tickets:
                    for ticket in tickets:
                        if event_id:
                            tally_slug = tally['slug']
                        else:
                            tally_slug = tally['tally']
                        if ticket['vote'] == tally_slug \
                        and ticket['ticket_type_slug'] == ticket_type['slug']:
                            votes += 1
                else:
                    if event_id:
                        tally_slug = tally['slug']
                    else:
                        tally_slug = tally['tally']
                event['tickets_sold'].append(
                    {
                        'event_id': event['id'],
                        'artist': tally['artist'],
                        'tally': tally_slug,
                        'ticket_type': ticket_type['name'],
                        'ticket_type_slug': ticket_type['slug'],
                        'tickets_remaining': ticket_type['tickets_remaining'],
                        'price': ticket_type['price'],
                        'votes': votes
                    }
                )
    return events


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

@app.route('/_clear_cart')
def clear_cart():
    session.pop('cart')
    return jsonify(result=True)

@app.route('/_vote')
def vote():
    code = request.args.get('code')
    tally = request.args.get('tally')
    ticket = Private(session['token']).vote_ticket(code, tally)['json']
    return jsonify(result=ticket)

@app.route('/_set_default_card')
def set_default_card():
    card = request.args.get('card')
    stripe_id = request.args.get('stripe_id')
    customer = stripe.Customer.modify(
        stripe_id, invoice_settings={'default_payment_method': card}
    )
    return jsonify(result=customer)

@app.route('/_remove_card')
def remove_card():
    card = request.args.get('card')
    removed_card = stripe.PaymentMethod.detach(card)
    return jsonify(result=removed_card)


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
    print('\n')
    print('s' * 80)
    print(session)
    print('s' * 80)
    print('\n')
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

@app.route('/list/<category>/<when>')
def lists(category, when):
    """List all public objects in the database."""
    if category == 'events':
        data = pub.list_events(when=when)
        return render_template(
            'list_events.html', category=category, data=data, when=when
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
    artists = []
    for event in events:
        event_ids.append(event['id'])
    all_tallies = pub.list_tallies()
    for tally in all_tallies:
        if tally['event_id'] in event_ids:
            tallies.append(tally)
    for tally in tallies:
        entry = {
                    'artist': tally['artist'],
                    'slug': tally['artist_slug'],
                    'tallies': []
                }
        if entry not in artists:
            artists.append(entry)
    for artist in artists:
        for tally in tallies:
            if tally['artist'] == artist['artist']:
                artist['tallies'].append(tally)
    artists = sorted(artists, key=itemgetter('artist'))
    venues = pub.list_venues()['json']
    ticket_types = sorted(
        Private(session['token']).list_ticket_types(),
        key=itemgetter('event_start_date'),
        reverse=True
    )
    tickets = []
    for ticket in Private(session['token']).list_tickets(): 
        if ticket['vote']:
            ticket['lineup'] = None
        else:
            ticket['lineup'] = pub.list_tallies(event_id=ticket['event_id'])
        tickets.append(ticket)
    return render_template(
        'dashboard.html',
        account=account,
        events=events,
        artists=artists,
        venues=venues,
        ticket_types=ticket_types,
        tickets=tickets
    )

@app.route('/create/<category>', methods=['GET', 'POST'])
@app.route('/create/<category>/<int:event_id>', methods=['GET', 'POST'])
@app.route('/create/<category>/<string:card_id>', methods=['GET', 'POST'])
@login_required
def create(category, event_id=None, card_id=None):
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
            address_country = request.form['country_code']
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
                    address_country=address_country,
                    description=description, facebook=facebook,
                    instagram=instagram, soundcloud=soundcloud,
                    spotify=spotify, twitter=twitter, website=website,
                    youtube=youtube, image=path
                )
                if str(artist['status']).startswith('2'):
                    messages.append('Artist created successfully.')
                else:
                    messages.append(artist['json'].values())
            else:
                messages.append('Invalid phone number.')
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
            lineup = request.form.getlist('lineup-select')
            image = request.files['image']
            path = image_to_path(image)
            event = Private(session['token']).create_event(
                name=name, venue=venue, start_date=start_date,
                start_time=start_time, end_date=end_date, end_time=end_time,
                description=description, image=path
            )
            if str(event['status']).startswith('2'):
                for artist in lineup:
                    tally = Private(session['token']).create_tally(
                        artist=artist, event=event['json']['id']
                    )
                    if str(tally['status']).startswith('2'):
                        messages.append('Artist added successfully.')
                    else:
                        messages.append(tally['json'].values())
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
    if category == 'ticket-type':
        if event_id:
            events = [pub.get_event(event_id=event_id)]
        else:
            events = pub.list_events(
                promoter=account['slug'], when='upcoming'
            )
        if request.method == 'POST':
            event = request.form['event-select']
            name = request.form['name-input']
            price = request.form['price-input']
            tickets_remaining = request.form['tickets-remaining-input']
            ticket_type = Private(session['token']).create_ticket_type(
                event=event, name=name, price=price,
                tickets_remaining=tickets_remaining
            )
            if str(ticket_type['status']).startswith('2'):
                messages.append('Ticket type created successfully.')
            else:
                messages.append(event['json'].values())
        return render_template(
            'create_ticket_type.html', events=events, messages=messages
        )
    if category == 'tickets':
        stripe_account_id = su.get_stripe_ids(
            user_id=account['id']
        )['json']['stripe_account_id']
        events = append_to_events(account['slug'], event_id)
        if request.method == 'POST':
            event_id = int(request.form['event-select'])
            for event in events:
                if event['id'] == event_id:
                    tickets_sold = event['tickets_sold']
            amount = 0
            description = []
            for key, value in request.form.items():
                if key != 'event-select':
                    tally = key.split('&')[0]
                    ticket_type = key.split('&')[1]
                    for item in tickets_sold:
                        if item['tally'] == tally \
                        and item['ticket_type_slug'] == ticket_type:
                            change = int(value) - item['votes']
                            if change > 0:
                                description.append(
                                    {
                                        'slug': ticket_type,
                                        'quantity': change,
                                        'vote': tally,
                                        'type': 'otd'
                                    }
                                )
                                amount += (
                                    change * Decimal(item['price']) * 100
                                )
                                new_ticket_type = Private(
                                    session['token']
                                ).edit_ticket_type(
                                    slug=ticket_type,
                                    name=item['ticket_type'],
                                    tickets_remaining=item['tickets_remaining']+change
                                )
            if amount > 0:
                charge = stripe.Charge.create(
                    amount=int(amount),
                    currency='gbp',
                    description=json.dumps(description),
                    source=stripe_account_id,
                )
                time.sleep(5)  
                events = append_to_events(account['slug'], event_id)
                messages.append('Tickets created successfully.')
        return render_template(
            'create_tickets.html',
            event_id=event_id,
            events=events,
            stripe_account_id=stripe_account_id,
            messages=messages
        )
    if category == 'card':
        intent = stripe.SetupIntent.create()
        stripe_id = su.get_stripe_ids(
            user_id=account['id']
        )['json']['stripe_id']
        if not stripe_id:
            customer = stripe.Customer.create(
                email=account['email'],
                name=account['name']
            )
            stripe_id = su.manage_stripe_ids(
                stripe_id=customer.id
            )['json']['stripe_id']
        if card_id:
            if card_id == 'error':
                messages.append('Something went wrong. Please try again and make sure that your payment details are entered correctly.')
                messages.append('If the error persists, please contact us at support@liveleague.co.uk.')
            else:
                attached = stripe.PaymentMethod.attach(
                    card_id, customer=stripe_id
                )
                default_source = stripe.Customer.retrieve(
                    stripe_id
                )['default_source']
                if not default_source:
                    customer = stripe.Customer.modify(
                        stripe_id,
                        invoice_settings={'default_payment_method': card_id}
                    )
                messages.append('Payment method created successfully.')
        return render_template(
            'create_card.html',
            account=account,
            client_secret=intent.client_secret,
            messages=messages
        )

@app.route('/edit/<category>', methods=['GET', 'POST'])
@app.route('/edit/<category>/<int:event_id>', methods=['GET', 'POST'])
@app.route('/edit/<category>/<string:slug>', methods=['GET', 'POST'])
@app.route(
    '/edit/<category>/<int:event_id>/<string:slug>', methods=['GET', 'POST']
)
@app.route('/edit/<category>/<string:slug>/<status>', methods=['GET', 'POST'])
@app.route(
    '/edit/<category>/<int:event_id>/<string:slug>/<status>',
    methods=['GET', 'POST']
)
@login_required
def edit(category, event_id=None, slug=None, status=None):
    """Edit page."""
    account = Private(session['token']).get_account()['json']
    status = Private(session['token']).get_account()['status']
    messages = []
    if not str(status).startswith('2'):
        return redirect(url_for('sign_in'))
    if status == 'success':
        if category == 'ticket-type':
            if slug:
                ticket_types = [pub.get_ticket_type(slug=slug)['json']]
            else:
                ticket_types = Private(session['token']).list_ticket_types()
            if event_id:
                events = [pub.get_event(event_id=event_id)]
            else:
                events = pub.list_events(
                    promoter=account['slug'], when='upcoming'
                )
            messages.append('Ticket type edited successfully.')
            return render_template(
                'edit_ticket_type.html',
                events=events,
                slug=slug,
                ticket_types=ticket_types,
                messages=messages
            )
    else:
        if category == 'venue':
            if not account['is_promoter'] or not account['is_verified']:
                return redirect(url_for('account'))
            else:
                form = VenueForm()
                if slug:
                    venues = [pub.get_venue(slug=slug)['json']]
                else:
                    venues = pub.list_venues()['json']
                if request.method == 'POST':
                    venue = request.form['venue-select']
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
                    venue = Private(session['token']).edit_venue(
                        venue=venue, name=name, description=description,
                        address_line1=address_line1,
                        address_line2=address_line2,
                        address_zip=address_zip, address_city=address_city,
                        address_state=address_state,
                        address_country=address_country,
                        google_maps=google_maps,
                        image=path
                    )
                    if str(venue['status']).startswith('2'):
                        messages.append('Venue edited successfully.')
                        if slug:
                            venues = [
                                pub.get_venue(
                                    slug=venue['json']['slug']
                                )['json']
                            ]
                        else:
                            venues = pub.list_venues()['json']
                    else:
                        messages.append(venue['json'].values())
                return render_template(
                    'edit_venue.html',
                    form=form,
                    venues=venues,
                    messages=messages
                )
        if category == 'event':
            if not account['is_promoter'] or not account['is_verified']:
                return redirect(url_for('account'))
            else:
                form = EventForm()
                if event_id:
                    events = [pub.get_event(event_id=event_id)]
                else:
                    events = pub.list_events(
                        promoter=account['slug'], when='upcoming'
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
                    lineup = request.form.getlist('lineup-select')
                    image = request.files['image']
                    path = image_to_path(image)
                    event = Private(session['token']).edit_event(
                        event=event, name=name, venue=venue,
                        start_date=start_date,
                        start_time=start_time, end_date=end_date,
                        end_time=end_time, description=description, image=path
                    )
                    previous_lineup = []
                    tallies = pub.get_event(
                        event_id=event['json']['id']
                    )['lineup']
                    for tally in tallies:
                        previous_lineup.append(
                            {tally['artist_slug']: tally['slug']}
                        )
                    if str(event['status']).startswith('2'):
                        for artist in lineup:
                            if not any(artist in d for d in previous_lineup):
                                tally = Private(session['token']).create_tally(
                                    artist=artist, event=event['json']['id']
                                )
                                if str(tally['status']).startswith('2'):
                                    messages.append(
                                        'Artist added successfully.'
                                    )
                                else:
                                    messages.append(tally['json'].values())
                        for item in previous_lineup:
                            for artist, slug in item.items():
                                if not any(artist in d for d in lineup):
                                    tally = Private(
                                        session['token']
                                    ).delete_tally(slug=slug)
                                    if str(tally['status']).startswith('2'):
                                        messages.append(
                                            'Artist removed successfully.'
                                        )
                                    else:
                                        messages.append(tally['json'].values())
                        if event_id:
                            events = [pub.get_event(
                                event_id=event['json']['id']
                            )]
                        else:
                            events = pub.list_events(
                                promoter=account['slug'],
                                when='upcoming'
                            )
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
        if category == 'ticket-type':
            if not account['is_promoter'] or not account['is_verified']:
                return redirect(url_for('account'))
            else:
                if slug:
                    ticket_types = [pub.get_ticket_type(slug=slug)['json']]
                else:
                    ticket_types = Private(
                        session['token']
                    ).list_ticket_types()
                if event_id:
                    events = [pub.get_event(event_id=event_id)]
                else:
                    events = pub.list_events(
                        promoter=account['slug'], when='upcoming'
                    )
                if request.method == 'POST':
                    slug = request.form['ticket-type-select']
                    name = request.form['name-input']
                    tickets_remaining = request.form['tickets-remaining-input']
                    ticket_type = Private(session['token']).edit_ticket_type(
                        slug=slug,
                        name=name,
                        tickets_remaining=tickets_remaining
                    )
                    if str(ticket_type['status']).startswith('2'):
                        slug = ticket_type['json']['slug']
                        if event_id:
                            return redirect(url_for(
                                'edit',
                                category='ticket-type',
                                event_id=event_id,
                                slug=slug,
                                status='success'
                            ))
                        else:
                            return redirect(url_for(
                                'edit',
                                category='ticket-type',
                                slug=slug,
                                status='success'
                            ))
                    else:
                        messages.append(ticket_type['json'].values())
                return render_template(
                    'edit_ticket_type.html',
                    events=events,
                    slug=slug,
                    ticket_types=ticket_types,
                    messages=messages
                )
        if category == 'account':
            edit_artist_promoter_form = RegisterArtistPromoterForm(
                prefix='edit_artist_promoter_form'
            )
            edit_user_form = RegisterUserForm(prefix='edit_user_form')
            if account['is_artist'] or account['is_promoter']:
                first_name = None
                last_name = None
            else:
                first_name = account['name'].split()[0]
                last_name = account['name'].split()[1]
            if request.method == 'POST':
                if account['is_artist'] or account['is_promoter']:
                    password = request.form[
                        'edit_artist_promoter_form-password'
                    ]
                    confirm_password = request.form[
                        'edit_artist_promoter_form-confirm_password'
                    ]
                    if password == confirm_password:
                        if password == '':
                            password = None
                        address_country = request.form[
                            'edit_artist_promoter_form-country_code'
                        ]
                        phone = request.form['edit_artist_promoter_form-phone']
                        valid_phone = False
                        if phone:
                            try:
                                phone = phonenumbers.parse(
                                    phone, address_country
                                )
                                if phonenumbers.is_possible_number(phone) and \
                                phonenumbers.is_valid_number(phone):
                                    phone = phonenumbers.format_number(
                                        phone,
                                        phonenumbers.PhoneNumberFormat.INTERNATIONAL
                                    )
                                valid_phone = True
                            except phonenumbers.NumberParseException:
                                messages.append(
                                    'The phone number entered is not valid.'
                                )
                                valid_phone = False
                        if not phone or (phone and valid_phone):
                            email = request.form[
                                'edit_artist_promoter_form-email'
                            ]
                            name = request.form[
                                'edit_artist_promoter_form-name'
                            ]
                            description = request.form[
                                'edit_artist_promoter_form-description'
                            ]
                            facebook = request.form[
                                'edit_artist_promoter_form-facebook'
                            ]
                            instagram = request.form[
                                'edit_artist_promoter_form-instagram'
                            ]
                            soundcloud = request.form[
                                'edit_artist_promoter_form-soundcloud'
                            ]
                            spotify = request.form[
                                'edit_artist_promoter_form-spotify'
                            ]
                            twitter = request.form[
                                'edit_artist_promoter_form-twitter'
                            ]
                            website = request.form[
                                'edit_artist_promoter_form-website'
                            ]
                            youtube = request.form[
                                'edit_artist_promoter_form-youtube'
                            ]
                            image = request.files[
                                'edit_artist_promoter_form-image'
                            ]
                            path = image_to_path(image)
                            account = Private(session['token']).edit_account(
                                email=email, password=password, name=name,
                                phone=phone, address_country=address_country,
                                description=description, facebook=facebook,
                                instagram=instagram, soundcloud=soundcloud,
                                spotify=spotify, twitter=twitter,
                                website=website, youtube=youtube, image=image
                            )
                            if str(account['status']).startswith('2'):
                                account = Private(
                                    session['token']
                                ).get_account()['json']
                                messages.append('Account edited successfully.')
                            else:
                                messages.append(account['json'].values())
                        else:
                            messages.append('Invalid phone number.')
                    else:
                        messages.append('The passwords provided do not match.')
                else:
                    password = request.form['edit_user_form-password']
                    confirm_password = request.form[
                        'edit_user_form-confirm_password'
                    ]
                    if password == confirm_password:
                        if password == '':
                            password = None
                        email = request.form[
                            'edit_user_form-email'
                        ]
                        first_name = request.form['edit_user_form-first_name']
                        last_name = request.form['edit_user_form-last_name']
                        name = first_name + ' ' + last_name
                        account = Private(session['token']).edit_account(
                            email=email, password=password, name=name
                        )
                        if str(account['status']).startswith('2'):
                            account = Private(
                                session['token']
                            ).get_account()['json']
                            messages.append('Account edited successfully.')
                        else:
                            messages.append(account['json'].values())
                    else:
                        messages.append('The passwords provided do not match.')
            return render_template(
                'edit_account.html',
                account=account,
                edit_artist_promoter_form=edit_artist_promoter_form,
                edit_user_form=edit_user_form,
                first_name=first_name,
                last_name=last_name,
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
    code = request.args.get('code')
    stripe_account_id = su.get_stripe_ids(
        user_id=account['id']
    )['json']['stripe_account_id']
    if stripe_account_id:
        express = stripe.Account.create_login_link(stripe_account_id)['url']
        oauth = None
        stripe_account = stripe.Account.retrieve(stripe_account_id)
        currently_due = stripe_account['requirements']['currently_due']
        payouts_enabled = stripe_account['payouts_enabled']
        if not account['is_verified']:
            if not currently_due and payouts_enabled:
                is_verified = su.manage_verification(
                    user_id=account['id'], is_verified=True
                )
                return redirect(url_for('account'))
    else:
        express = None
        if code:
            response = stripe.OAuth.token(
                grant_type='authorization_code',
                code=code,
                assert_capabilities=['card_payments', 'transfers']
            )
            su.manage_stripe_ids(
                user_id=account['id'],
                stripe_account_id=response['stripe_user_id']
            )['json']['stripe_account_id']
            return redirect(url_for('account'))
        if account['phone']:
            phone = phonenumbers.format_number(
                phonenumbers.parse(account['phone'], None),
                phonenumbers.PhoneNumberFormat.NATIONAL
            )
        else:
            phone = account['phone']
        oauth = 'https://dashboard.stripe.com/express/oauth/authorize?' + \
            'response_type=code&client_id=' + CLIENT_ID + \
            '&suggested_capabilities[]=card_payments' + \
            '&suggested_capabilities[]=transfers' + \
            '&stripe_user[email]=' + account['email'] + \
            '&stripe_user[name]=' + account['name'] + \
            '&stripe_user[country]=' + account['address_country'] + \
            '&stripe_user[phone_number]=' + phone + \
            '&scope=read_write&state=' + \
            str(account['id']) + '_' + str(round(time.time()))
    return render_template(
        'account.html',
        account=account,
        past_tickets=past_tickets,
        upcoming_tickets=upcoming_tickets,
        past_events=past_events,
        upcoming_events=upcoming_events,
        stripe_account_id=stripe_account_id,
        express=express,
        oauth=oauth
    )

@app.route('/cart')
def cart():
    """Cart page."""
    cart = load_cart()
    cart_total = calculate_cart_total(cart)
    quantity = 0
    for item in cart:
        quantity += item['quantity']
    return render_template(
        'cart.html',
        cart=cart,
        cart_total=cart_total,
        quantity=quantity
    )

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Checkout page."""
    cart = load_cart()
    cart_total = calculate_cart_total(cart)
    login_form = LoginForm(prefix='login_form')
    register_form = RegisterUserForm(prefix='register_user_form')
    messages = None
    if 'token' in session:
        account = Private(session['token']).get_account()['json']
        status = Private(session['token']).get_account()['status']
        if not str(status).startswith('2'):
            session.pop('token')
            return redirect(url_for('sign_in'))
        total = int(float(cart_total)) * 100
        stripe_customer_id = su.get_stripe_ids(
            user_id=account['id']
        )['json']['stripe_customer_id']
        if not stripe_customer_id:
            customer = stripe.Customer.create(
                email=account['email'],
                name=account['name']
            )
            su.manage_stripe_ids(
                user_id=account['id'], stripe_customer_id=customer.id
            )
            return redirect(url_for('checkout'))
        description = []
        quantity = 0
        if cart:
            for item in cart:
                description.append(
                    {
                        'slug': item['slug'],
                        'quantity': item['quantity'],
                        'vote': '',
                        'type': 'online'
                    }
                )
                quantity += item['quantity']
            transfer_group = str(account['id']) + '_' + str(round(time.time()))
            intent = stripe.PaymentIntent.create(
                amount=total,
                currency='gbp',
                customer=stripe_customer_id,
                description=json.dumps(description),
                transfer_group=transfer_group
            )
            client_secret = intent['client_secret']
        else:
            client_secret = None
    else:
        account = None
        client_secret = None
        quantity = 0
        for item in cart:
            quantity += item['quantity']
    if login_form.validate_on_submit():
        token = sign_in_or_register(method='login', form=request.form)
        if not str(token['status']).startswith('2'):
            messages = token['json'].values()
        else:
            session['token'] = token['json']['token']
            return redirect(url_for('checkout'))
    if register_form.validate_on_submit():
        token = sign_in_or_register(method='register_user', form=request.form)
        if not str(token['status']).startswith('2'):
            messages = token['json'].values()
        else:
            session['token'] = token['json']['token']
            return redirect(url_for('checkout'))
    return render_template(
        'checkout.html',
        account=account,
        cart=cart,
        cart_total=cart_total,
        client_secret=client_secret,
        login_form=login_form,
        register_form=register_form,
        messages=messages,
        quantity=quantity
    )

@app.route('/success', methods=['GET', 'POST'])
def success():
    """Payment successful page."""
    return render_template('success.html')

@app.route('/error', methods=['GET', 'POST'])
def error():
    """Payment error page."""
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

@app.route('/<int:event_id>')
def event(event_id):
    """Event page."""
    event = pub.get_event(event_id=event_id)
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
