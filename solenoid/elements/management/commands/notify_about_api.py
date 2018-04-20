from datetime import timedelta
import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from solenoid.elements.models import ElementsAPICall

logger = logging.getLogger(__name__)

MESSAGE_BASE = ("Usage report for {date}:\n"
    "Total API calls: {count}\n"
    "Failed API calls: {fail}\n"
    "Retried API calls: {retry}\n"
    "Probable timeouts: {timeout}\n")


class Command(BaseCommand):
    help = 'Sends admins an email about API usage for monitoring purposes'

    def _format_message(self, calls):
        call_count_fail = calls.filter(
            response_status__in=ElementsAPICall.STATUS_FAIL).count()
        call_count_retry = calls.filter(
            response_status__in=ElementsAPICall.STATUS_RETRY).count()
        call_count_timeout = calls.filter(
            response_status__isnull=True).count()

        return MESSAGE_BASE.format(
            date=timezone.now().strftime('%-d %B %Y'),
            count=calls.count(),
            fail=call_count_fail,
            retry=call_count_retry,
            timeout=call_count_timeout
        )

    def _update_with_api_warning(self, message):
        last_month = timezone.now() - timedelta(days=30)
        monthly_calls = ElementsAPICall.objects.filter(
            timestamp__gte=last_month).count()

        if monthly_calls >= 225:
            message.append('You have issued {calls} in the past 30 days. '
                'You may need to upgrade your static IP plan, which '
                'only allows 250 calls/month.'.format(calls=monthly_calls))
        return message

    def _send_message(self, message):
        recipients = [admin[1] for admin in settings.ADMINS]

        try:
            send_mail(
                'Solenoid API usage report',
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=False,
            )
        except SMTPException:
            logger.exception('Mail could not be sent')
            raise CommandError

    def handle(self, *args, **options):
        yesterday = timezone.now() - timedelta(days=1)
        calls = ElementsAPICall.objects.filter(timestamp__gte=yesterday)

        if calls:
            message = self._format_message(calls)
            message = self._update_with_api_warning(message)

            self._send_message(message)
