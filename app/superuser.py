import requests
import os

if os.environ.get('FLASK_ENV') == 'development':
    API_URL = 'http://157.245.44.130:8000/v1'
    TOKEN = '63e901e32cd6cbe239beb75dedbf7de0eba2a4e4'
else:
    API_URL = 'https://api.liveleague.co.uk/v1'
    TOKEN = '622d73f9f2d56c4797917fd8086f5a3d51117d0c'

class Superuser(object):
    """Interact with the superuser API."""

    def api_call(self, endpoint, method='get', json=None, files=None):
        """Makes an API call to the back-end server."""
        headers = {
            'Authorization': 'Token ' + TOKEN
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
        return {'status': r.status_code, 'json': r.json()}

    def create_secret(self, email):
        """Email a secret code and return a hash. For password resets."""
        json = {'email': email}
        secret_hash = self.api_call('/superuser/create/secret/', 'post', json)
        return secret_hash
    
    def manage_password(self, email, password):
        """Mange the user's password."""
        json = {'password': password}
        password = self.api_call(
            '/superuser/password/' + email + '/', 'patch', json
        )
        return password

    def manage_credit(self, user_id, credit):
        """Manage the credit in a user's account."""
        json = {'credit': str(credit)}
        credit = self.api_call(
            '/superuser/credit/' + str(user_id), 'patch', json
        )
        return credit

    def get_stripe_ids(self, user_id):
        """Retrieves the Stripe IDs of a user."""
        stripe_ids = self.api_call('/superuser/stripe/' + str(user_id))
        return stripe_ids

    def manage_stripe_ids(self, user_id, stripe_account_id=None,
                          stripe_customer_id=None):
        """Manage the Stripe IDs of a user."""
        json = {}
        for param in ['stripe_account_id', 'stripe_customer_id']:
            if eval(param) is not None:
                json[param] = eval(param)
        stripe_ids = self.api_call(
            '/superuser/stripe/' + str(user_id), 'patch', json
        )
        return stripe_ids

    def manage_verification(self, user_id, is_verified):
        """Verify a promoter's account."""
        json = {'is_verified': is_verified}
        is_verified = self.api_call(
            '/superuser/verified/' + str(user_id), 'patch', json
        )
        return is_verified
