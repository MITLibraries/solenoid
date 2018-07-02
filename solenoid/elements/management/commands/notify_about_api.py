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
        # The issue_unsent_calls job runs hourly. It's possible that, if this
        # command runs in the period between the last time that job started
        # and the last time it was completed, a number of API calls will appear
        # to have timed out (as they will exist but not yet have an http
        # response status code). Therefore we should use a window that is
        # slightly offset, to exclude the most recent job from this reporting
        # window. (Using 2 hours rather than 1 so as not to have to think about
        # fencepost errors or delays in http responses.)
        yesterday = timezone.now() - timedelta(hours=26)
        recently = timezone.now() - timedelta(hours=2)
        calls = ElementsAPICall.objects.filter(
            timestamp__gte=yesterday,
            timestamp__lt=recently)

        if calls:
            message = self._format_message(calls)
            message = self._update_with_api_warning(message)

            self._send_message(message)
