from social_core.backends.oauth import BaseOAuth2


class MITOAuth2(BaseOAuth2):
    """MIT OAuth authentication backend"""
    name = 'mitoauth2'
    AUTHORIZATION_URL = 'https://oidc.mit.edu/authorize'
    ACCESS_TOKEN_URL = 'https://oidc.mit.edu/token'

    def get_user_details(self, response):
        """Return user details from MIT account"""
        return {'name': response.get('name'),
                'email': response.get('email') or ''}
