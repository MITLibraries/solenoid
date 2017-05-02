import dj_database_url
import os
import sys

from .base import *  # noqa


# DATABASE CONFIGURATION
# -----------------------------------------------------------------------------

db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(db_from_env)  # noqa


# GENERAL CONFIGURATION
# -----------------------------------------------------------------------------

SECRET_KEY = bool(os.environ.get('DJANGO_SECRET_KEY'))

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['*']


# STATIC FILE CONFIGURATION
# -----------------------------------------------------------------------------

STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'


# LOGGING CONFIGURATION
# -----------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'brief': {
            'format': '%(asctime)s %(levelname)s %(name)s[%(funcName)s]: %(message)s',  # noqa
        },
    },
    'handlers': {
        'console_info': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout
        },
    },
    'loggers': {
        '': {
            'handlers': ['console_info'],
            'level': 'INFO',
        }
    }
}


# OAUTH CONFIGURATION
# -----------------------------------------------------------------------------

# Default to requiring login on Heroku servers, but allow this to be turned off
# via environment variable in case it's useful to have a test server be more
# freely accessible.
LOGIN_REQUIRED = bool(os.environ.get('DJANGO_LOGIN_REQUIRED', True))

SOCIAL_AUTH_MITOAUTH2_KEY = os.environ.get('DJANGO_MITOAUTH2_KEY', None)
SOCIAL_AUTH_MITOAUTH2_SECRET = os.environ.get('DJANGO_MITOAUTH2_SECRET', None)
