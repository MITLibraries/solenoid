# -*- coding: utf-8 -*-
from datetime import date
import os

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse, resolve
from django.test import TestCase, Client

from solenoid.people.models import DLC, Author

from ..forms import _validate_csv
from ..models import Record
from ..views import UnsentList, InvalidList

# ------ MODELS ------
# Do I want to enforce choices on Record.dlc?
# Error handling - what do we do when a record does not have the required data?
# For instance, blank DLC

# ------ VIEWS ------
# People can filter it by DLC or search by author? Something useful, maybe with
# autocomplete, if that's not too many yaks
# But the first case should have it sorted by DLC and then author (per model default)
# People can select desired records
# (Also there should be a 'select entire DLC' option but that's JS I won't test here)
# Posting a set of records causes the email constructor to be invoked with that set


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

    def test_unsent_records_page_has_all_unsent_in_context(self):
        # assertQuerysetEqual never works, so we're just comparing the pks.
        self.assertEqual(
            set(UnsentList().get_queryset().values_list('pk')),
            set(Record.objects.filter(status=Record.UNSENT).values_list('pk')))

    def test_unsent_records_page_displays_all_unsent(self):
        c = Client()
        response = c.get(self.url)
        for record in Record.objects.filter(status=Record.UNSENT):
            self.assertContains(response, record.citation)


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


class ImportViewTest(TestCase):
    """Tests that make sure that the import view correctly verifies the
    imported CSV file and sets record properties accordingly."""

    def setUp(self):
        self.url = reverse('records:import')
        self.client = Client()

    def tearDown(self):
        Record.objects.all().delete()

    def test_import_records_url_exists(self):
        resolve(self.url)

    def test_import_records_view_renders(self):
        with self.assertTemplateUsed('records/import.html'):
            self.client.get(self.url)

    def _check_validation(self, testfile):
        basedir = os.path.dirname(os.path.abspath(__file__))
        with self.assertRaises(ValidationError):
            filename = os.path.join(basedir, 'csv', testfile)
            with open(filename, 'rb') as bad_csv:
                _validate_csv(bad_csv)

    def test_invalid_csv_rejected(self):
        # Inadmissible encoding
        self._check_validation('bad_encoding.csv')

        # Headers don't match data
        self._check_validation('invalid.csv')

        # A required header is missing
        self._check_validation('missing_headers.csv')

        # Seriously what even is this
        self._check_validation('this_is_a_cc0_kitten_pic_not_a_csv.jpeg')

    def _post_csv(self, testfile):
        basedir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(basedir, 'csv', testfile)
        with open(filename, 'rb') as csv_file:
            self.client.post(self.url, {'csv_file': csv_file})

    def test_author_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.author.first_name, 'Fake')
        self.assertEqual(record.author.last_name, 'Author')

    def test_records_without_authors_rejected(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_mit_id.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_author_data_filled_in_where_possible(self):
        dlc = DLC.objects.create(name='Some Department Or Other')
        Author.objects.create(
            first_name='Fake',
            last_name='Author',
            mit_id='123456789',
            dlc=dlc,
            email='fake@example.com'
        )
        self._post_csv('missing_author_first_name.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.author.first_name, 'Fake')
        self.assertEqual(record.author.last_name, 'Author')

    def test_publisher_name_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.publisher_name, 'Elsevier')

    def test_records_without_publishers_rejected(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_publisher_name.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_acq_method_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.acq_method, 'RECRUIT_FROM_AUTHOR_MANUSCRIPT')

    def test_records_without_acq_method_rejected(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_acq_method.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_records_with_unknown_acq_method_marked_invalid(self):
        orig_count = Record.objects.count()

        self._post_csv('bad_acq_method.csv')

        self.assertEqual(orig_count + 1, Record.objects.count())
        self.assertEqual(Record.objects.latest('pk').status, Record.INVALID)

    def test_citation_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.citation, 'Ramos, Itzel, et al. "Phenazines Affect Biofilm Formation by Pseudomonas Aeruginosa in Similar Ways at Various Scales." Research in Microbiology 161 3 (2010): 187-91.')  # noqa

    def test_records_without_citation_rejected(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_citation.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_status_set_when_present(self):
        assert False

    def test_records_without_status_marked_invalid(self):
        assert False

    def test_records_unknown_status_marked_invalid(self):
        assert False

    def test_status_timestamp_set_on_ingest(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        # This test may fail if run very close to midnight UTC.
        self.assertEqual(record.status_timestamp, date.today())

    def test_status_timestamp_set_when_emailed(self):
        assert False

    def test_doi_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.doi, '10.2105/12zh1')

    def test_fpv_records_without_doi_rejected(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_doi_fpv.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_manuscript_records_without_doi_accepted(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_doi_manuscript.csv')

        self.assertEqual(orig_count + 1, Record.objects.count())
        record = Record.objects.latest('pk')
        self.assertEqual(record.doi, '')
        self.assertEqual(record.acq_method, 'RECRUIT_FROM_AUTHOR_MANUSCRIPT')

    def test_encodings_handled_properly(self):
        """We should be able to roll with either cp1252 (Windows probable
        default), ascii, or utf-8."""
        assert False

    def test_blank_DLC_handled_correctly_known_author(self):
        # This should cause the author and DLC to exist.
        self._post_csv('single_good_record.csv')
        Record.objects.all().delete()

        # Verify our assumption that we know about this author.
        author = Author.objects.get(mit_id='123456789')
        self.assertEqual(author.dlc.name, 'Biology Department')

        self._post_csv('missing_dlc_known_author.csv')

        self.assertEqual(1, Record.objects.count())
        record = Record.objects.latest('pk')
        self.assertEqual(record.author.dlc.name, 'Biology Department')

    def test_blank_DLC_handled_correctly_unknown_author(self):
        orig_count = Record.objects.count()

        # Verify our assumption that we don't know about this author.
        with self.assertRaises(Author.DoesNotExist):
            Author.objects.get(mit_id='000000000')

        self._post_csv('missing_dlc_unknown_author.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_DLC_with_comma_handled_correctly(self):
        """Earth, Atmospheric, and Planetary Sciences should not break our
        CSV parsing."""
        assert False

    def test_emoji_handled_correctly(self):
        """I definitely promise someone will use emoji in their paper titles
        if they haven't already. Might be another decade before one shows up in
        a DLC name, but preparedness is key."""
        orig_count = Record.objects.count()

        self._post_csv('emoji.csv')

        self.assertEqual(orig_count + 1, Record.objects.count())

        record = Record.objects.latest('pk')
        self.assertIn('💖', record.citation)

    def test_paper_id_used_for_idempotency(self):
        assert False
