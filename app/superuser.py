import requests

API_URL = 'https://api.liveleague.co.uk/v1/'
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
        elif method == 'POST':
            r = requests.post(
                API_URL + endpoint, headers=headers, json=json
            )
        elif method == 'PATCH':
            r = requests.patch(
                API_URL + endpoint, headers=headers, json=json
            )
        return {'status': r.status_code, 'json': r.json()}

    def create_secret(self, email):
        """Email a secret code and return a hash. For password resets."""
        json = {"email": email}
        secret_hash = self.api_call('/superuser/create/secret', 'POST', json)
        return secret_hash
    
    def manage_password(self, email, password):
        """Mange the user's password."""
        json = {"password": password}
        password = self.api_call('/superuser/password/' + email, 'PATCH', json)
        return password

    def manage_credit(self, id, credit):
        """Manage the credit in a user's account."""
        json = {"credit": str(credit)}
        credit = self.api_call('/superuser/credit/' + str(id), 'PATCH', json)
        return credit
