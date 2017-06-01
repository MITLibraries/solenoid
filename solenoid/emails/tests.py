from datetime import date
from unittest.mock import patch, call

from django.core import mail
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test import TestCase, Client, override_settings

from solenoid.people.models import Author, Liaison
from solenoid.records.models import Record, Message

from .models import EmailMessage
from .views import _get_or_create_emails


@override_settings(LOGIN_REQUIRED=False)
class EmailCreatorTestCase(TestCase):
    fixtures = ['testdata.yaml']

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
        # Expected to be a paper by Tonegawa, who belongs to BCS, whose
        # liaison is Cutter. This record does not yet have an email.
        email_pks = _get_or_create_emails([2])
        email = EmailMessage.objects.get(pk=email_pks[0])
        self.assertEqual(email.liaison.pk, 2)

    def test_get_or_create_emails_returns_correctly(self):
        """When we pass in records to _get_or_create_emails, we should get back
        one email per author in the recordset."""
        email_pks = _get_or_create_emails([1])
        self.assertEqual(len(email_pks), 1)

        email_pks = _get_or_create_emails([1, 2])
        self.assertEqual(len(email_pks), 2)

        email_pks = _get_or_create_emails([1, 2, 3])
        self.assertEqual(len(email_pks), 3)

        email_pks = _get_or_create_emails([1, 2, 3, 4])
        # Records 3 and 4 are by the same author.
        self.assertEqual(len(email_pks), 3)


@override_settings(LOGIN_REQUIRED=False)
class EmailEvaluateTestCase(TestCase):
    fixtures = ['testdata.yaml']

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

    @patch('solenoid.emails.models.EmailMessage.send')
    def test_only_unsent_emails_are_editable_2(self, mock_send):
        """On post, the email evaluate page does not re-send emails that have
        already been sent."""
        sent_email = EmailMessage.objects.get(pk=1)
        sent_email.date_sent = date.today()
        sent_email.save()

        self.client.post(self.url, {'submit_send': 'send & next'})
        assert not mock_send.called

    def test_template_renders_form_media(self):
        """Make sure we remembered to include {{ form.media }}, which is
        required for rendering the WYSIWYG editor.
        It's hard to directly test that the template HTML contains that
        string, but we can check that the rendered template contains part of
        the expected output of form.media, which would be unlikely to get there
        any other way."""
        response = self.client.get(self.url)
        self.assertContains(response, 'ckeditor/ckeditor.js')

    def test_email_evaluate_workflow_1(self):
        """
        Make sure that EmailEvaluate walks through the expected set of emails
        when users are hitting 'cancel & next'.

        It'd be nice to test that the session variables are set correctly, but
        testing Django session is a pain.
        """
        # Set up a path that should take us through the evaluate view 3 times.
        # Implicitly, we entered the email evaluation workflow with the pks =
        # [1, 2, 3], but 1 has already been popped by EmailCreate.
        # See https://docs.djangoproject.com/en/1.8/topics/testing/tools/#persistent-state
        # for info on how to use sessions in testing.
        session = self.client.session
        session['email_pks'] = [2, 3]
        session['total_email'] = 3
        session['current_email'] = 1
        session.save()

        current_url = reverse('emails:evaluate', args=(1,))
        self.client.get(current_url)

        response = self.client.post(current_url,
                                    data={'submit_cancel': 'submit_cancel'})
        expected_url = reverse('emails:evaluate', args=(2,))
        self.assertRedirects(response, expected_url)

        response = self.client.post(expected_url,
                                    data={'submit_cancel': 'submit_cancel'})
        expected_url = reverse('emails:evaluate', args=(3,))
        self.assertRedirects(response, expected_url)

        response = self.client.post(expected_url,
                                    data={'submit_cancel': 'submit_cancel'})
        expected_url = reverse('home')
        self.assertRedirects(response, expected_url)

    def test_email_evaluate_workflow_2(self):
        """
        Make sure that EmailEvaluate walks through the expected set of emails
        when users are hitting 'save & next'.
        """
        # Set up a path that should take us through the evaluate view 3 times.
        # Implicitly, we entered the email evaluation workflow with the pks =
        # [1, 2, 3], but 1 has already been popped by EmailCreate.
        # See https://docs.djangoproject.com/en/1.8/topics/testing/tools/#persistent-state
        # for info on how to use sessions in testing.
        session = self.client.session
        session['email_pks'] = [2, 3]
        session['total_email'] = 3
        session['current_email'] = 1
        session.save()

        current_url = reverse('emails:evaluate', args=(1,))
        self.client.get(current_url)

        response = self.client.post(current_url,
                                    data={'submit_save': 'submit_save'})
        expected_url = reverse('emails:evaluate', args=(2,))
        self.assertRedirects(response, expected_url)

        response = self.client.post(expected_url,
                                    data={'submit_save': 'submit_save'})
        expected_url = reverse('emails:evaluate', args=(3,))
        self.assertRedirects(response, expected_url)

        response = self.client.post(expected_url,
                                    data={'submit_save': 'submit_save'})
        expected_url = reverse('home')
        self.assertRedirects(response, expected_url)

    def test_email_evaluate_workflow_3(self):
        """
        Make sure that EmailEvaluate walks through the expected set of emails
        when users are hitting 'send & next'.
        """
        # Set up a path that should take us through the evaluate view 3 times.
        # Implicitly, we entered the email evaluation workflow with the pks =
        # [1, 2, 3], but 1 has already been popped by EmailCreate.
        # See https://docs.djangoproject.com/en/1.8/topics/testing/tools/#persistent-state
        # for info on how to use sessions in testing.
        session = self.client.session
        session['email_pks'] = [2, 3]
        session['total_email'] = 3
        session['current_email'] = 1
        session.save()

        # Make sure email 2 is sendable - in the test data it's missing a
        # record, meaning its author can't be identified.
        record = Record.objects.get(pk=2)
        email = EmailMessage.objects.get(pk=2)
        record.email = email
        record.save()

        current_url = reverse('emails:evaluate', args=(1,))
        self.client.get(current_url)

        response = self.client.post(current_url,
                                    data={'submit_send': 'submit_send'})
        expected_url = reverse('emails:evaluate', args=(2,))
        self.assertRedirects(response, expected_url)

        response = self.client.post(expected_url,
                                    data={'submit_send': 'submit_send'})
        expected_url = reverse('emails:evaluate', args=(3,))
        self.assertRedirects(response, expected_url)

        response = self.client.post(expected_url,
                                    data={'submit_send': 'submit_send'})
        expected_url = reverse('home')
        self.assertRedirects(response, expected_url)


