from datetime import date
import requests
from unittest.mock import patch, MagicMock
from urllib.parse import urljoin
from xml.etree.ElementTree import tostring

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from solenoid.emails.models import EmailMessage
from solenoid.emails.signals import email_sent

from .models import ElementsAPICall
from .views import wrap_elements_api_call, _issue_elements_api_call

USERNAME = 'username'
AUTHOR_NAME = 'Author Name'

GOOD_XML = """
<update-record xmlns="http://www.symplectic.co.uk/publications/api">
    <fields>
        <field name="c-requested" operation="set">
            <boolean>
                true
            </boolean>
        </field>
        <field name="c-reqnote" operation="set">
            <text>
                {username}-{author_name} {date}
            </text>
        </field>
    </fields>
</update-record>
        """.format(username=USERNAME,
                   author_name=AUTHOR_NAME,
                   date=date.today().strftime('%-d %B %Y')
                   # Yes, that's a DOUBLE space in the replace. We don't want
                   # to replace the single space between field names and
                   # attributes, just to strip the whitespace that's there for
                   # ease of reading.
                   ).replace('  ', '').replace('\n', '')


class ViewsTests(TestCase):
    fixtures = ['testdata.yaml']

    def setUp(self):
        self.call = ElementsAPICall.objects.create(
            request_data=ElementsAPICall.make_xml('username', 'Author Name'),
            request_url='https://10.0.0.2',
        )

    # -------------------- Tests of wrap_elements_api_call --------------------

    @override_settings(USE_ELEMENTS=False)
    @patch('solenoid.elements.views._issue_elements_api_call')
    def test_use_elements_setting_respected(self, mock_call):
        retval = wrap_elements_api_call(EmailMessage)
        assert retval is False
        mock_call.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD=None)
    @patch('solenoid.elements.views._issue_elements_api_call')
    def test_elements_password_setting_respected(self, mock_call):
        with self.assertRaises(ImproperlyConfigured):
            wrap_elements_api_call(EmailMessage)
        mock_call.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.views._issue_elements_api_call')
    def test_checks_kwargs_for_username(self, mock_call):
        with self.assertRaises(AssertionError):
            wrap_elements_api_call(EmailMessage,
                instance=EmailMessage.objects.get(pk=1))
        mock_call.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.views._issue_elements_api_call')
    def test_checks_kwargs_for_instance(self, mock_call):
        with self.assertRaises(AssertionError):
            wrap_elements_api_call(EmailMessage,
                username='username')
        mock_call.assert_not_called()

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.views._issue_elements_api_call')
    @patch('solenoid.elements.models.ElementsAPICall.make_xml')
    def test_calls_make_xml_with_proper_args(self, mock_xml, mock_call):
        email = EmailMessage.objects.get(pk=1)
        wrap_elements_api_call(EmailMessage,
            username='username',
            instance=email)
        mock_xml.assert_called_once_with(
            username='username',
            author_name=email.author.last_name)

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.views._issue_elements_api_call')
    @patch('solenoid.elements.models.ElementsAPICall.objects.create')
    def test_creates_api_call_with_proper_args(self, mock_create, mock_call):
        email = EmailMessage.objects.get(pk=1)
        wrap_elements_api_call(EmailMessage,
            username='username',
            instance=email)

        for record in email.record_set.all():
            xml = ElementsAPICall.make_xml(username='username',
                author_name=email.author.last_name)
            url = urljoin(settings.ELEMENTS_ENDPOINT,
                          'publication/records/{source}/{id}'.format(
                              source=record.source, id=record.elements_id))

            mock_create.assert_called()
            _, kwargs = mock_create.call_args
            assert kwargs['request_url'] == url

            # We can't compare the request_data and `xml` directly, because
            # they're actually different Element objects, in different parts of
            # memory, and thus will show as unequal. For the same reason we
            # cannot use mock_create.assert_called_once_with(). Therefore we
            # assert the call, and then assert separately that its kwargs were
            # as expected.
            assert (tostring(kwargs['request_data']) ==
                    tostring(xml))

    @override_settings(USE_ELEMENTS=True, ELEMENTS_PASSWORD='foo')
    @patch('solenoid.elements.views._issue_elements_api_call')
    def test_calls_issue_elements_api_call_function(self, mock_call):
        email = EmailMessage.objects.get(pk=1)
        wrap_elements_api_call(EmailMessage,
            username='username',
            instance=email)

        for record in email.record_set.all():
            mock_call.assert_called()
            args, _ = mock_call.call_args
            assert isinstance(args[0], ElementsAPICall)

    def test_wrap_is_registered_with_email_sent(self):
        # You can't mock out the wrap function and test that the mock was
        # called, because the mock will not have been registered with the
        # signal. Instead, just check to see that the wrap function is
        # registered, and trust that Django handles its signal receivers
        # correctly.
        registered_functions = [r[1]() for r in email_sent.receivers]
        assert wrap_elements_api_call in registered_functions

    # ------------------- Tests of _issue_elements_api_call -------------------

    @patch('solenoid.elements.models.ElementsAPICall.retry')
    @patch('solenoid.elements.models.ElementsAPICall.update')
    @patch('solenoid.elements.models.ElementsAPICall.issue')
    def test_handles_requests_TooManyRedirects(self,
            mock_issue, mock_update, mock_retry):
        mock_issue.side_effect = requests.TooManyRedirects()
        # This should not raise an exception, but it also shouldn't do anything
        # else.
        _issue_elements_api_call(self.call)
        mock_update.assert_not_called()
        mock_retry.assert_not_called()

    @patch('solenoid.elements.models.ElementsAPICall.retry')
    @patch('solenoid.elements.models.ElementsAPICall.update')
    @patch('solenoid.elements.models.ElementsAPICall.issue')
    def test_handles_timeouts(self,
            mock_issue, mock_update, mock_retry):
        mock_issue.return_value = None
        # This should not raise an exception, but it also shouldn't do anything
        # else.
        _issue_elements_api_call(self.call)
        mock_update.assert_not_called()
        mock_retry.assert_not_called()

    @patch('solenoid.elements.models.ElementsAPICall.update')
    @patch('solenoid.elements.models.ElementsAPICall.issue')
    def test_updates_call(self,
            mock_issue, mock_update):

        # The call won't actually be updated since we're mocking that out;
        # let's make sure that should_retry returns False.
        call = self.call
        call.response_status = 200
        call.save()

        response = MagicMock(status_code=200, content='content')
        mock_issue.return_value = response

        _issue_elements_api_call(call)

        mock_update.assert_called_once_with(response)

    @patch('solenoid.elements.models.ElementsAPICall.retry')
    @patch('solenoid.elements.models.ElementsAPICall.issue')
    def test_retries_call(self, mock_issue, mock_retry):
        response = MagicMock(status_code=409, content='content')
        mock_issue.return_value = response

        _issue_elements_api_call(self.call)
        mock_retry.assert_called()

        assert self.call.should_retry  # check assumption that 409 -> retry


