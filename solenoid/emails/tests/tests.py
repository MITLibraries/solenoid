from datetime import date
from unittest.mock import patch, call

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase, Client, override_settings

from solenoid.people.models import Author, Liaison
from solenoid.records.models import Record

from ..models import EmailMessage
from ..views import _email_send, _get_or_create_emails


@override_settings(LOGIN_REQUIRED=False)
class EmailCreatorTestCase(TestCase):
    fixtures = ['records.yaml']

    @patch('solenoid.emails.views._get_or_create_emails')
    def test_posting_to_create_view_calls_creator(self, mock_create):
        mock_create.return_value = [1]
        c = Client()
        c.post(reverse('emails:create'), {'records': ['1']})
        mock_create.assert_called_once_with(['1'])

        mock_create.reset_mock()
        c.post(reverse('emails:create'), {'records': ['1', '2']})
        mock_create.assert_called_once_with(['1', '2'])

    def test_posting_to_create_view_returns_email_eval(self):
        c = Client()
        response = c.post(reverse('emails:create'), {'records': ['1']})
        self.assertRedirects(response, reverse('emails:evaluate', args=(1,)))

    def test_email_recipient(self):
        """The email created by _get_or_create_emails must be to: the relevant
        liaison."""
        # Expected to be a paper by Fermi, who belongs to Physics, whose
        # liaison is Krug.
        record = Record.objects.get(pk=1)
        _get_or_create_emails([record.pk])
        email = EmailMessage.objects.latest('pk')
        self.assertEqual(email.liaison.pk, 1)

    def test_email_author_without_liaison(self):
        """Something logical should happen."""
        assert False


