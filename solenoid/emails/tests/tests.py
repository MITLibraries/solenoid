from datetime import date
from unittest.mock import patch

from django.core.urlresolvers import reverse
from django.test import TestCase, Client, override_settings

from solenoid.people.models import Author, Liaison
from solenoid.records.models import Record

from ..models import EmailMessage
from ..views import _email_create_many, _email_create_one


@override_settings(LOGIN_REQUIRED=False)
class EmailCreatorTestCase(TestCase):
    fixtures = ['records.yaml']

    @patch('solenoid.emails.views._email_create_many')
    def test_posting_to_create_view_calls_creator(self, mock_create_many):
        c = Client()
        c.post(reverse('emails:create'), {'records': ['1']})
        mock_create_many.assert_called_once_with(['1'])

        mock_create_many.reset_mock()
        c.post(reverse('emails:create'), {'records': ['1', '2']})
        mock_create_many.assert_called_once_with(['1', '2'])

    def test_posting_to_create_view_returns_email_eval(self):
        c = Client()
        response = c.post(reverse('emails:create'), {'records': ['1']})
        self.assertRedirects(response, reverse('emails:evaluate'))

    @patch('solenoid.emails.views._email_create_one')
    def test_email_created_for_each_professor(self, mock_create_one):
        """Given a set of records, the email bulk creator function must call the
        single email creation function exactly once for each professor
        associated with any record."""
        # These 3 records are associated with two authors: Fermi (pk=1) an
        # Liskov (pk=3; authored two of these records). Therefore we expect
        # _email_create_one to be called once, and only once, for each of these
        # authors, and for no one else.
        _email_create_many(['1', '3', '4'])
        # See https://docs.python.org/3/library/unittest.mock.html#calls-as-tuples # noqa
        # for why this introspection syntax works.
        author_pks = [call[0][0].pk for call in mock_create_one.call_args_list]
        assert 1 in author_pks
        assert 3 in author_pks
        self.assertEqual(len(author_pks), 2)

    @patch('solenoid.emails.views._email_create_one')
    def test_create_many_passes_correct_record_set(self, mock_create_one):
        """Given a set of records, the email bulk creator function must pass
        the expected records for each author to the single email creation
        function."""
        _email_create_many(['1', '3', '4'])

        # This gives us a dict with {pk of author: [list of pks of records]}
        # for ease of testing.
        arg_sets = {call[0][0].pk: [record.pk for record in call[0][1]]
                    for call in mock_create_one.call_args_list}
        self.assertEqual(arg_sets[1], [1])
        self.assertEqual(arg_sets[3], [3, 4])

    def test_email_recipient(self):
        """The email created by _email_create_one must be to: the relevant
        liaison."""
        # Expected to be a paper by Fermi, who belongs to Physics, whose
        # liaison is Krug.
        record = Record.objects.get(pk=1)
        _email_create_one(record.author, [record])
        email = EmailMessage.objects.latest('pk')
        self.assertEqual(email.liaison.pk, 1)

    def test_email_has_all_expected_records(self):
        """The email text includes all expected records."""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        _email_create_one(records[0].author, records)
        email = EmailMessage.objects.latest('pk')
        assert Record.objects.get(pk=3).citation in email.original_text
        assert Record.objects.get(pk=4).citation in email.original_text

    def test_invalid_records_do_not_get_emailed(self):
        """If the input set contains invalid records, they do not make it
        into the EmailMessage."""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        _email_create_one(records[0].author, records)
        email = EmailMessage.objects.latest('pk')
        assert Record.objects.get(pk=5).citation not in email.original_text

    def test_already_sent_records_do_not_get_emailed(self):
        """If the input set contains invalid records, they do not make it
        into the EmailMessage."""
        records = Record.objects.filter(pk__in=[2, 3, 4, 5])
        _email_create_one(records[0].author, records)
        email = EmailMessage.objects.latest('pk')
        assert Record.objects.get(pk=2).citation not in email.original_text

    @patch.dict('solenoid.emails.helpers.SPECIAL_MESSAGES',
                {'ACM-Special Message': 'A very special message'})
    def test_publisher_special_message_included(self):
        """The email text includes special messages for each publisher in its
        record set with a special message."""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        _email_create_one(records[0].author, records)
        email = EmailMessage.objects.latest('pk')
        self.assertEqual(email.original_text.count('A very special message'),
                         1)

    @patch.dict('solenoid.emails.helpers.SPECIAL_MESSAGES',
                {'Scholastic': 'A very special message',
                 'Wiley': 'An equally special message'})
    def test_irrelevant_publisher_special_message_excluded(self):
        """The email text does not include special messages for publishers not
        in its record set."""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        _email_create_one(records[0].author, records)
        email = EmailMessage.objects.latest('pk')
        self.assertNotIn('A very special message', email.original_text)
        self.assertNotIn('An equally special message', email.original_text)

    def test_html_rendered_as_html(self):
        """Make sure that we see <p>, not &lt;p&gt;, and so forth, in our
        constructed email text. (If we put {{ citations }} into the email
        template without the |safe filter, we'll end up with escaped HTML,
        which is no good for our purposes.)"""
        records = Record.objects.filter(pk__in=[3, 4, 5])
        _email_create_one(records[0].author, records)
        email = EmailMessage.objects.latest('pk')
        self.assertNotIn('&lt;p&gt;', email.original_text)

    def test_fpv_accepted_message_included(self):
        """The Recruit from Author - FPV Accepted message is included if that is
        the recruitment strategy."""
        # Record 4 should have an fpv message; 3 does not
        records = Record.objects.filter(pk__in=[3, 4])
        _email_create_one(records[0].author, records)
        email = EmailMessage.objects.latest('pk')
        self.assertIn(Record.objects.get(pk=4).fpv_message,
                      email.original_text)

    def test_fpv_accepted_message_excluded(self):
        """The Recruit from Author - FPV Accepted message is NOT included if
        that ISN'T the recruitment strategy."""
        record = Record.objects.get(pk=3)
        _email_create_one(record.author, [record])
        email = EmailMessage.objects.latest('pk')
        msg = 'allows authors to download and deposit the final published ' \
              'article, but does not allow the Libraries to perform the ' \
              'downloading'
        self.assertNotIn(msg, email.original_text)

    def test_emails_get_cced_to_scholcomm(self):
        assert False

    def test_email_author_without_liaison(self):
        """Something logical should happen."""
        assert False


