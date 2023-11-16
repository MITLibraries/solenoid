"""
Django settings for the 'solenoid' project.

This is the 'heroku' settings file, which imports required configs from
the 'base' settings file and contains the required configurations
for the Solenoid app deployed to Heroku (for staging and production). 

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import sys

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

# ================================ #
# ==== ENVIRONMENT VARIABLES  ==== #
# ================================ #

# CORE SETTINGS
# Default to requiring login on Heroku servers, but allow this to be turned off
# via environment variable in case it's useful to have a test server be more
# freely accessible.
LOGIN_REQUIRED = env.bool("DJANGO_LOGIN_REQUIRED", True)

# DSPACE SETTINGS
DSPACE_SALT = env.str("DJANGO_SECRET_KEY")

# SENTRY SETTINGS
SENTRY_DSN = env.str("SENTRY_DSN", None)
SENTRY_ENVIRONMENT = env.str("SENTRY_ENVIRONMENT", "development")

# ============================== #
# ==== DJANGO CORE SETTINGS ==== #
# ============================== #
ALLOWED_HOSTS = [
    "mitlibraries-solenoid.herokuapp.com",
    "mitlibraries-solenoid-staging.herokuapp.com",
]
# This allows us to include test apps in ALLOWED_HOSTS even though we don't
# know their name until runtime.
if HEROKU_APP_NAME:
    ALLOWED_HOSTS.append("{}.herokuapp.com".format(HEROKU_APP_NAME))

MIDDLEWARE += ["whitenoise.middleware.WhiteNoiseMiddleware"]

# DATABASE
db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES["default"].update(db_from_env)

# STATIC FILES
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# DJANGO COMPRESSOR
COMPRESS_OFFLINE = True

# LOGGING
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "brief": {
            "format": (
                "%(asctime)s %(levelname)s %(name)s[%(funcName)s]: " "%(message)s"
            ),
        },
    },
    "handlers": {
        "console_info": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
        },
    },
    "loggers": {
        "": {
            "handlers": ["console_info"],
            "level": "INFO",
        }
    },
}

# ======================================== #
# ==== SOLENOID AND EXTERNAL SETTINGS ==== #
# ======================================== #

# Will be emailed by the management command about API usage. This is currently
# set to a Webmoira list.
ADMINS = [("Solenoid Admins", "solenoid-admins@mit.edu")]


# SYMPLECTIC ELEMENTS
# The quotaguard docs say there will be a QUOTAGUARD_URL env variable
# provisioned, but in the wild the observed name of this variable is
# QUOTAGUARDSTATIC_URL.
QUOTAGUARD_URL = env.str("QUOTAGUARDSTATIC_URL", None)

# SENTRY
sentry_sdk.init(
    dsn=SENTRY_DSN,
    environment=SENTRY_ENVIRONMENT,
    integrations=[CeleryIntegration(), DjangoIntegration()],
)
