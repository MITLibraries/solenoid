"""
Django settings for solenoid project. This is a base settings file; it is
intended to be imported by environment-specific settings files such as a
production settings file. However, it is suitable for local development as-is.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""
import os

import dj_database_url
from django.urls import reverse_lazy

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def boolean(value):
    """Turn the given string value into a boolean.

    Any truthy value will be interpreted as True and anything else will
    be False. For convenience, this function will also accept a boolean
    value (and simply return it) and the value None, which will be
    interpreted as False.
    """
    if isinstance(value, bool) or value is None:
        return bool(value)
    return value.lower() in ('true', 't', 'yes', 'y', '1')


def make_list(value):
    """Return a list of items from a comma-separated string.

    Surrounding whitespace will be stripped from the list items. If the
    provided string is empty, an empty list will be returned. This function
    will also accept the value None and return an empty list.
    """
    if value is None:
        return []
    return list(filter(None, [s.strip() for s in value.split(',')]))


# -----------------------------------------------------------------------------
# ------------------------> core django configurations <-----------------------
# -----------------------------------------------------------------------------

# APP CONFIGURATION
# -----------------------------------------------------------------------------

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

SOLENOID_APPS = [
    'solenoid.elements',
    'solenoid.emails',
    'solenoid.people',
    'solenoid.records',
    'solenoid.userauth',
]

INSTALLED_APPS = DJANGO_APPS + SOLENOID_APPS


# MIDDLEWARE CONFIGURATION
# -----------------------------------------------------------------------------

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]


# DEBUG
# -----------------------------------------------------------------------------

DEBUG = boolean(os.getenv('DJANGO_DEBUG', False))

# DATABASE CONFIGURATION
# -----------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600)
}


# GENERAL CONFIGURATION
# -----------------------------------------------------------------------------

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# This will accept a comma-separated list of allowed hosts
ALLOWED_HOSTS = make_list(os.getenv('ALLOWED_HOSTS'))

if 'HEROKU_APP_NAME' in os.environ:
    ALLOWED_HOSTS.append(
            '{}.herokuapp.com'.format(os.environ['HEROKU_APP_NAME']))

ROOT_URLCONF = 'solenoid.urls'

WSGI_APPLICATION = 'solenoid.wsgi.application'

SITE_ID = 1

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# INTERNATIONALIZATION CONFIGURATION
# -----------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'
USE_TZ = True

# Turned off to save on overhead, since we won't need this for an MIT internal
# app.
USE_I18N = False
USE_L10N = False


# TEMPLATE CONFIGURATION
# -----------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'solenoid', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# STATIC FILE CONFIGURATION
# -----------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'solenoid', 'static')]

FIXTURE_DIRS = [os.path.join(BASE_DIR, 'solenoid', 'fixtures')]


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
            'format': ('%(asctime)s %(levelname)s %(name)s[%(funcName)s]: '
                       '%(message)s'),
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'solenoid.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'brief',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
        }
    }
}


# EMAIL CONFIGURATION
# -----------------------------------------------------------------------------

ADMINS = [('Solenoid Admin', os.getenv('SOLENOID_ADMIN', None))]

EMAIL_USE_TLS = True
EMAIL_HOST = 'outgoing.mit.edu'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'libsys'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER + '@mit.edu'

# THIS CONTROLS WHETHER THE SYSTEM WILL SEND EMAIL. If you don't want to send
# real actual email, don't set this environment variable.
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_SMTP_PASSWORD', None)

# The default backend is SMTP, but if we haven't configured the environment
# with the password, we can't use SMTP, so use the console backend instead.
# This will allow for local development/testing and avoid spamming anyone.
if not EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Expects a string, which is an email address, or None. Any emails sent by the
# system will be cc:ed to this email address.
SCHOLCOMM_MOIRA_LIST = 'sccs-fta@mit.edu'

# If True, will only send email to admins. If False, will send email to
# liaisons and the moira list.
EMAIL_TESTING_MODE = boolean(os.environ.get('DJANGO_EMAIL_TESTING_MODE',
                                            False))


# -----------------------------------------------------------------------------
# -----------------> third-party and solenoid configurations <-----------------
# -----------------------------------------------------------------------------

# OAUTH CONFIGURATION
# -----------------------------------------------------------------------------

INSTALLED_APPS += ['social_django']

# These are the people who should be allowed to log in. This should be a list
# of strings representing MIT usernames; they will be correctly formatted in
# the SOCIAL_AUTH_MITOAUTH2_WHITELISTED_EMAILS list comprehension.
WHITELIST = ['cjrobles', 'cquirion', 'lhanscom', 'khdunn',
             'dfazio', 'efinnie', 'mgraves', 'hbailey']

SOCIAL_AUTH_MITOAUTH2_WHITELISTED_EMAILS = ['%s@mit.edu' % kerb
                                            for kerb in WHITELIST]

SOCIAL_AUTH_PIPELINE = [
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
]

# This is actually a token revocation pipeline, not a disconnection pipeline.
# We need to revoke the tokens, because if we don't logout appears to fail;
# it flushes users from the session, but then it checks with the social auth
# URLs, finds a token, and re-adds the user to the session, which appears to
# the user to be broken.
# It would be better to just call revoke_tokens, but this function isn't
# written to run independently of the pipeline, and it's hard to figure out
# how to hook into it.
# If we ever need to *actually* disconnect users - sever local users from
# their MIT OAuth IDs - we'll have to rework this.
SOCIAL_AUTH_DISCONNECT_PIPELINE = [
    # Collects the social associations to disconnect.
    'social_core.pipeline.disconnect.get_entries',

    # Revoke any access_token when possible.
    'social_core.pipeline.disconnect.revoke_tokens',
]

# Default to not requiring login for ease of local development, but allow it
# to be set with an environment variable to facilitate testing. You will need
# to fill in key and secret values for your environment as well if you set this
# to True.
LOGIN_REQUIRED = boolean(os.environ.get('DJANGO_LOGIN_REQUIRED', False))

if LOGIN_REQUIRED:
    # args is *case-sensitive*, even though other parts of python-social-auth
    # are casual about casing.
    LOGIN_URL = reverse_lazy('social:begin', args=('mitoauth2',))

    AUTHENTICATION_BACKENDS = [
        'solenoid.userauth.backends.MITOAuth2',
        # Required for user/pass authentication - this is useful for the admin
        # site.
        'django.contrib.auth.backends.ModelBackend',
    ]

    SOCIAL_AUTH_MITOAUTH2_KEY = os.environ.get('DJANGO_MITOAUTH2_KEY')
    SOCIAL_AUTH_MITOAUTH2_SECRET = os.environ.get('DJANGO_MITOAUTH2_SECRET')

    MIDDLEWARE += [
        'social_django.middleware.SocialAuthExceptionMiddleware',
    ]

    TEMPLATES[0]['OPTIONS']['context_processors'].extend(
        ['social_django.context_processors.backends',
         'social_django.context_processors.login_redirect'])


# CKEDITOR CONFIGURATION
# -----------------------------------------------------------------------------

INSTALLED_APPS += ['ckeditor']


# This is the same version of jquery that is commented out in the base
# template.
# -If you uncomment that line and load jquery in base.html, delete this
# setting.- Loading jquery multiple times will lead to sorrow.

CKEDITOR_JQUERY_URL = ('https://ajax.googleapis.com/ajax/libs/jquery/'
                       '1.12.4/jquery.min.js')

# We're intentionally not configuring CKeditor file uploads, because file
# uploads are not part of the use case documentation, and they add security
# headaches.

CKEDITOR_CONFIGS = {
    'default': {
        'removePlugins': 'stylesheetparser',
        'allowedContent': {
            '$1': {
                'elements': 'div p a b i em strong',
                'attributes': 'href',
                'classes': True
            }
        },
    }
}


# SYMPLECTIC ELEMENTS CONFIGURATION
# -----------------------------------------------------------------------------

# Defaults to the dev instance - only use the production Elements app if you
# are very sure you should!
ELEMENTS_ENDPOINT = os.environ.get('DJANGO_ELEMENTS_ENDPOINT',
                                   'https://pubdata-dev.mit.edu:8091/'
                                   'secure-api/v5.5/')

# You'll need to have an API user configured in the Elements app that matches
# these parameters. See docs/README.md.
ELEMENTS_USER = os.environ.get('DJANGO_ELEMENTS_USER', 'solenoid')
ELEMENTS_PASSWORD = os.environ.get('DJANGO_ELEMENTS_PASSWORD')

# Set this to False if you don't want to issue API calls (e.g. during testing,
# on localhost, on environments that don't know the password or don't have IPs
# known to the Elements firewall).
USE_ELEMENTS = boolean(os.environ.get('DJANGO_USE_ELEMENTS', False))

QUOTAGUARD_URL = None

# DJANGO-COMPRESSOR CONFIGURATION
# -----------------------------------------------------------------------------

INSTALLED_APPS += ['compressor']

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

COMPRESS_ENABLED = True
COMPRESS_OFFLINE = False  # The default, but we're being explicit.

COMPRESS_PRECOMPILERS = [
    ('text/x-sass', 'django_libsass.SassCompiler'),
    ('text/x-scss', 'django_libsass.SassCompiler'),
]

COMPRESS_ROOT = STATIC_ROOT

# CRISPY-FORMS CONFIGURATION
# -----------------------------------------------------------------------------

INSTALLED_APPS += ['crispy_forms']

# See http://django-crispy-forms.readthedocs.io/en/latest/template_packs.html .
CRISPY_TEMPLATE_PACK = 'mitlib_crispy'

CRISPY_ALLOWED_TEMPLATE_PACKS = ['mitlib_crispy']


# DJANGO-DEBUG-TOOLBAR CONFIGURATION
# -----------------------------------------------------------------------------

INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

INTERNAL_IPS = ['127.0.0.1']


# DSPACE CUSTOMIZATION CONFIGURATION
# -----------------------------------------------------------------------------

DSPACE_SALT = os.getenv('DSPACE_AUTHOR_ID_SALT', default='salty')


# CELERY CONFIGURATION
# -----------------------------------------------------------------------------

CELERY_BROKER_URL = os.getenv('REDIS_URL',
                              default='redis://localhost:6379/0')
CELERY_BROKER_TRANSPORT_OPTIONS = {"max_retries": 3, "interval_start": 0,
                                   "interval_step": 0.2, "interval_max": 0.5}
