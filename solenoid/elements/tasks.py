from celery import shared_task
from celery.utils.log import get_task_logger

from .elements import patch_elements_record
from .errors import RetryError

logger = get_task_logger(__name__)


@shared_task(bind=True, autoretry_for=(RetryError,), retry_backoff=True)
def task_patch_elements_record(self, url, xml_data):
    return patch_elements_record(url, xml_data)
