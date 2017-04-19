from django.core.urlresolvers import reverse, resolve
from django.test import TestCase, Client

from .models import Record
from .views import UnsentList, InvalidList

# ------ MODELS ------
# Do we want a unique_together enforcement? If so, which?
# Do I want to enforce choices on Record.dlc?
# A citation constructor - you're going to need one - only allow one format for
# now - do you need to allow for multiple item types?
#   Yes you do! You really want to use the Citation field rather than rolling
#   your own, but it needs to be complete.
# Error handling - what do we do when a record does not have the required data?
# For instance, blank DLC
# Do I need to enforce choices on the method of acq? I definitely need to clean it.
# The guidance field has HTML formatting - how do I want to handle that? If I
# save it as text and parse it later as html, will that work?
# Sorts by DLC and then last name

# ------ VIEWS ------
# People can filter it by DLC or search by author? Something useful, maybe with
# autocomplete, if that's not too many yaks
# But the first case should have it sorted by DLC and then author (per model default)
# People can select desired records
# (Also there should be a 'select entire DLC' option but that's JS I won't test here)
# Posting a set of records causes the email constructor to be invoked with that set
# There's a view that lists -invalid- records


class RecordModelTest(TestCase):
    fixtures = ['records.yaml']

    def test_status_options_are_enforced(self):
        """The system should not allow records to be saved with an invalid
        status. (Status is a parameter purely internal to solenoid.)"""
        # We're going to enumerate the choices here so we can control their
        # ordering, because some status transitions are invalid, and we don't
        # want to fail the test due to hitting them. But let's make sure our
        # enumeration remains valid as circumstances change.
        choices = [Record.UNSENT, Record.INVALID, Record.SENT]
        self.assertEqual(set(choices), set(Record.STATUS_CHOICES_LIST))

        record = Record.objects.filter(status=Record.UNSENT).first()

        # These should all work. If they don't, save() will throw an error and
        # the test will fail.
        for choice in choices:
            record.status = choice
            record.save()

        bad_choice = "noooope"
        assert bad_choice not in choices

        record.status = bad_choice
        with self.assertRaises(ValueError):
            record.save()

    def test_validate_acquisition_options(self):
        """The system should assign INVALID status to any record with an
        unrecognized acquisition method."""
        choices = Record.ACQ_METHODS_LIST
        # Ensure that the record's status is not INVALID, so that the status
        # we observe later will signify a meaningful change.
        record = Record.objects.filter(status=Record.UNSENT).first()

        # These should all work. If they don't, save() will throw an error and
        # the test will fail.
        for choice in choices:
            record.acq_method = choice
            record.save()

        bad_choice = "noooope"
        assert bad_choice not in choices

        record.acq_method = bad_choice
        record.save()
        self.assertEqual(record.status, Record.INVALID)

        # Trying again should not change the status.
        record.acq_method = bad_choice
        record.save()
        self.assertEqual(record.status, Record.INVALID)

    def test_cannot_set_sent_to_unsent(self):
        record = Record.objects.first()
        record.status = Record.SENT
        record.save()

        record.status = Record.UNSENT
        with self.assertRaises(ValueError):
            record.save()

    def test_cannot_set_sent_to_invalid(self):
        record = Record.objects.first()
        record.status = Record.SENT
        record.save()

        record.status = Record.INVALID
        with self.assertRaises(ValueError):
            record.save()


class UnsentRecordsViewsTest(TestCase):
    fixtures = ['records.yaml']

    def setUp(self):
        self.url = reverse('records:unsent_list')

    def test_unsent_records_url_exists(self):
        resolve(self.url)

    def test_unsent_records_view_renders(self):
        c = Client()
        with self.assertTemplateUsed('records/record_list.html'):
            c.get(self.url)

    def test_unsent_records_page_lists_all_unsent(self):
        # assertQuerysetEqual never works, so we're just comparing the pks.
        self.assertEqual(
            set(UnsentList().get_queryset().values_list('pk')),
            set(Record.objects.filter(status=Record.UNSENT).values_list('pk')))


class InvalidRecordsViewsTest(TestCase):
    fixtures = ['records.yaml']

    def setUp(self):
        self.url = reverse('records:invalid_list')

    def test_invalid_records_url_exists(self):
        resolve(self.url)

    def test_invalid_records_view_renders(self):
        c = Client()
        with self.assertTemplateUsed('records/record_list.html'):
            c.get(self.url)

    def test_invalid_records_page_lists_all_invalid(self):
        self.assertEqual(
            set(InvalidList().get_queryset().values_list('pk')),
            set(Record.objects.filter(status=Record.INVALID).values_list('pk'))) # noqa