@override_settings(LOGIN_REQUIRED=False)
class EmailMessageModelTestCase(TestCase):
    fixtures = ['testdata.yaml']

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
        email = EmailMessage.create_original_text(records)
        assert Record.objects.get(pk=3).citation in email
        assert Record.objects.get(pk=4).citation in email

    def test_already_sent_records_do_not_get_emailed(self):
        """If the input set contains already-sent records, they do not make it
        into the EmailMessage text."""
        records = Record.objects.filter(pk__in=[3, 4, 6])
        email = EmailMessage.create_original_text(records)
        assert Record.objects.get(pk=6).citation not in email

    def test_publisher_special_message_included(self):
        """The email text includes special messages for each publisher in its
        record set with a special message."""
        message = Message.objects.create(text='A very special message')
        r3 = Record.objects.get(pk=3)
        r3.message = message
        r3.save()

        records = Record.objects.filter(pk__in=[3, 4, 5])
        text = EmailMessage.create_original_text(records)
        self.assertEqual(text.count('A very special message'), 1)

    def test_html_rendered_as_html(self):
        """Make sure that we see <p>, not &lt;p&gt;, and so forth, in our
        constructed email text. (If we put {{ citations }} into the email
        template without the |safe filter, we'll end up with escaped HTML,
        which is no good for our purposes.)"""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        email = EmailMessage.create_original_text(records)
        self.assertNotIn('&lt;p&gt;', email)

    def test_fpv_accepted_message_included(self):
        """The Recruit from Author - FPV Accepted message is included if that is
        the recruitment strategy."""
        # Record 4 should have an fpv message; 3 does not
        records = Record.objects.filter(pk__in=[3, 4])
        email = EmailMessage.create_original_text(records)
        self.assertIn(Record.objects.get(pk=4).fpv_message,
                      email)

    def test_fpv_accepted_message_excluded(self):
        """The Recruit from Author - FPV Accepted message is NOT included if
        that ISN'T the recruitment strategy."""
        record = Record.objects.filter(pk=3)
        email = EmailMessage.create_original_text(record)
        msg = 'allows authors to download and deposit the final published ' \
              'article, but does not allow the Libraries to perform the ' \
              'downloading'
        self.assertNotIn(msg, email)

    def test_liaison_property_1(self):
        """If EmailMessage._liaison exists, email.liaison returns it."""
        email = EmailMessage.objects.get(pk=2)
        self.assertEqual(email.liaison.pk, 1)

    def test_liaison_property_2(self):
        """If EmailMessage._liaison does not exist, email.liaison returns the
        expected liaison based on the author's DLC."""

        # This email is associated with record #1 -> author #1 -> DLC #1 ->
        # liaison #1.
        email = EmailMessage.objects.get(pk=1)
        self.assertEqual(email.liaison.pk, 1)

    def test_dlc_property_1(self):
        """The DLC property returns the DLC of the author of the records
        associated with the email, when those exist."""
        email = EmailMessage.objects.get(pk=1)
        self.assertEqual(email.dlc.pk, 1)

    def test_dlc_property_2(self):
        """The DLC property returns None when the email has no records."""
        email = EmailMessage.objects.get(pk=2)
        self.assertEqual(email.dlc, None)

    def test_author_property_1(self):
        """The DLC property returns the author of the records associated with
        the email, when those exist."""
        email = EmailMessage.objects.get(pk=1)
        self.assertEqual(email.author.pk, 1)

    def test_author_property_2(self):
        """The DLC property returns None when the email has no records."""
        email = EmailMessage.objects.get(pk=2)
        self.assertEqual(email.author, None)

    def test_plaintext_property(self):
        """We have only the html message but we need to generate a text
        format and update the email sending function."""
        email = EmailMessage.objects.get(pk=3)
        self.assertEqual(email.latest_text,
                         "<b>Most recent text<b> of email 3")
        self.assertEqual(email.plaintext,
                         "Most recent text of email 3")

    def test_get_or_create_for_records_1(self):
        """EmailMessage.get_or_create_for_records raises an error if the given
        records do not all have the same author."""
        with self.assertRaises(ValidationError):
            records = Record.objects.filter(pk__in=[1, 2])
            EmailMessage.get_or_create_for_records(records)

    def test_get_or_create_for_records_2(self):
        """EmailMessage.get_or_create_for_records returns an already existing
        email where appropriate."""
        records = Record.objects.filter(pk__in=[1])
        email = EmailMessage.get_or_create_for_records(records)
        self.assertEqual(email.pk, 1)

    def test_get_or_create_for_records_3(self):
        """EmailMessage.get_or_create_for_records makes sure all Records fed
        into it have FKs to its returned EmailMessage, regardless of whether
        they were already linked."""
        records = Record.objects.filter(pk__in=[1, 7])
        email = EmailMessage.get_or_create_for_records(records)
        self.assertEqual(email.pk, 1)
        self.assertEqual(Record.objects.get(pk=1).email.pk, 1)
        self.assertEqual(Record.objects.get(pk=7).email.pk, 1)

    def test_get_or_create_for_records_4(self):
        """EmailMessage.get_or_create_for_records excludes all Records that
        were attached to an already-sent EmailMessage."""
        # This email is attached to record #1.
        email = EmailMessage.objects.get(pk=1)
        email.date_sent = date.today()
        email.save()

        records = Record.objects.filter(pk__in=[1, 7])
        email = EmailMessage.get_or_create_for_records(records)
        self.assertNotEqual(email.pk, 1)  # should be a new email

        # Record 1 should still be attached to its existing email.
        self.assertEqual(Record.objects.get(pk=1).email.pk, 1)

        # Record 7 should be attached to a new, unsent email.
        self.assertEqual(Record.objects.get(pk=7).email.pk, email.pk)
        self.assertFalse(Record.objects.get(pk=7).email.date_sent)

    def test_get_or_create_for_records_5(self):
        """EmailMessage.get_or_create_for_records returns None if all records
        have already been sent."""
        email = EmailMessage.objects.get(pk=1)
        email.date_sent = date.today()
        email.save()

        records = Record.objects.filter(pk__in=[1])
        email = EmailMessage.get_or_create_for_records(records)
        assert email is None

    def test_get_or_create_for_records_6(self):
        """EmailMessage.get_or_create_for_records raises an error if there are
        multiple unsent EmailMessages corresponding to its Author."""
        email = EmailMessage.objects.get(pk=2)
        self.assertFalse(email.date_sent)

        record = Record.objects.get(pk=7)
        record.email = email
        record.save()

        with self.assertRaises(ValidationError):
            # Note that these records have the same author, so we are not
            # failing the author validation criterion.
            records = Record.objects.filter(pk__in=[1, 7])
            EmailMessage.get_or_create_for_records(records)


