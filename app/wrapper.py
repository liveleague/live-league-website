from datetime import date, datetime, timedelta
from operator import itemgetter
import requests
import os

if os.environ.get('FLASK_ENV') == 'development':
    API_URL = 'http://157.245.44.130:8000/v1'
else:
    API_URL = 'https://api.liveleague.co.uk/v1'

def image_to_files(image):
    """Helper function to get 'files' from an image."""
    if image:
        files = {'image': open(image, 'rb')}
    else:
        files = None
    return files


class Public(object):
    """Interact with the public API."""

    def __init__(self):
        self.today = str(date.today())
        self.yesterday = str(date.today()  - timedelta(days=1))
        self.now = str(datetime.now().time())

    def api_call(self, endpoint, method='get', json=None, files=None):
        """Makes an API call to the back-end server."""
        if files:
            r = requests.request(
                method, API_URL + endpoint, data=json, files=files
            )
        else:
            r = requests.request(
                method, API_URL + endpoint, json=json
            )
        return {'status': r.status_code, 'json': r.json()}

    def user_exists(self, email):
        """Check if an email address belongs to a user."""
        json = {'email': email}
        exists = self.api_call('/user/exists/', 'post', json)
        return exists

    def create_user(self, email, password, name):
        """Create a user."""
        json = {'email': email, 'password': password, 'name': name}
        user = self.api_call('/user/create/', 'post', json)
        return user

    def create_temporary_user(self, email):
        """Create a temporary user."""
        json = {'email': email}
        temporary_user = self.api_call('/user/create/temporary/', 'post', json)
        return temporary_user

    def create_artist(self, email, password, name, phone=None,
                      address_country=None, description=None, facebook=None,
                      instagram=None, soundcloud=None, spotify=None,
                      twitter=None, website=None, youtube=None, image=None):
        """Create an artist."""
        json = {
            'email': email, 'password': password, 'name': name, 'phone': phone,
            'address_country': address_country, 'description': description,
            'facebook': facebook, 'instagram': instagram,
            'soundcloud': soundcloud, 'spotify': spotify, 'twitter': twitter,
            'website': website, 'youtube': youtube
        }
        files = image_to_files(image)
        artist = self.api_call('/user/create/artist/', 'post', json, files)
        return artist

    def invite_artist(self, email, name, phone=None, address_country=None,
                      description=None, facebook=None, instagram=None,
                      soundcloud=None, spotify=None, twitter=None,
                      website=None, youtube=None, image=None):
        """Invite an artist."""
        json = {
            'email': email, 'name': name, 'phone': phone,
            'address_country': address_country, 'description': description,
            'facebook': facebook, 'instagram': instagram,
            'soundcloud': soundcloud, 'spotify': spotify, 'twitter': twitter,
            'website': website, 'youtube': youtube
        }
        files = image_to_files(image)
        artist = self.api_call('/user/invite/artist/', 'post', json, files)
        return artist

    def create_promoter(self, email, password, name, phone, address_country,
                        description=None, facebook=None, instagram=None,
                        soundcloud=None, spotify=None, twitter=None,
                        website=None, youtube=None, image=None):
        """Create a promoter."""
        json = {
            'email': email, 'password': password, 'name': name, 'phone': phone,
            'address_country': address_country, 'description': description,
            'facebook': facebook, 'instagram': instagram,
            'soundcloud': soundcloud, 'spotify': spotify, 'twitter': twitter,
            'website': website, 'youtube': youtube
        }
        files = image_to_files(image)
        promoter = self.api_call('/user/create/promoter/', 'post', json, files)
        return promoter

    def get_prizes(self):
        """Retrieve the current prize pool."""
        prizes = self.api_call('/league/prizes/')
        return prizes

    def get_token(self, email, password):
        """Retrieve a token or create one for the first time."""
        json = {'email': email, 'password': password}
        token = self.api_call('/user/token/', 'post', json)
        return token

    def get_artist(self, slug):
        """Retrieve an artist."""
        artist = self.api_call('/user/artist/' + slug)
        return artist

    def get_promoter(self, slug):
        """Retrieve a promoter."""
        promoter = self.api_call('/user/promoter/' + slug)
        return promoter

    def get_venue(self, slug):
        """Retrieve a venue."""
        venue = self.api_call('/league/venue/' + slug)
        return venue

    def get_event(self, event_id):
        """Retrieve a event."""
        response = self.api_call('/league/event/' + str(event_id))
        event = response['json']
        if 'lineup' in event:
            lineup = event['lineup']
            tallies = []
            for item in lineup:
                artist = item['artist']
                artist_slug = item['artist_slug']
                tally = self.get_tally(event_id, artist_slug)['json']
                tally['artist_slug'] = artist_slug
                tallies.append(tally)
            event['lineup'] = tallies
        return event

    def get_tally(self, event_id, artist_slug):
        """Retrieve a tally."""
        tally = self.api_call(
            '/league/tally/' + str(event_id) + '-' + artist_slug
        )
        return tally

    def get_ticket(self, code):
        """Retrieve a ticket that is unowned."""
        ticket = self.api_call('/league/ticket/' + code)
        return ticket

    def get_ticket_type(self, slug):
        """Retrieve a tally."""
        ticket_type = self.api_call('/league/ticket-type/' + slug)
        return ticket_type
    
    def list_artists(self):
        """List artists."""
        artists = self.api_call('/user/list/artists/')
        return artists
    
    def list_venues(self):
        """List venues."""
        venues = self.api_call('/league/list/venues/')
        return venues

    def list_events(self, promoter='', venue='', when='all'):
        """List events."""
        if when == 'past':
            date_filter = 'end_date__lt=' + self.today
        elif when == 'upcoming':
            date_filter = 'start_date__gt=' + self.yesterday
        else:
            date_filter = ''
        url = '/league/list/events/?ordering=start_date&' + date_filter + \
              '&promoter=' + promoter + '&venue=' + venue
        events = self.api_call(
            '/league/list/events/?ordering=start_date&' + date_filter + \
            '&promoter=' + promoter + '&venue=' + venue
        )['json']
        return events

    def list_tallies(self, slug='', event_id='', when='all'):
        """List tallies (lineup entries) for artists in the league."""
        response = self.api_call(
            '/league/list/tallies/?ordering=event__start_date&artist=' + \
            slug + '&event=' + str(event_id)
        )
        tallies = []
        for tally in response['json']:
            if when == 'past':
                if tally['event_end_date'] < self.today:
                    tallies.append(tally)
            elif when == 'upcoming':
                if tally['event_start_date'] > self.yesterday:
                    tallies.append(tally)
            else:
                tallies.append(tally)
        return tallies

    def list_table_rows(self):
        """List table rows for artists in the league."""
        response = self.api_call('/league/list/table-rows/?ordering=-points')
        table_rows = []
        for item in response['json']:
            table_row = {}
            for key in item:
                if key == 'points' or key == 'event_count':
                    if item[key] is None:
                        table_row[key] = 0
                    else:
                        table_row[key] = item[key]
                else:
                    table_row[key] = item[key]
            table_rows.append(table_row)
        table_rows = sorted(table_rows, key=itemgetter('name'))
        table_rows = sorted(
            table_rows, key=itemgetter('event_count'), reverse=True
        )
        table_rows = sorted(
            table_rows, key=itemgetter('points'), reverse=True
        )
        return table_rows


