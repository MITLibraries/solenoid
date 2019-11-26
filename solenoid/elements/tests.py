from unittest.mock import patch
from urllib.parse import urljoin
from xml.etree.ElementTree import tostring

from requests.exceptions import HTTPError

import requests_mock
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.utils import timezone
from freezegun import freeze_time

from ..emails.models import EmailMessage
from ..emails.signals import email_sent
from .errors import RetryError
from .helpers import make_xml
from .tasks import patch_elements_record
from .views import wrap_elements_api_call

USERNAME = 'username'

with freeze_time('2019-01-01'):
    GOOD_XML = (f'<update-object xmlns="http://www.symplectic.co.uk/'
                f'publications/api"><oa><library-status status="full-'
                f'text-requested"><last-requested-when>'
                f'{timezone.now().isoformat()}</last-requested-when>'
                f'<note-field clear-existing-note="true"><note>'
                f'Library status changed to Full text requested on '
                f'{timezone.now().strftime("%-d %B %Y")} '
                f'by username.</note></note-field></library-status>'
                f'</oa></update-object>')


class HelpersTest(TestCase):
    @freeze_time('2019-01-01')
    def test_make_xml(self):
        xml = make_xml('username')
        assert GOOD_XML == tostring(xml, encoding='unicode')


@requests_mock.Mocker()
class TasksTest(TestCase):
    def test_patch_elements_record_success(self, m):
        m.register_uri('PATCH', 'mock://api.com', text='Success')
        response = patch_elements_record('mock://api.com', GOOD_XML)
        assert 200 == response.status_code

    def test_patch_elements_record_raises_retry(self, m):
        with self.assertRaises(RetryError):
            m.register_uri('PATCH', 'mock://api.com/409', status_code=409)
            patch_elements_record('mock://api.com/409', GOOD_XML)
        with self.assertRaises(RetryError):
            m.register_uri('PATCH', 'mock://api.com/500', status_code=500)
            patch_elements_record('mock://api.com/500', GOOD_XML)
        with self.assertRaises(RetryError):
            m.register_uri('PATCH', 'mock://api.com/504', status_code=504)
            patch_elements_record('mock://api.com/504', GOOD_XML)

    def test_patch_elements_record_failure_raises_exception(self, m):
        m.register_uri('PATCH', 'mock://api.com/400', status_code=400)
        with self.assertRaises(HTTPError):
            patch_elements_record('mock://api.com/400', GOOD_XML)


class ViewsTests(TestCase):
    fixtures = ['testdata.yaml']

    @override_settings(USE_ELEMENTS=False)
    @patch('solenoid.elements.tasks.patch_elements_record')
    def test_use_elements_setting_respected(self, mock_patch):
        retval = wrap_elements_api_call(EmailMessage)
        assert retval is False
        mock_patch.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD=None)
    @patch('solenoid.elements.tasks.patch_elements_record')
    def test_elements_password_setting_respected(self, mock_patch):
        with self.assertRaises(ImproperlyConfigured):
            wrap_elements_api_call(EmailMessage)
        mock_patch.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.tasks.patch_elements_record')
    def test_checks_kwargs_for_username(self, mock_patch):
        with self.assertRaises(AssertionError):
            wrap_elements_api_call(EmailMessage,
                                   instance=EmailMessage.objects.get(pk=1))
        mock_patch.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.tasks.patch_elements_record')
    def test_checks_kwargs_for_instance(self, mock_patch):
        with self.assertRaises(AssertionError):
            wrap_elements_api_call(EmailMessage, username='username')
        mock_patch.assert_not_called()

    @freeze_time('2019-01-01')
    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo',
                       CELERY_ALWAYS_EAGER=True)
    @patch('solenoid.elements.tasks.patch_elements_record.delay')
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
