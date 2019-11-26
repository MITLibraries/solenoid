import requests

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

from .errors import RetryError

logger = get_task_logger(__name__)

AUTH = (settings.ELEMENTS_USER,
        settings.ELEMENTS_PASSWORD)

PROXIES = {
    'http': settings.QUOTAGUARD_URL,
    'https': settings.QUOTAGUARD_URL,
}


@shared_task(bind=True,
             autoretry_for=(RetryError,),
             retry_backoff=True)
def patch_elements_record(self, url, xml_data):
    """Issue a patch to the Elements API for a given item record URL, with the
    given update data. Return the response."""
    response = requests.patch(url,
                              data=xml_data,
                              headers={'Content-Type': 'text/xml'},
                              proxies=PROXIES,
                              auth=AUTH)
    if response.status_code in [409, 500, 504]:
        raise RetryError(f'Elements response status {response.status_code} '
                         'requires retry')
    response.raise_for_status()
    return response
