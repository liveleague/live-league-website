from datetime import date, datetime, timedelta
import requests

API_URL = 'https://api.liveleague.events'


class Public(object):
    """Interact with the public API."""

    def __init__(self):
        self.today = str(date.today())
        self.yesterday = str(date.today()  - timedelta(days=1))

    def api_call(self, endpoint, method='GET', json=None):
        """Makes an API call to the back-end server."""
        if method == 'GET':
            r = requests.get(API_URL + endpoint)
        elif method == 'POST':
            r = requests.post(API_URL + endpoint, json=json)
        if str(r.status_code).startswith('2'):
            return r.json()
        else:
            return r.status_code

    def create_user(self, email, password, name):
        """Create a user."""
        json = {'email': email, 'password': password, 'name': name}
        user = self.api_call('/user/create/', 'POST', json)
        return user

    def get_token(self, email, password):
        """Retrieve a token or create one for the first time."""
        json = {'email': email, 'password': password}
        token = self.api_call('/user/token/', 'POST', json)
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

    def get_event(self, id):
        """Retrieve a event."""
        event = self.api_call('/league/event/' + str(id))
        if 'lineup' in event:
            id
            lineup = event['lineup']
            tallies = []
            for item in lineup:
                artist = item['artist']
                artist_slug = item['artist_slug']
                tally = self.get_tally(id, artist_slug)
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

    def list_tallies(self, slug='', event_id='', when='all'):
        """List tallies (lineup entries) for artists in the league."""
        response = self.api_call(
            '/league/list/tallies/?artist=' + slug + '&event=' + str(event_id)
        )
        tallies = []
        for tally in response:
            if (when == 'past' and tally['event_start_date'] < self.today) or \
               (when == 'upcoming' and tally['event_start_date'] > self.yesterday) or \
               when not in ['past', 'upcoming']:
                    tallies.append(tally)
        return tallies

    def list_table_rows(self):
        """List table rows for artists in the league."""
        table_rows = self.api_call('/league/list/table-rows/?ordering=-points')
        return table_rows

    def list_events(self, promoter='', venue='', when='all'):
        """List events."""
        extras = '&promoter=' + promoter + '&venue=' + venue
        if when == 'upcoming':
            events = self.api_call(
                '/league/list/events/?ordering=start_date&start_date__gt=' + \
                self.yesterday + extras
            )
        elif when == 'past':
            events = self.api_call(
                '/league/list/events/?ordering=start_date&start_date__lt=' + \
                self.today + extras
            )
        else:
            events = self.api_call(
                '/league/list/events/?ordering=start_date' + promoter + venue
            )
        return events


class Private(object):
    """Interact with the private API."""

    def __init__(self, token):
        self.token = token
        self.today = str(date.today())
        self.yesterday = str(date.today()  - timedelta(days=1))

    def api_call(self, endpoint, method='GET', json=None):
        """Makes an API call to the back-end server."""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token ' + self.token
        }
        if method == 'GET':
            r = requests.get(API_URL + endpoint, headers=headers)
        elif method == 'POST':
            r = requests.post(
                API_URL + endpoint, headers=headers, json=json
            )
        elif method == 'PATCH':
            r = requests.patch(
                API_URL + endpoint, headers=headers, json=json
            )
        if str(r.status_code).startswith('2'):
            return r.json()
        else:
            return r.status_code

    def create_ticket(self, ticket_type):
        """Create a ticket."""
        json = {'ticket_type': ticket_type}
        ticket = self.api_call('/league/create/ticket/', 'POST', json)
        return ticket

    def get_account(self):
        """Retrieve the user's account."""
        account = self.api_call('/user/me')
        return account

    def vote_ticket(self, code, vote):
        """Vote."""
        json = {'vote': vote}
        ticket = self.api_call('/league/vote/ticket/' + code + '/', 'PATCH', json)
        return ticket

    def get_ticket(self, code):
        """Retrieve a ticket that is owned by the user."""
        ticket = self.api_call('/league/ticket/' + code)
        return ticket

    def list_tickets(self, when='all'):
        """List the user's tickets."""
        response = self.api_call('/league/list/tickets?ordering=ticket_type__event__start_date')
        tickets = []
        for ticket in response:
            if (when == 'past' and ticket['event_start_date'] < self.today) or \
               (when == 'upcoming' and ticket['event_start_date'] > self.yesterday) or \
               when not in ['past', 'upcoming']:
                    tickets.append(ticket)
        return tickets
