import os
import base64
import json
import time
import secrets
import webbrowser
import logging
from urllib.parse import urlencode
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
from pathlib import Path

# Add logger configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class SpotifyAuth:
    """
    A class to handle Spotify authentication using the Authorization Code flow.

    This class manages the entire authentication process, including:
    - Initiating the auth flow by opening a browser for user login
    - Handling the callback with a local server
    - Exchanging the authorization code for access and refresh tokens
    - Caching tokens in memory and optionally in a file
    - Refreshing expired access tokens

    Attributes:
        _SPOTIFY_SCOPE (str): The Spotify API scopes required for the application.
        _REDIRECT_URI (str): The redirect URI for the Spotify API callback.
        _AUTH_URL (str): The Spotify accounts service authorization URL.
        _TOKEN_URL (str): The Spotify accounts service token URL.
        _SERVER_PORT (int): The port number for the local callback server.

    Args:
        cache_token_path (str, optional): The file path to cache the tokens. 
            If not provided, tokens are only cached in memory.
    """

    _SPOTIFY_SCOPE = 'user-read-private user-read-email playlist-read-private ' \
                     'playlist-read-collaborative playlist-modify-public playlist-modify-private ' \
                     'user-library-read user-library-modify user-top-read user-read-playback-position ' \
                     'user-read-recently-played user-follow-read user-follow-modify ' \
                     'user-read-currently-playing user-modify-playback-state user-read-playback-state ' \
                     'user-read-private user-read-email streaming app-remote-control'
    _REDIRECT_URI = 'http://localhost:8000/callback'
    _AUTH_URL = 'https://accounts.spotify.com/authorize'
    _TOKEN_URL = 'https://accounts.spotify.com/api/token'
    _SERVER_PORT = 8000

    def __init__(self, cache_token_path=None):
        self._authorization_code = None
        self._auth_state = None
        self._httpd = None
        self._cache_token_path = cache_token_path
        self._in_memory_token = None

    class _AuthHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Disable logging by overriding this method
            pass

        def do_GET(self):
            query_components = parse_qs(urlparse(self.path).query)
            if 'code' in query_components and 'state' in query_components:
                received_state = query_components['state'][0]
                if received_state != self.server.auth_instance._auth_state:
                    self._send_response(400, 'State mismatch. Authorization failed.')
                    return
                self.server.auth_instance._authorization_code = query_components['code'][0]
                self._send_response(200, 'Authorization successful! You can close this window.')
            else:
                self._send_response(400, 'Authorization failed.')

        def _send_response(self, status_code, message):
            self.send_response(status_code)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(message.encode())
    def _start_local_server(self):
        server_address = ('', self._SERVER_PORT)
        self._httpd = HTTPServer(server_address, self._AuthHandler)
        self._httpd.auth_instance = self
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def _stop_local_server(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()

    def _get_auth_url(self):
        client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        self._auth_state = secrets.token_urlsafe(16)
        
        params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': self._REDIRECT_URI,
            'scope': self._SPOTIFY_SCOPE,
            'state': self._auth_state
        }
        
        return f"{self._AUTH_URL}?{urlencode(params)}"

    def _get_tokens(self, code):
        client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self._REDIRECT_URI
        }
        
        return self._make_token_request(headers, data)

    def _refresh_access_token(self, refresh_token):
        client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        return self._make_token_request(headers, data, refresh_token)

    def _make_token_request(self, headers, data, refresh_token=None):
        response = requests.post(self._TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        
        tokens = response.json()
        if refresh_token:
            tokens['refresh_token'] = refresh_token
        tokens['expires_at'] = int(time.time()) + tokens['expires_in']
        self._save_tokens(tokens)
        return tokens

    def _save_tokens(self, tokens):
        # First layer: Save in memory
        self._in_memory_token = tokens
        
        # Second layer: Save to file if specified
        if self._cache_token_path:
            token_path = Path(self._cache_token_path).expanduser()
            with token_path.open('w') as f:
                json.dump(tokens, f)
            # Set file permissions to be readable/writable only by the owner
            token_path.chmod(0o600)

    def _load_tokens(self):
        # First layer: Check in-memory cache
        if self._in_memory_token:
            return self._in_memory_token
        
        # Second layer: Check file cache if specified
        if self._cache_token_path:
            token_path = Path(self._cache_token_path).expanduser()
            try:
                with token_path.open('r') as f:
                    tokens = json.load(f)
                # Update in-memory cache
                self._in_memory_token = tokens
                return tokens
            except FileNotFoundError:
                return None
        
        return None

    def _get_valid_tokens(self):
        tokens = self._load_tokens()
        if tokens:
            if int(time.time()) < tokens['expires_at']:
                return tokens
            else:
                refreshed_tokens = self._refresh_access_token(tokens['refresh_token'])
                self._save_tokens(refreshed_tokens)
                return refreshed_tokens
        return None

    def authenticate(self):
        """
        Authenticate the user with Spotify and retrieve access tokens.

        This method handles the entire authentication flow:
        1. Check for valid cached tokens
        2. If no valid tokens, start the authorization code flow
        3. Exchange the authorization code for tokens
        4. Cache the new tokens

        Returns:
            dict: A dictionary containing the access token, refresh token, and expiration time.
        """
        tokens = self._get_valid_tokens()
        if tokens:
            logger.info("Using cached tokens.")
            return tokens
        
        logger.info("Starting local server for authentication...")
        self._start_local_server()
        
        auth_url = self._get_auth_url()
        logger.info("Opening browser for Spotify authentication...")
        webbrowser.open(auth_url)
        
        logger.info("Waiting for authentication...")
        while self._authorization_code is None:
            time.sleep(0.1)
        
        logger.info("Authentication successful! Stopping local server...")
        self._stop_local_server()
        
        tokens = self._get_tokens(self._authorization_code)
        logger.info("Tokens obtained successfully!")
        
        # Reset the state and authorization code
        self._auth_state = None
        self._authorization_code = None
        
        return tokens

# Usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Example with both in-memory and file caching
    auth = SpotifyAuth(cache_token_path='~/.spotify_token.json')
    tokens = auth.authenticate()
    logger.debug("Access Token: %s", tokens['access_token'])

    # Test in-memory caching
    tokens_memory = auth.authenticate()
    logger.debug("Access Token (from memory): %s", tokens_memory['access_token'])

    # Test file caching (create a new instance to simulate a new session)
    auth_new = SpotifyAuth(cache_token_path='~/.spotify_token.json')
    tokens_file = auth_new.authenticate()
    logger.debug("Access Token (from file): %s", tokens_file['access_token'])
