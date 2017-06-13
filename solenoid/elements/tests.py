import requests
from unittest import skip
from unittest.mock import patch, MagicMock
from xml.etree.ElementTree import tostring

from django.test import TestCase

from .models import ElementsAPICall

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
                {username}-{author_name} 13 June 2017
            </text>
        </field>
    </fields>
</update-record>
        """.format(username=USERNAME, author_name=AUTHOR_NAME
                   # Yes, that's a DOUBLE space in the replace. We don't want
                   # to replace the single space between field names and
                   # attributes, just to strip the whitespace that's there for
                   # ease of reading.
                   ).replace('  ', '').replace('\n', '')


@skip
class ViewsTest(TestCase):

    # -------------------- Tests of wrap_elements_api_call --------------------

    def test_use_elements_setting_respected(self):
        assert False

    def test_elements_password_setting_respected(self):
        assert False

    def test_checks_kwargs_for_username(self):
        assert False

    def test_checks_kwargs_for_instance(self):
        assert False

    def test_calls_make_xml_with_proper_args(self):
        assert False

    def test_creates_api_call_with_proper_args(self):
        assert False

    def test_calls_issue_elements_api_call_function(self):
        assert False

    def test_receives_email_sent(self):
        assert False

    # ------------------- Tests of _issue_elements_api_call -------------------

    def test_handles_requests_TooManyRedirects(self):
        assert False

    def test_handles_timeouts(self):
        assert False

    def test_updates_call(self):
        assert False

    def test_retries_call(self):
        assert False


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