class ElementsAPICallTest(TestCase):
    def setUp(self):
        self.call = ElementsAPICall.objects.create(
            request_data=ElementsAPICall.make_xml('username', 'Author Name'),
            request_url='https://10.0.0.2',
        )

    def test_make_xml(self):
        xml = ElementsAPICall.make_xml(USERNAME, AUTHOR_NAME)

        # tostring() returns bytes (not str) and expected is type str, so we
        # need to do some type casting to make sure the assertion works.
        self.assertEqual(tostring(xml), bytes(GOOD_XML.encode('utf-8')))

    @patch('requests.Session.send')
    def test_follow_redirects_good(self, mock_send):
        mock_send.return_value = MagicMock(status_code=400)
        req = requests.Request('PATCH', 'http://10.0.0.2').prepare()
        response = requests.Response()
        response.status_code = 303
        response.next = req
        resp = self.call._follow_redirects(response)
        assert resp.status_code == 400

    @patch('requests.Session.send')
    def test_follow_redirects_infinite_loop(self, mock_send):
        mock_send.return_value = MagicMock(status_code=303)
        req = requests.Request('PATCH', 'http://10.0.0.2').prepare()
        response = requests.Response()
        response.status_code = 303
        response.next = req
        with self.assertRaises(requests.TooManyRedirects):
            self.call._follow_redirects(response)

    @patch('solenoid.elements.models.ElementsAPICall._follow_redirects')
    @patch('requests.patch')
    def test_issue_follows_redirects(self, mock_patch, mock_follow):
        mock_patch.return_value = MagicMock(status_code=303)
        self.call.issue()
        mock_follow.assert_called_once()

    @patch('solenoid.elements.models.ElementsAPICall._follow_redirects')
    @patch('requests.patch')
    def test_issue_non_redirect(self, mock_patch, mock_follow):
        mock_patch.return_value = MagicMock(status_code=200)
        self.call.issue()
        mock_follow.assert_not_called()

    @patch('solenoid.elements.models.ElementsAPICall.issue')
    def test_retry_once(self, mock_issue):
        # We're only going to test one retry, not the whole exponential backoff
        # process, because that would be time-consuming and tests should be
        # fast.
        mock_issue.return_value = MagicMock(status_code='200', content='stuff')
        self.call.retry()
        mock_issue.assert_called_once()

        new_call = ElementsAPICall.objects.latest('pk')
        assert new_call.response_status == '200'
        assert new_call.response_content == 'stuff'

    def test_update(self):
        response = MagicMock(status_code=200,
                             content='this seems fine')
        self.call.update(response)
        self.call.refresh_from_db()
        assert self.call.response_status == '200'
        assert self.call.response_content == 'this seems fine'

    def test_should_retry(self):
        call = self.call

        # ~~~ failing statuses ~~~ #
        call.response_status = 400
        call.save()
        assert not call.should_retry

        call.response_status = 401
        call.save()
        assert not call.should_retry

        call.response_status = 403
        call.save()
        assert not call.should_retry

        call.response_status = 404
        call.save()
        assert not call.should_retry

        call.response_status = 410
        call.save()
        assert not call.should_retry

        # ~~ retryable statuses ~~ #
        call.response_status = 409
        call.save()
        assert call.should_retry

        call.response_status = 500
        call.save()
        assert call.should_retry

        call.response_status = 504
        call.save()
        assert call.should_retry

        # ~~~~ good statuses ~~~~ #
        call.response_status = 200
        call.save()
        assert not call.should_retry

        call.response_status = 303
        call.save()
        assert not call.should_retry