@override_settings(LOGIN_REQUIRED=False)
class EmailSendTestCase(TestCase):
    fixtures = ['testdata.yaml']

    def setUp(self):
        self.url = reverse('emails:send')
        self.client = Client()

    def test_email_send_function_sends(self):
        email = EmailMessage.objects.get(pk=1)
        self.assertFalse(email.date_sent)
        email.send()
        self.assertEqual(len(mail.outbox), 1)

    def test_email_send_function_does_not_resend(self):
        email = EmailMessage.objects.get(pk=1)
        email.date_sent = date.today()
        email.save()
        email.send()
        self.assertEqual(len(mail.outbox), 0)

    def test_email_send_function_sets_datestamp(self):
        email = EmailMessage.objects.get(pk=1)
        self.assertFalse(email.date_sent)
        email.send()
        email.refresh_from_db()
        self.assertTrue(email.date_sent)
        # Conceivably this test will fail if run near midnight UTC.
        self.assertEqual(email.date_sent, date.today())

    def test_email_send_function_sets_liaison(self):
        email = EmailMessage.objects.get(pk=1)
        liaison = email.liaison
        assert not email.date_sent

        email.send()
        email.refresh_from_db()
        assert email.date_sent

        self.assertEqual(email._liaison, liaison)

    def test_email_is_sent_to_liaison(self):
        email = EmailMessage.objects.get(pk=1)
        email.send()
        self.assertEqual(len(mail.outbox), 1)  # check assumption
        self.assertIn(EmailMessage.objects.get(pk=1).liaison.email_address,
            mail.outbox[0].to)

    @override_settings(SCHOLCOMM_MOIRA_LIST='scholcomm@example.com')
    def test_email_is_sent_to_scholcomm_moira_list(self):
        email = EmailMessage.objects.get(pk=1)
        email.send()
        self.assertEqual(len(mail.outbox), 1)  # check assumption
        self.assertIn('scholcomm@example.com', mail.outbox[0].to)

    @override_settings(SCHOLCOMM_MOIRA_LIST=None)
    def test_email_handles_empty_moira_list(self):
        """If no scholcomm list has been set, the email function should not
        break."""
        email = EmailMessage.objects.get(pk=1)
        email.send()
        self.assertEqual(len(mail.outbox), 1)

    # autospec=True ensures that 'self' is passed into the mock, allowing us to
    # examine the call args as desired:
    # https://docs.python.org/3.3/library/unittest.mock-examples.html#mocking-unbound-methods
    @patch('solenoid.emails.models.EmailMessage.send', autospec=True)
    def test_email_send_view_calls_function(self, mock_send):
        self.client.post(self.url, data={'emails': [1, 2]})
        email1 = EmailMessage.objects.get(pk=1)
        email2 = EmailMessage.objects.get(pk=2)
        expected = [call(email1), call(email2)]
        mock_send.assert_has_calls(expected, any_order=True)

    def test_subject_is_something_logical(self):
        email = EmailMessage.objects.get(pk=1)
        email.send()
        self.assertEqual(len(mail.outbox), 1)
        expected = 'OA outreach message to forward: {author}'.format(
            author=email.author.last_name)
        self.assertEqual(mail.outbox[0].subject, expected)

    def test_email_not_sent_when_missing_liaison(self):
        email = EmailMessage.objects.get(pk=3)
        assert not email.liaison  # check assumption: no liaison
        assert not email.date_sent  # check assumption: unsent
        self.assertFalse(email.send())
        self.assertEqual(len(mail.outbox), 0)
