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

# Will be emailed by the management command about API usage.
ADMINS = [('Andromeda Yelton', 'm31@mit.edu')]

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


# SYMPLECTIC ELEMENTS CONFIGURATION
# -----------------------------------------------------------------------------

# If the QUOTAGUARD_URL is unset, we can't use Elements, so check that in
# addition to the user-supplied Boolean.
USE_ELEMENTS = True and bool(QUOTAGUARD_URL)
