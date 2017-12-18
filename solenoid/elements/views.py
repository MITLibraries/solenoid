# The goal: given a Record, mark it as requested in Elements.

# Current status and next steps:
# * Authentication requires credentials + app whitelist + firewall whitelist;
#   have acquired that for test, and requested firewall whitelist in production
# * The required workflow is:
#   1) GET the object
#   2) find all manual records associated with the object (type 'manual' is not
#      guaranteed to be unique) and get their record IDs
#   3) issue PATCH requests for all records to update their c-requested field
#      (and possibly the date and note fields)
# * Make sure xml validates; then remove validation parameter
# * Integrate with signals so that it's nonblocking
#   * Consider whether you want to do a scheduler dyno later - might have a
#     cost, but would let you rerun all failed updates
# * Consider whether you want any kind of logging/monitoring to notify you when
#   the API fails
# * If we can get the record number from the CSV, do that (and definitely
#   monitor it).
# Make sure to validate for the record ID when you ingest CSV.

import logging
from urllib.parse import urljoin
from xml.etree.ElementTree import tostring

import requests

from django import db
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver

from solenoid.emails.signals import email_sent

from .models import ElementsAPICall


logger = logging.getLogger(__name__)


# Honestly this belongs in the management command issue_unsent_calls, but it
# started its life here and it's way easier to test here.
def issue_elements_api_call(call):
    """Sends a patch request to Elements about a Record. Takes a call argument,
    which is an ElementsAPICall prepared with request data. Updates it with
    response data. Does not return anything.
    """

    logger.info('Entering issue_elements_api_call for call #{pk}'.format(
        pk=call.pk))

    try:
        response = call.issue()
    except requests.TooManyRedirects:
        logger.exception("Call #{pk} raised too many redirects".format(
            pk=call.pk))
        return

    # Handle timeouts.
    if not response:
        logger.warning('No response received from Elements API call')
        return

    call.update(response)

    if call.should_retry:
        logger.warning("Call #{pk} must be retried".format(pk=call.pk))
        call.retry()


@receiver(email_sent)
def wrap_elements_api_call(sender, **kwargs):
    """Creates an Elements API call object when an email has been sent.

    Unsent or retryable ElementsAPICalls should be sent via management
    command. They are not sent as part of this function because they block the
    request/response loop, which causes Heroku to time out and crash."""
    logger.info('email_sent signal received')
    db.close_old_connections()

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
    xml = ElementsAPICall.make_xml(username=kwargs['username'])

    for record in instance.record_set.all():
        url = urljoin(settings.ELEMENTS_ENDPOINT,
                      'publications/{id}'.format(
                          id=record.paper_id))

        logger.info('Constructing ElementsAPICall for record #{pk}'.format(
            pk=record.pk))

        # Construct call
        ElementsAPICall.objects.create(
            request_data=tostring(xml).decode('utf-8'),
            request_url=url
        )