class Private(object):
    """Interact with the private API."""

    def __init__(self, token):
        self.token = token
        self.today = str(date.today())
        self.yesterday = str(date.today()  - timedelta(days=1))
        self.now = str(datetime.now().time())

    def api_call(self, endpoint, method='get', json=None, files=None):
        """Makes an API call to the back-end server."""
        headers = {
            'Authorization': 'Token ' + self.token
        }
        if files:
            r = requests.request(
                method, API_URL + endpoint, headers=headers, data=json,
                files=files
            )
        else:
            r = requests.request(
                method, API_URL + endpoint, headers=headers, json=json
            )
        if method == 'delete':
            return {'status': r.status_code, 'json': ''}
        else:
            return {'status': r.status_code, 'json': r.json()}

    def create_venue(self, name, address_line1, address_zip, address_city,
                     address_country, description=None, address_line2=None,
                     address_state=None, google_maps=None, image=None):
        """Create a venue."""
        json = {
            'name': name, 'description': description,
            'address_line1': address_line1, 'address_line2': address_line2,
            'address_zip': address_zip, 'address_city': address_city,
            'address_state': address_state, 'address_country': address_country,
            'google_maps': google_maps
        }
        files = image_to_files(image)
        venue = self.api_call('/league/create/venue/', 'post', json, files)
        return venue

    def create_event(self, name, venue, start_date, start_time, end_date,
                     end_time, description=None, image=None):
        """Create an event."""
        json = {
            'name': name, 'venue': venue, 'start_date': start_date,
            'start_time': start_time, 'end_date': end_date,
            'end_time': end_time, 'description': description
        }
        files = image_to_files(image)
        event = self.api_call('/league/create/event/', 'post', json, files)
        return event

    def create_tally(self, artist, event):
        """Create a tally."""
        json = {'artist': artist, 'event': event}
        tally = self.api_call('/league/create/tally/', 'post', json)
        return tally

    def create_ticket_type(self, event, name, price, tickets_remaining=None):
        """Create a ticket type."""
        json = {
            'event': event, 'name': name, 'price': price,
            'tickets_remaining': tickets_remaining
        }
        ticket_type = self.api_call(
            '/league/create/ticket-type/', 'post', json
        )
        return ticket_type

    def create_ticket(self, ticket_type):
        """Create a ticket."""
        json = {'ticket_type': ticket_type}
        ticket = self.api_call('/league/create/ticket/', 'post', json)
        return ticket

    def edit_venue(self, venue, name, address_line1, address_zip, address_city,
                   address_country, description=None, address_line2=None,
                   address_state=None, google_maps=None, image=None):
        """Edit a venue."""
        json = {
            'name': name, 'description': description,
            'address_line1': address_line1, 'address_line2': address_line2,
            'address_zip': address_zip, 'address_city': address_city,
            'address_state': address_state, 'address_country': address_country,
            'google_maps': google_maps
        }
        files = image_to_files(image)
        venue = self.api_call(
            '/league/edit/venue/' + venue + '/', 'patch', json, files
        )
        return venue

    def edit_event(self, event, name, venue, start_date, start_time, end_date,
                   end_time, description=None, image=None):
        """Edit an event."""
        json = {
            'name': name, 'venue': venue, 'start_date': start_date,
            'start_time': start_time, 'end_date': end_date,
            'end_time': end_time, 'description': description
        }
        files = image_to_files(image)
        event = self.api_call(
            '/league/edit/event/' + event + '/', 'patch', json, files
        )
        return event

    def delete_tally(self, slug):
        """Create a tally."""
        json = None
        tally = self.api_call(
            '/league/delete/tally/' + slug + '/', 'delete', json
        )
        return tally

    def edit_ticket_type(self, slug, name=None, tickets_remaining=None):
        """Edit a ticket type."""
        json = {'name': name, 'tickets_remaining': tickets_remaining}
        ticket_type = self.api_call(
            '/league/edit/ticket-type/' + slug + '/', 'patch', json
        )
        return ticket_type

    def edit_account(self, email=None, password=None, name=None, phone=None,
                     stripe_id=None, address_country=None, description=None,
                     facebook=None, instagram=None, soundcloud=None,
                     spotify=None, twitter=None, website=None, youtube=None,
                     image=None):
        """Edit the user's account."""
        json = {}
        for param in ['email', 'password', 'name', 'phone', 'stripe_id',
                      'address_country', 'description', 'facebook',
                      'instagram', 'soundcloud', 'spotify', 'twitter',
                      'website', 'youtube']:
            if eval(param) is not None:
                json[param] = eval(param)
        files = image_to_files(image)
        account = self.api_call('/user/me/', 'patch', json, files)
        return account

    def get_account(self):
        """Retrieve the user's account."""
        account = self.api_call('/user/me/')
        return account
    
    def update_address_zip(self):
        """Update the user's postcode."""
        json = {'address_zip': address_zip}
        address_zip = self.api_call('/user/me/', 'patch', json)
        return address_zip

    def vote_ticket(self, code, vote):
        """Vote."""
        json = {'vote': vote}
        ticket = self.api_call(
            '/league/vote/ticket/' + code + '/', 'patch', json
        )
        return ticket

    def get_ticket(self, code):
        """Retrieve a ticket that is owned by the user."""
        ticket = self.api_call('/league/ticket/' + code)
        return ticket

    def list_tickets(self, when='all', owner=''):
        """List the user's tickets."""
        response = self.api_call(
            '/league/list/tickets?ordering=-id&owner=' + owner
        )
        tickets = []
        for ticket in response['json']:
            if when == 'past':
                if ticket['event_end_date'] < self.today:
                    tickets.append(ticket)
            elif when == 'upcoming':
                if ticket['event_start_date'] > self.yesterday:
                    tickets.append(ticket)
            else:
                tickets.append(ticket)
        return tickets

    def list_ticket_types(self, event_id=None, when='all'):
        """List the user's ticket types (promoters only)."""
        response = self.api_call('/league/list/ticket-types')
        ticket_types = []
        for ticket_type in response['json']:
            if when == 'past':
                if ticket_type['event_end_date'] < self.today:
                    ticket_types.append(ticket_type)
            elif when == 'upcoming':
                if ticket_type['event_start_date'] > self.yesterday:
                    ticket_types.append(ticket_type)
            else:
                ticket_types.append(ticket_type)
        return ticket_types
