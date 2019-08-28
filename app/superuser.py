import requests

API_URL = 'http://46.101.31.33:8000'
TOKEN = '622d73f9f2d56c4797917fd8086f5a3d51117d0c'


class Superuser(object):
    """Interact with the superuser API."""

    def api_call(self, endpoint, method='GET', json=None):
        """Makes an API call to the back-end server."""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token ' + TOKEN
        }
        if method == 'GET':
            r = requests.get(API_URL + endpoint, headers=headers)
        elif method == 'PATCH':
            r = requests.patch(
                API_URL + endpoint, headers=headers, json=json
            )
        if str(r.status_code).startswith('2'):
            return r.json()
        else:
            return r.status_code

    def manage_credit(self, id, credit):
        """Manage the credit in a user's account."""
        json = {"credit": str(credit)}
        credit = self.api_call('/superuser/credit/' + str(id), 'PATCH', json)
        return credit
