import dj_database_url
import os
import sys

from .base import *  # noqa

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# DATABASE CONFIGURATION
# -----------------------------------------------------------------------------

db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(db_from_env)  # noqa


# GENERAL CONFIGURATION
# -----------------------------------------------------------------------------

SECRET_KEY = bool(os.environ.get('DJANGO_SECRET_KEY'))

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['mitlibraries-solenoid.herokuapp.com',
                 'mitlibraries-solenoid-staging.herokuapp.com']

# This allows us to include review apps in ALLOWED_HOSTS even though we don't
# know their name until runtime.
APP_NAME = os.environ.get('HEROKU_APP_NAME')
if APP_NAME:
    url = '{}.herokuapp.com'.format(APP_NAME)
    ALLOWED_HOSTS.append(url)


# STATIC FILE CONFIGURATION
# -----------------------------------------------------------------------------

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MIDDLEWARE += ['whitenoise.middleware.WhiteNoiseMiddleware']

COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True


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

# Will be emailed by the management command about API usage. This is currently
# set to a Webmoira list.
ADMINS = [('Solenoid Admins', 'solenoid-admins@mit.edu')]


# OAUTH CONFIGURATION
# -----------------------------------------------------------------------------

# Default to requiring login on Heroku servers, but allow this to be turned off
# via environment variable in case it's useful to have a test server be more
# freely accessible.
if os.environ.get('DJANGO_LOGIN_REQUIRED') == 'False':
    # You can't actually set a Boolean environment variable, just a string.
    LOGIN_REQUIRED = False
else:
    LOGIN_REQUIRED = True


# QUOTAGUARD CONFIGURATION
# -----------------------------------------------------------------------------

# The quotaguard docs say there will be a QUOTAGUARD_URL env variable
# provisioned, but in the wild the observed name of this variable is
# QUOTAGUARDSTATIC_URL.
QUOTAGUARD_URL = os.environ.get('QUOTAGUARDSTATIC_URL', None)


# EXCEPTION CONFIGURATION
# -----------------------------------------------------------------------------

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN', None),
    integrations=[DjangoIntegration()]
)


# DSPACE CUSTOMIZATION CONFIGURATION
# -----------------------------------------------------------------------------

# Do not substitute a default value on Heroku, this is required in production
DSPACE_SALT = os.environ['DSPACE_AUTHOR_ID_SALT']
