import requests
from social_core.backends.oauth import BaseOAuth2
from social_core.utils import url_add_parameters


class MITOAuth2(BaseOAuth2):
    """MIT OAuth authentication backend"""
    name = 'mitoauth2'
    ID_KEY = 'sub'
    AUTHORIZATION_URL = 'https://oidc.mit.edu/authorize'
    ACCESS_TOKEN_URL = 'https://oidc.mit.edu/token'
    USER_INFO_URL = 'https://oidc.mit.edu/userinfo'

    def get_user_details(self, response):
        """Fetch user details from user information endpoint after successful
        authorization.

        This is important because it's not enough to verify that the user has
        an MIT account (which is covered by the authorization steps); we will
        need to verify that the account is on our list of authorized users."""
        token = response.get('access_token')
        headers = {"Authorization": "Bearer %s" % token}
        endpoint = self.USER_INFO_URL
        response = requests.get(endpoint, headers=headers)
        return {'email': response.json()['email'] or ''}

    def auth_complete_credentials(self):
        return self.get_key_and_secret()

    def access_token_url(self):
        base_url = super(MITOAuth2, self).access_token_url()
        params = {
            'grant_type': 'authorization_code',
            'code': self.data['code'],
            'redirect_uri': self.get_redirect_uri()
        }
        return url_add_parameters(base_url, params)

    def get_redirect_uri(self, state=None):
        return self.redirect_uri
