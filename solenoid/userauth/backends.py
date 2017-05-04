from social_core.backends.oauth import BaseOAuth2
from social_core.utils import url_add_parameters


class MITOAuth2(BaseOAuth2):
    """MIT OAuth authentication backend"""
    name = 'mitoauth2'
    AUTHORIZATION_URL = 'https://oidc.mit.edu/authorize'
    ACCESS_TOKEN_URL = 'https://oidc.mit.edu/token'

    def get_user_details(self, response):
        """Return user details from MIT account"""
        return {'name': response.get('name'),
                'email': response.get('email') or ''}

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
