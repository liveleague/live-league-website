import requests

API_URL = 'http://46.101.31.33:8000'
ticket_type = '1-regular'
token = 'e7cb5135e4b24d3eca49153a432daba57f3ce84d'

data = {'ticket_type': ticket_type}
endpoint = '/league/create/ticket'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Token ' + token
}

ticket = requests.post(API_URL + endpoint, headers=headers, data=data)
print(ticket.status_code)
print(ticket.headers)
