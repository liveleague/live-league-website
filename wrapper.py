from datetime import date, datetime, timedelta
import requests

def api_call(endpoint):
    """Makes an API call to the back-end server."""
    response = requests.get('http://46.101.31.33:8000' + endpoint).json()
    return response

def get_artist(slug):
    """Retrieve an artist."""
    artist = api_call('/user/artist/' + slug)
    return artist

def list_tallies(when, slug):
    """List tallies (events and votes) for artists in the league."""
    tallies = api_call('/league/list/tallies/?artist=' + slug)
    return tallies

def list_table_rows():
    """List table rows for artists in the league."""
    table_rows = api_call('/league/list/table-rows/?ordering=-points')
    return table_rows

def list_events(when='all'):
    """
    List events.
    Date format = 'yyyy-mm-dd'
    """
    if when == 'upcoming':
        yesterday = str(date.today()  - timedelta(days=1))
        events = api_call(
            '/league/list/events/?ordering=start_date&start_date__gt=' + yesterday
        )
    elif when == 'past':
        events = api_call(
            '/league/list/events/?ordering=start_date&start_date__lt=' + str(date.today())
        )
    else:
        events = api_call('/league/list/events/')
    return events
