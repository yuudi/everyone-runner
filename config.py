from os import environ

BASE_URL = environ.get('BASE_URL', 'http://localhost:5000')
INACTIVE_TIMELIMIT = int(environ.get('INACTIVE_TIMELIMIT', 60*60*4))
API_SECRET = environ.get('API_SECRET', '')
