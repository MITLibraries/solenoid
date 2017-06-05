import requests
import time
from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings
from django.db import models

HEADERS = {'Content-Type': 'application/xml'}


class ElementsAPICall(models.Model):
    """Stores records of requests made to the Elements API and responses
    received. This will allow us to retry failed calls and monitor for
    problems with the integration."""

    request_data = models.TextField(help_text='The xml sent (i.e. the "data"'
        'kwarg in the requests.patch() call.')
    request_url = models.URLField(help_text='The URL to which the call was '
        'sent (i.e. the "url" argument to requests.patch()).')
    response_content = models.TextField(blank=True, null=True,
        help_text='The content of the response. Will be blank if there was no'
        'response (i.e. due to timeout or other failed call).')
    response_status = models.CharField(max_length=3, blank=True, null=True,
        help_text='The HTTP status code of the response. Will be blank if'
        'there was no response.')
    timestamp = models.DateTimeField(auto_now_add=True)
    retry_of = models.ForeignKey('self', blank=True, null=True,
        help_text='If this call is a retry of a previous failed call, this is'
        'a ForeignKey to that call. Otherwise it is blank.')

    # For the errors that may be returned by the Elements API, see
    # https://support.symplectic.co.uk/support/solutions/articles/6000170776-api-v5-5-requests-and-responses .
    STATUS_FAIL = [400, 401, 403, 404, 410]
    STATUS_RETRY = [409, 500, 504]

    @classmethod
    def make_xml(cls):
        top = Element('update-record')
        top.set('xmlns', 'http://www.symplectic.co.uk/publications/api')
        fields = SubElement(top, 'fields')

        # Update c-requested field
        container_field = SubElement(fields, 'field')
        container_field.set('name', 'c-requested')
        container_field.set('operation', 'set')
        bool_field = SubElement(container_field, 'boolean')
        bool_field.text = 'true'

        # Update c-reqnote field
        container_field = SubElement(fields, 'field')
        container_field.set('name', 'c-reqnote')
        container_field.set('operation', 'set')
        text_field = SubElement(container_field, 'text')
        text_field.text = 'Email sent by solenoid'

        return top

    def _follow_redirects(self, response):
        """If Elements redirected the call, follow the redirect up to five
        steps, and then return the response (if not a redirect) or raise an
        exception."""
        tries = 5
        while tries > 0:
            response = requests.Session.send(response.next)
            if response.status_code != 303:
                return response
            tries -= 1

        raise requests.TooManyRedirects

    def issue(self):
        """Issue a patch call to the Elements API for this call's request.
        Return the response.

        This function follows redirects; the returned response will have a
        non-redirect status code."""
        # Send request
        response = requests.patch(self.request_url,
            data=tostring(self.request_data).decode('utf-8'),
            headers=HEADERS,
            # Passing in an auth parameter makes requests handle HTTP Basic
            # Auth transparently.
            auth=(settings.ELEMENTS_USER, settings.ELEMENTS_PASSWORD))

        if response.status_code == 303:
            response = self._follow_redirects(response)

        return response

    def retry(self):
        """Retry a call, using exponential backoff. Creates new call objects
        ForeignKeyed back to self. Does not return.
        """
        tries = 4
        delay = 2

        while tries > 0:
            new_call = ElementsAPICall.objects.create(
                request_data=self.request_data,
                request_url=self.request_url,
                retry_of=self
            )
            response = new_call.issue()
            new_call.update(response)

            if not new_call.should_retry:
                return

            time.sleep(delay)
            tries -= 1
            delay *= 2

    def update(self, response):
        """Update an existing ElementsAPICall with response data."""
        self.response_content = response.content
        self.response_status = response.status
        self.save()

    @property
    def should_retry(self):
        # If there is no status, this returns False, which is correct, because
        # we can't retry a call we haven't issued (and we shouldn't retry a
        # call that timed out).
        return int(self.response_status) in self.STATUS_RETRY
