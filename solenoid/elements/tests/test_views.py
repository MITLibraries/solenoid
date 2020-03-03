from unittest.mock import patch
from urllib.parse import urljoin
from xml.etree.ElementTree import tostring

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from freezegun import freeze_time

from solenoid.emails.models import EmailMessage
from solenoid.emails.signals import email_sent
from solenoid.elements.views import wrap_elements_api_call
from solenoid.elements.xml_handlers import make_xml


class ViewsTests(TestCase):
    fixtures = ['testdata.yaml']

    @override_settings(USE_ELEMENTS=False)
    @patch('solenoid.elements.tasks.task_patch_elements_record.delay')
    def test_use_elements_setting_respected(self, mock_patch):
        retval = wrap_elements_api_call(EmailMessage)
        assert retval is False
        mock_patch.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD=None)
    @patch('solenoid.elements.tasks.task_patch_elements_record.delay')
    def test_elements_password_setting_respected(self, mock_patch):
        with self.assertRaises(ImproperlyConfigured):
            wrap_elements_api_call(EmailMessage)
        mock_patch.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.tasks.task_patch_elements_record.delay')
    def test_checks_kwargs_for_username(self, mock_patch):
        with self.assertRaises(AssertionError):
            wrap_elements_api_call(EmailMessage,
                                   instance=EmailMessage.objects.get(pk=1))
        mock_patch.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.tasks.task_patch_elements_record.delay')
    def test_checks_kwargs_for_instance(self, mock_patch):
        with self.assertRaises(AssertionError):
            wrap_elements_api_call(EmailMessage, username='username')
        mock_patch.assert_not_called()

    @freeze_time('2019-01-01')
    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo',
                       CELERY_ALWAYS_EAGER=True)
    @patch('solenoid.elements.tasks.task_patch_elements_record.delay')
    def test_calls_task_with_proper_args(self, mock_patch):
        email = EmailMessage.objects.get(pk=1)
        wrap_elements_api_call(EmailMessage,
                               username='username',
                               instance=email)

        for record in email.record_set.all():
            xml = make_xml(username='username')
            url = urljoin(settings.ELEMENTS_ENDPOINT,
                          'publications/{id}'.format(id=record.paper_id))

            mock_patch.assert_called_once_with(url,
                                               tostring(xml).decode('utf-8'))

    def test_wrap_is_registered_with_email_sent(self):
        # You can't mock out the wrap function and test that the mock was
        # called, because the mock will not have been registered with the
        # signal. Instead, just check to see that the wrap function is
        # registered, and trust that Django handles its signal receivers
        # correctly.
        registered_functions = [r[1]() for r in email_sent.receivers]
        assert wrap_elements_api_call in registered_functions
