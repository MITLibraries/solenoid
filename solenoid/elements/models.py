from django.db import models


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
