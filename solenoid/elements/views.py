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

# Note: Christine has figured out how to include record ID (YAY), so we only
# have to issue the patch call. However, I'm not sure how to validate the date
# field.

import logging
import requests
from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver

from solenoid.emails.models import email_sent

from .models import ElementsAPICall

logger = logging.getLogger(__name__)


def _issue_elements_api_call(call):
    """Sends a patch request to Elements about a Record. Takes a call argument,
    which is an ElementsAPICall prepared with request data. Updates it with
    response data. Does not return anything.
    """

    try:
        response = call.issue()
    except requests.TooManyRedirects:
        logger.exception("Call %d raised too many redirects" % call.pk)
        return

    # Handle timeouts.
    if not response:
        logger.warning('No response received from Elements API call')
        return

    call.update(response)

    if call.should_retry:
        logger.warning("Call %d must be retried" % call.pk)
        call.retry()


@receiver(email_sent)
def wrap_elements_api_call(sender):
    """Notifies Elements when a record has been requested. Returns True on
    success, False otherwise.

    Note that this wants to be a *signal receiver* and not anything that could
    conceivably block a view, since the latency on the response may be high
    (it may even time out)."""
    if not settings.USE_ELEMENTS:
        return False

    if not settings.ELEMENTS_PASSWORD:
        logger.warning('Tried to issue Elements API call without password')
        raise ImproperlyConfigured

    # Construct XML. (This is the same for all records in the email.)
    xml = ElementsAPICall.make_xml()

    for record in sender.record_set.all():
        url = urljoin(settings.ELEMENTS_ENDPOINT,
                      'publication/records/{source}/{id}'.format(
                          source=record.source, id=record.elements_id))

        # Construct call
        call = ElementsAPICall.objects.create(
            request_data=xml,
            request_url=url
        )

        _issue_elements_api_call(call)
