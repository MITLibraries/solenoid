"""
WSGI config for solenoid project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "solenoid.settings.base")
application = get_wsgi_application()


try:
    # If whitenoise is available (i.e. we're on Heroku), wrap the WSGI
    # application in it.
    from whitenoise.django import DjangoWhiteNoise
    application = DjangoWhiteNoise(application)
except (ImportError, ModuleNotFoundError):
    # If we can't find whitenoise (e.g. on localhost), just use the default.
    pass
