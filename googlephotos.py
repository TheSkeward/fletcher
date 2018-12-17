import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

gphotos = None

def authorize_googlephotos_function(message=None, client=None, args=None):
    global config
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
            {'client_id': config['google-photos']['client_id']},
            scope=['https://www.googleapis.com/auth/photoslibrary.readonly'])

    # Indicate where the API server will redirect the user after the user completes
    # the authorization flow. The redirect URI is required.
    flow.redirect_uri = 'https://novalinium.com/breksta-oauth'

    # Generate URL for request to Google's OAuth 2.0 server.
    # Use kwargs to set optional request parameters.
    authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true')
    print(authorization_url)
    return authorization_url

def login_googlephotos_function(message=None, client=None, args=None):
    global config
    global gphotos
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
            {'client_id': config['google']['photos-oauth-client-id']},
            scope=['https://www.googleapis.com/auth/photoslibrary.readonly'])
    flow.fetch_token(authorization_response=args[0])
    credentials = flow.credentials
    freeze = """
[google-photos]
token = {}
refresh_token = {}
token_uri = {}
client_id = {}
client_secret = {}
scopes = {}
""".format(credentials.token,credentials.refresh_token,credentials.token_uri,credentials.client_id,credentials.client_secret,credentials.scopes)
    gphotos = build('photos.library', 'v1', credentials=credentials)
    print(freeze)
    return freeze

def autoload(ch):
    global config 
    global gphotos
    if gphotos is not None:
        return
    if 'refresh_token' not in config['google-photos']:
        return authorize_google_photos_function()
    ch.add_command({
        'trigger': ['!photos_login'],
        'function': login_googlephotos_function,
        'async': False,
        'admin': True,
        'args_num': 1,
        'args_name': [],
        'description': 'Log onto Google Photos (Admin)'
        })
    gphotos = build('photos.library', 'v1', credentials=config['google-photos'])
