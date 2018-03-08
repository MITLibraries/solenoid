import logging
import requests
import time
from xml.etree.ElementTree import Element, SubElement

from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)
HEADERS = {'Content-Type': 'text/xml'}
PROXIES = {
    'http': settings.QUOTAGUARD_URL,
    'https': settings.QUOTAGUARD_URL,
}


class ElementsAPICall(models.Model):

    """Stores records of requests made to the Elements API and responses
    received. This will allow us to retry failed calls and monitor for
    problems with the integration."""

    request_data = models.TextField(
        help_text='The xml sent (i.e. the "data" kwarg in the requests.patch()'
        ' call.')
    request_url = models.URLField(
        help_text='The URL to which the call was sent (i.e. the "url" argument'
        ' to requests.patch()).')
    response_content = models.TextField(
        blank=True,
        null=True,
        help_text='The content of the response. Will be blank if there was no'
        'response (i.e. due to timeout or other failed call).')
    response_status = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        help_text='The HTTP status code of the response. Will be blank if'
        'there was no response.')
    timestamp = models.DateTimeField(auto_now_add=True)
    retry_of = models.ForeignKey(
        'self',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text='If this call is a retry of a previous failed call, this is'
        'a ForeignKey to that call. Otherwise it is blank.')

    # For the errors that may be returned by the Elements API, see
    # https://support.symplectic.co.uk/support/solutions/articles/6000170776-api-v5-5-requests-and-responses .
    STATUS_FAIL = [400, 401, 403, 404, 410]
    STATUS_RETRY = [409, 500, 504]

    def __str__(self):
        return "API call #{self.pk} ({self.timestamp})".format(self=self)

    @classmethod
    def make_xml(cls, username):
        logger.info('Making XML')

        top = Element('update-object')
        top.set('xmlns', 'http://www.symplectic.co.uk/publications/api')
        oa_field = SubElement(top, 'oa')

        # Update library status field
        status_field = SubElement(oa_field, 'library-status')
        status_field.set('status', 'full-text-requested')
        date_field = SubElement(status_field, 'last-requested-when')
        date_field.text = timezone.now().isoformat()
        note_field = SubElement(status_field, 'note-field')
        note_field.set('clear-existing-note', 'true')
        note = SubElement(note_field, 'note')
        note.text = "Library status changed to Full text requested on " \
            "{date} by {username}.".format(
                date=timezone.now().strftime('%-d %B %Y'),
                username=username)

        return top

    def _follow_redirects(self, response):
        """If Elements redirected the call, follow the redirect up to five
        steps, and then return the response (if not a redirect) or raise an
        exception."""
        logger.info('Following redirects for call #{pk}'.format(pk=self.pk))
        tries = 5
        while tries > 0:
            logger.info('Following redirect; {tries} tries remain'.format(
                tries=tries))
            response = requests.Session.send(response.next)
            if response.status_code != 303:
                return response
            tries -= 1

        logger.warning('Max number of redirects exceeded')
        raise requests.TooManyRedirects

    def issue(self):
        """Issue a patch call to the Elements API for this call's request.
        Return the response.

        This function follows redirects; the returned response will have a
        non-redirect status code."""

        logger.info('Issuing ElementsAPICall #{pk}'.format(pk=self.pk))

        if not settings.QUOTAGUARD_URL:
            logger.warning('No URL; not issuing call.')
            return

        # Send request
        response = requests.patch(self.request_url,
            data=self.request_data,
            headers=HEADERS,
            proxies=PROXIES,
            # Passing in an auth parameter makes requests handle HTTP Basic
            # Auth transparently.
            auth=(settings.ELEMENTS_USER, settings.ELEMENTS_PASSWORD))

        if response.status_code == 303:
            response = self._follow_redirects(response)

        logger.info('Returning response for call #{pk}'.format(pk=self.pk))
        return response

    def retry(self):
        """Retry a call, using exponential backoff. Creates new call objects
        ForeignKeyed back to self. Does not return anything.
        """
        logger.info('Retrying ElementsAPICall #{pk}'.format(pk=self.pk))

        tries = 4
        delay = 2

        while tries > 0:
            logger.info('Retry {num} for call {pk}'.format(
                num=tries, pk=self.pk))

            new_call = ElementsAPICall.objects.create(
                request_data=self.request_data,
                request_url=self.request_url,
                retry_of=self
            )
            response = new_call.issue()
            new_call.update(response)

            if not new_call.should_retry:
                logger.info('Not retrying #{pk} because should_retry is '
                    'False'.format(pk=new_call.pk))
                return

            time.sleep(delay)
            tries -= 1
            delay *= 2

    def update(self, response):
        """Update an existing ElementsAPICall with response data."""
        logger.info('Updating ElementsAPICall #{pk}'.format(pk=self.pk))
        self.response_content = response.content
        self.response_status = response.status_code
        self.save()

    @property
    def should_retry(self):
        # If there is no status, this returns False, which is correct, because
        # we can't retry a call we haven't issued (and we shouldn't retry a
        # call that timed out).
        return int(self.response_status) in self.STATUS_RETRY
