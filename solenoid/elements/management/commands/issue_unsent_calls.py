import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from solenoid.elements.models import ElementsAPICall
from solenoid.elements.views import issue_elements_api_call


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Issues all unsent ElementsAPICalls'

    def handle(self, *args, **options):
        if not settings.USE_ELEMENTS:
            logger.info('Not running issue_unsent_calls command because '
                'settings.USE_ELEMENTS is False.')
            return

        qs1 = ElementsAPICall.objects.filter(response_status='')
        qs2 = ElementsAPICall.objects.filter(response_status__isnull=True)

        for call in (qs1 | qs2):
            issue_elements_api_call(call)
