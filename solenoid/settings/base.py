"""
Django settings for the 'solenoid' project.

This is the 'base' settings file, and the configurations included here
are to be imported into other files containing environment-specific configs
(e.g. the settings file used in production). 

The settings configured in this file are suitable for local development
and testing.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os

import dj_database_url
import environ

BASE_DIR = environ.Path(__file__) - 3  # get root of the project
env = environ.Env()
env.read_env(
    env_file=os.path.join(BASE_DIR, ".env")
)  # read .env file located at project root

# ================================ #
# ==== ENVIRONMENT VARIABLES  ==== #
# ================================ #

# CORE SETTINGS
DEBUG = env.bool("DJANGO_DEBUG", False)
SECRET_KEY = env.str("DJANGO_SECRET_KEY")
LOGIN_REQUIRED = env.bool("DJANGO_LOGIN_REQUIRED", False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
ADMINS = [("Solenoid Admin", env.str("SOLENOID_ADMIN", None))]
EMAIL_HOST_PASSWORD = env.str(
    "DJANGO_SMTP_PASSWORD", None
)  # if set, the system will send emails


# SOLENOID SETTINGS
DATABASE_URL = env.str("DATABASE_URL", "sqlite:///db.sqlite3")
HEROKU_APP_NAME = env.str("HEROKU_APP_NAME", "")
if HEROKU_APP_NAME:
    ALLOWED_HOSTS.append("{}.herokuapp.com".format(HEROKU_APP_NAME))

# If True, will only send email to admins. If False, will send email to
# liaisons and the moira list.
EMAIL_TESTING_MODE = env.bool("DJANGO_EMAIL_TESTING_MODE", False)

# SYMPLECTIC ELEMENTS SETTINGS
# Set this to False if you don't want to issue API calls (e.g. during testing,
# on localhost, on environments that don't know the password or don't have IPs
# known to the Elements firewall).
USE_ELEMENTS = env.bool("DJANGO_USE_ELEMENTS", False)
# You'll need to have an API user configured in the Elements app that matches
# these parameters. See docs/README.md.
ELEMENTS_USER = env.str("DJANGO_ELEMENTS_USER", "solenoid")
ELEMENTS_PASSWORD = env.str("DJANGO_ELEMENTS_PASSWORD", None)

# Defaults to the dev instance - only use the production Elements app if you
# are very sure you should!
ELEMENTS_ENDPOINT = env.str(
    "DJANGO_ELEMENTS_ENDPOINT", "https://pubdata-dev.mit.edu:8091/secure-api/v5.5/"
)

# DSPACE SETTINGS
DSPACE_SALT = env.str("DSPACE_AUTHOR_ID_SALT", "salty")

# CELERY SETTINGS
CELERY_BROKER_URL = env.str("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env.str("REDIS_URL", "redis://localhost:6379")

# ============================== #
# ==== DJANGO CORE SETTINGS ==== #
# ============================== #

# APPLICATION DEFINITION
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

SOLENOID_APPS = [
    "solenoid.elements",
    "solenoid.emails",
    "solenoid.people",
    "solenoid.records",
    "solenoid.accounts",
]

INSTALLED_APPS = DJANGO_APPS + SOLENOID_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # 'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = "solenoid.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "solenoid", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "solenoid.wsgi.application"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# SITES
SITE_ID = 1

# DATABASE
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", "sqlite:///db.sqlite3"), conn_max_age=600
    )
}

# INTERNATIONALIZATION
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
USE_I18N = False

# STATIC FILES
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

# extra places for collectstatic to find static files.
STATICFILES_DIRS = [os.path.join(BASE_DIR, "solenoid", "static")]
FIXTURE_DIRS = [os.path.join(BASE_DIR, "solenoid", "fixtures")]

# AUTHENTICATION VALIDATORS
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

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
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "solenoid.log"),
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "brief",
        },
    },
    "loggers": {
        "": {
            "handlers": ["file"],
            "level": "INFO",
        }
    },
}

# EMAIL
EMAIL_USE_TLS = True
EMAIL_HOST = "outgoing.mit.edu"
EMAIL_PORT = 587
EMAIL_HOST_USER = "libsys"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER + "@mit.edu"


# The default backend is SMTP, but if we haven't configured the environment
# with the password, we can't use SMTP, so use the console backend instead.
# This will allow for local development/testing and avoid spamming anyone.
if not EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Expects a string, which is an email address, or None. Any emails sent by the
# system will be cc:ed to this email address.
SCHOLCOMM_MOIRA_LIST = "sccs-fta@mit.edu"


# ======================================== #
# ==== SOLENOID AND EXTERNAL SETTINGS ==== #
# ======================================== #

LOGIN_REDIRECT_URL = "/"  # redirect to home URL after successful login

# CKEDITOR
INSTALLED_APPS += ["ckeditor"]

# This is the same version of jquery that is commented out in the base
# template.
# -If you uncomment that line and load jquery in base.html, delete this
# setting.- Loading jquery multiple times will lead to sorrow.
CKEDITOR_JQUERY_URL = "https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"

# We're intentionally not configuring CKeditor file uploads, because file
# uploads are not part of the use case documentation, and they add security
# headaches.
CKEDITOR_CONFIGS = {
    "default": {
        "removePlugins": "stylesheetparser",
        "allowedContent": {
            "$1": {
                "elements": "div p a b i em strong",
                "attributes": "href",
                "classes": True,
            }
        },
    }
}

# SYMPLECTIC ELEMENTS
QUOTAGUARD_URL = None

# DJANGO COMPRESSOR
INSTALLED_APPS += ["compressor"]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = False  # The default, but we're being explicit.
COMPRESS_PRECOMPILERS = [
    ("text/x-sass", "django_libsass.SassCompiler"),
    ("text/x-scss", "django_libsass.SassCompiler"),
]

COMPRESS_ROOT = STATIC_ROOT

# CRISPY FORMS
INSTALLED_APPS += ["crispy_forms"]
CRISPY_TEMPLATE_PACK = "mitlib_crispy"
CRISPY_ALLOWED_TEMPLATE_PACKS = ["mitlib_crispy"]

# DJANGO DEBUG TOOLBAR

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ["127.0.0.1"]

# CELERY
INSTALLED_APPS += ["celery_progress"]
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "max_retries": 5,
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 0.5,
    "max_connections": 20,
}
