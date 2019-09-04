from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from solenoid.elements.models import ElementsAPICall


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('Deletes successfully sent ElementsAPICall records from the '
            'database if they are more than 4 weeks old')

    def handle(self, *args, **options):
        last_month = timezone.now() - timedelta(weeks=4)
        ElementsAPICall.objects.filter(
            response_status='200'
            ).filter(timestamp__lt=last_month).delete()
