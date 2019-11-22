import logging
from urllib.parse import urljoin
from xml.etree.ElementTree import tostring

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver
from solenoid.emails.signals import email_sent

from .helpers import make_xml
from .tasks import patch_elements_record

logger = logging.getLogger(__name__)


@receiver(email_sent)
def wrap_elements_api_call(sender, **kwargs):
    """Calls the patch_elements_record celery task when an email has been sent.
    """
    logger.info('email_sent signal received')

    if not settings.USE_ELEMENTS:
        logger.info('USE_ELEMENTS is False; not sending API call')
        return False

    if not settings.ELEMENTS_PASSWORD:
        logger.warning('Tried to issue Elements API call without password')
        raise ImproperlyConfigured

    try:
        assert 'username' in kwargs
        assert 'instance' in kwargs
    except AssertionError:
        logger.exception('email_sent did not provide expected args')
        raise

    instance = kwargs['instance']

    # Construct XML. (This is the same for all records in the email.)
    xml = make_xml(username=kwargs['username'])
    request_data = tostring(xml).decode('utf-8')

    for record in instance.record_set.all():
        url = urljoin(settings.ELEMENTS_ENDPOINT,
                      'publications/{id}'.format(
                          id=record.paper_id))

        logger.info(f'Call patch_elements_record task for record #{record.pk}')

        # Call task
        patch_elements_record.delay(url, request_data)