@override_settings(LOGIN_REQUIRED=False)
class EmailEvaluateTestCase(TestCase):
    fixtures = ['emails.yaml']

    def setUp(self):
        self.url = reverse('emails:evaluate')
        self.client = Client()

    def test_latest_version_displays_on_unsent_page_if_not_blank(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Most recent text of email 1")

    def test_liaison_email_address_displays(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'krug@example.com')
        self.assertEqual(response.content.count(b'krug@example.com'), 2)

    def test_users_can_save_changes_to_emails(self):
        orig_text_1 = EmailMessage.objects.get(pk=2).latest_text

        new_text = 'This is what we change the email to'
        self.client.post(self.url, {
            'form-TOTAL_FORMS': 2,
            'form-INITIAL_FORMS': 2,
            # 'form-MIN_NUM_FORMS': 0,
            'form-0-latest_text': new_text,     # change this
            'form-0-id': 1,
            'form-1-latest_text': orig_text_1,  # don't change this
            'form-1-id': 2,
        })

        self.assertEqual(new_text,
            EmailMessage.objects.get(pk=1).latest_text)
        self.assertEqual(orig_text_1,
            EmailMessage.objects.get(pk=2).latest_text)

    def test_only_unsent_emails_appear(self):
        sent_email = EmailMessage.objects.get(pk=1)
        sent_email.date_sent = date.today()
        sent_email.save()

        response = self.client.get(self.url)
        self.assertNotContains(response, "Most recent text of email 1")
        self.assertContains(response, "Original text of email 2")

    def test_revert_changes_button_appears(self):
        response = self.client.get(self.url)
        for email in EmailMessage.objects.filter(date_sent__isnull=True):
            url = reverse('emails:revert', args=(email.pk,))
            self.assertContains(response, url)


@override_settings(LOGIN_REQUIRED=False)
class EmailMessageModelTestCase(TestCase):
    fixtures = ['emails.yaml']

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

# https://pypi.python.org/pypi/html2text - might be of use if we need to
# generate multipart.
