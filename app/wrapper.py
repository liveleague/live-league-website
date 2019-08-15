from datetime import date, datetime, timedelta
import requests


class Public(object):
    """Interact with the public API."""

    def __init__(self):
        self.today = str(date.today())
        self.yesterday = str(date.today()  - timedelta(days=1))

    def api_call(self, endpoint, method='GET', data=None):
        """Makes an API call to the back-end server."""
        if method == 'GET':
            return requests.get('http://46.101.31.33:8000' + endpoint).json()
        elif method == 'POST':
            return requests.post(
                'http://46.101.31.33:8000' + endpoint, data
            ).json()

    def get_token(self, email, password):
        """Retrieve a token or create one for the first time."""
        data = {'email': email, 'password': password}
        token = self.api_call('/user/token/', 'POST', data=data)
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
        event = self.api_call('/league/event/' + id)
        print(event)
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

    def list_tallies(self, slug, when='all'):
        """List tallies (events and votes) for artists in the league."""
        response = self.api_call(
            '/league/list/tallies/?artist=' + slug
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

    def list_events(self, promoter=None, venue=None, when='all'):
        """
        List events.
        Date format = 'yyyy-mm-dd'
        """
        if promoter:
            promoter = '&promoter=' + promoter
        else:
            promoter = ""
        if venue:
            venue = '&venue=' + venue
        else:
            venue = ""

        if when == 'upcoming':
            events = self.api_call(
                '/league/list/events/?ordering=start_date&start_date__gt=' + \
                self.yesterday + promoter + venue
            )
        elif when == 'past':
            events = self.api_call(
                '/league/list/events/?ordering=start_date&start_date__lt=' + \
                self.today + promoter + venue
            )
        else:
            events = self.api_call(
                '/league/list/events/?ordering=start_date' + promoter + venue
            )
        return events
