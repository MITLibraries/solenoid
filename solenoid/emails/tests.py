from unittest.mock import patch

from django.core.urlresolvers import reverse
from django.test import TestCase, Client

from .views import _email_create_many

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
        # See https://docs.python.org/3/library/unittest.mock.html#calls-as-tuples
        # for why this introspection syntax works.
        author_pks = [call[0][0].pk for call in mock_create_one.call_args_list]
        assert 1 in author_pks
        assert 3 in author_pks
        self.assertEqual(len(author_pks), 2)


    def test_email_to_field(self):
        """Generated emails must be to: the relevant liaison."""
        assert False


    def test_email_has_all_expected_records(self):
        """The email text includes all expected records."""
        assert False


    def test_invalid_records_do_not_get_emailed(self):
        """If the input set contains invalid records, they do not make it
        into the EmailMessage."""
        assert False


    def test_publisher_special_message_included(self):
        """The email text includes special messages for each publisher in its
        record set with a special message."""
        assert False


    def test_irrelevant_publisher_special_message_excluded(self):
        """The email text does not include special messages for publishers not
        in its record set."""
        assert False


    def test_fpv_accepted_message_included(self):
        """The Recruit from Author – FPV Accepted message is included if that is
        the recruitment strategy."""
        assert False


    def test_fpv_accepted_message_excluded(self):
        """The Recruit from Author – FPV Accepted message is NOT included if
        that ISN'T the recruitment strategy."""
        assert False


    def test_fpv_accepted_message_has_correct_count(self):
        """If the email has records subject to both policies, the message is
        included the correct number of times."""
        assert False

# Do we actually need to display the email to scholcomm, or just send to subject liaisons??
