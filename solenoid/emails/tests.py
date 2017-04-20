from unittest.mock import patch

from django.core.urlresolvers import reverse
from django.test import TestCase, Client

class EmailCreatorTestCase(TestCase):
    fixtures = ['records.yaml']

    @patch('solenoid.emails.views.email_bulk_create')
    def test_posting_to_create_view_calls_creator(self, mock_bulk_create):
        c = Client()
        c.post(reverse('emails:create'), {'records': ['1']})
        mock_bulk_create.assert_called_once_with(['1'])

        mock_bulk_create.reset_mock()
        c.post(reverse('emails:create'), {'records': ['1', '2']})
        mock_bulk_create.assert_called_once_with(['1', '2'])


    def test_posting_to_create_view_returns_email_eval(self):
        c = Client()
        response = c.post(reverse('emails:create'), {'records': ['1']})
        self.assertRedirects(response, reverse('emails:evaluate'))


    def test_email_created_for_each_professor(self):
        """Given a set of records, must produce an email for each professor
        associated with any record."""
        assert False


    def test_email_to_field(self):
        """Generated emails must be to: the relevant liaison."""
        assert False


    def test_email_has_all_expected_records(self):
        """The email text includes all expected records."""
        assert False


    def test_invalid_records_do_not_get_emailed(self):
        """If the input set contains invalid records, they do not make it
        into the email."""
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