@override_settings(LOGIN_REQUIRED=False)
class EmailEvaluateTestCase(TestCase):
    fixtures = ['emails.yaml']

    def setUp(self):
        self.url = reverse('emails:evaluate', args=(1,))
        self.client = Client()

    def test_latest_version_displays_on_unsent_page_if_not_blank(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Most recent text of email 1")

    def test_liaison_email_address_displays(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'krug@example.com')

    def test_users_can_save_changes_to_emails(self):
        new_text = 'This is what we change the email to'
        self.client.post(self.url, {
            'submit_save': 'save & next',
            'latest_text': new_text
        })

        self.assertEqual(new_text,
            EmailMessage.objects.get(pk=1).latest_text)

    def test_only_unsent_emails_are_editable_1(self):
        """The email evaluate page for a sent email shows its text as sent but
        does not contain an HTML form element."""
        sent_email = EmailMessage.objects.get(pk=1)
        sent_email.date_sent = date.today()
        sent_email.save()

        response = self.client.get(self.url)
        self.assertContains(response, "Most recent text of email 1")
        self.assertNotContains(response, "</form>")

    @patch('solenoid.emails.views._email_send')
    def test_only_unsent_emails_are_editable_2(self, mock_send):
        """On post, the email evaluate page does not re-send emails that have
        already been sent."""
        sent_email = EmailMessage.objects.get(pk=1)
        sent_email.date_sent = date.today()
        sent_email.save()

        self.client.post(self.url, {'submit_send': 'send & next'})
        assert not mock_send.called


@override_settings(LOGIN_REQUIRED=False)
class EmailMessageModelTestCase(TestCase):
    fixtures = ['emails.yaml', 'records.yaml']

    def test_revert(self):
        original_text = 'This is the original text'
        latest_text = 'This is the subsequent text'

        email = EmailMessage.objects.create(
            original_text=original_text,
            latest_text=latest_text,
            author=Author.objects.latest('pk'),
            liaison=Liaison.objects.latest('pk'),
        )

        email.revert()
        self.assertEqual(email.latest_text, original_text)

    def test_latest_text_is_set_on_creation(self):
        original_text = 'This is the original text'

        email = EmailMessage.objects.create(
            original_text=original_text,
            # Note that latest_text is not set here, hence defaults blank.
            author=Author.objects.latest('pk'),
            liaison=Liaison.objects.latest('pk'),
        )

        self.assertEqual(email.latest_text, original_text)

    def test_email_has_all_expected_records(self):
        """The email text includes all expected records."""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        email = EmailMessage.create_original_text(records[0].author, records)
        assert Record.objects.get(pk=3).citation in email
        assert Record.objects.get(pk=4).citation in email

    def test_invalid_records_do_not_get_emailed(self):
        """If the input set contains invalid records, they do not make it
        into the EmailMessage text."""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        email = EmailMessage.create_original_text(records[0].author, records)
        assert Record.objects.get(pk=5).citation not in email

    def test_already_sent_records_do_not_get_emailed(self):
        """If the input set contains already-sent records, they do not make it
        into the EmailMessage text."""
        records = Record.objects.filter(pk__in=[2, 3, 4, 5])
        email = EmailMessage.create_original_text(records[0].author, records)
        assert Record.objects.get(pk=2).citation not in email

    @patch.dict('solenoid.emails.helpers.SPECIAL_MESSAGES',
                {'ACM-Special Message': 'A very special message'})
    def test_publisher_special_message_included(self):
        """The email text includes special messages for each publisher in its
        record set with a special message."""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        text = EmailMessage.create_original_text(records[0].author, records)
        self.assertEqual(text.count('A very special message'), 1)

    @patch.dict('solenoid.emails.helpers.SPECIAL_MESSAGES',
                {'Scholastic': 'A very special message',
                 'Wiley': 'An equally special message'})
    def test_irrelevant_publisher_special_message_excluded(self):
        """The email text does not include special messages for publishers not
        in its record set."""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        email = EmailMessage.create_original_text(records[0].author, records)
        self.assertNotIn('A very special message', email)
        self.assertNotIn('An equally special message', email)

    def test_html_rendered_as_html(self):
        """Make sure that we see <p>, not &lt;p&gt;, and so forth, in our
        constructed email text. (If we put {{ citations }} into the email
        template without the |safe filter, we'll end up with escaped HTML,
        which is no good for our purposes.)"""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        email = EmailMessage.create_original_text(records[0].author, records)
        self.assertNotIn('&lt;p&gt;', email)

    def test_fpv_accepted_message_included(self):
        """The Recruit from Author - FPV Accepted message is included if that is
        the recruitment strategy."""
        # Record 4 should have an fpv message; 3 does not
        records = Record.objects.filter(pk__in=[3, 4])
        email = EmailMessage.create_original_text(records[0].author, records)
        self.assertIn(Record.objects.get(pk=4).fpv_message,
                      email)

    def test_fpv_accepted_message_excluded(self):
        """The Recruit from Author - FPV Accepted message is NOT included if
        that ISN'T the recruitment strategy."""
        record = Record.objects.get(pk=3)
        email = EmailMessage.create_original_text(record.author, [record])
        msg = 'allows authors to download and deposit the final published ' \
              'article, but does not allow the Libraries to perform the ' \
              'downloading'
        self.assertNotIn(msg, email)



@override_settings(LOGIN_REQUIRED=False)
class EmailSendTestCase(TestCase):
    fixtures = ['emails.yaml']

    def setUp(self):
        self.url = reverse('emails:send')
        self.client = Client()

    def test_email_send_function_sends(self):
        self.assertFalse(EmailMessage.objects.get(pk=1).date_sent)
        _email_send(1)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_send_function_does_not_resend(self):
        email = EmailMessage.objects.get(pk=1)
        email.date_sent = date.today()
        email.save()
        _email_send(1)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_send_function_sets_datestamp(self):
        self.assertFalse(EmailMessage.objects.get(pk=1).date_sent)
        _email_send(1)
        self.assertTrue(EmailMessage.objects.get(pk=1).date_sent)
        # Conceivably this test will fail if run near midnight UTC.
        self.assertEqual(EmailMessage.objects.get(pk=1).date_sent,
            date.today())

    def test_email_is_sent_to_liaison(self):
        _email_send(1)
        self.assertEqual(len(mail.outbox), 1)  # check assumption
        self.assertIn(EmailMessage.objects.get(pk=1).liaison.email_address,
            mail.outbox[0].to)

    @override_settings(SCHOLCOMM_MOIRA_LIST='scholcomm@example.com')
    def test_email_is_sent_to_scholcomm_moira_list(self):
        _email_send(1)
        self.assertEqual(len(mail.outbox), 1)  # check assumption
        self.assertIn('scholcomm@example.com', mail.outbox[0].to)

    @override_settings(SCHOLCOMM_MOIRA_LIST=None)
    def test_email_handles_empty_moira_list(self):
        """If no scholcomm list has been set, the email function should not
        break."""
        _email_send(1)
        self.assertEqual(len(mail.outbox), 1)

    @patch('solenoid.emails.views._email_send')
    def test_email_send_view_calls_function(self, mock_send):
        self.client.post(self.url, data={'emails': [1, 2]})
        # Even if we post ints, they'll get cast to strs before we call the
        # function, and the test will fail if we don't recognize this.
        expected = [call('1'), call('2')]
        mock_send.assert_has_calls(expected, any_order=True)

    def test_subject_is_something_logical(self):
        assert False

    def test_text_version_is_something_logical(self):
        """We have only the html message but we need to generate a text
        format and update the email sending function."""
        assert False

# https://pypi.python.org/pypi/html2text - might be of use if we need to
# generate multipart.
