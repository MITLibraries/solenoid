# -*- coding: utf-8 -*-
from datetime import date
import os
from string import Template
from unittest import skip

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse, resolve
from django.forms.models import model_to_dict
from django.template.defaultfilters import escape
from django.test import TestCase, Client, override_settings

from solenoid.emails.models import EmailMessage
from solenoid.people.models import DLC, Author, Liaison

from ..forms import _validate_csv
from ..helpers import Headers
from ..models import Record
from ..views import UnsentList

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
# Emails getting created from records (either test that emails are autocreated
# on import, or that they can be created manually)


@override_settings(LOGIN_REQUIRED=False)
class UnsentRecordsViewsTest(TestCase):
    fixtures = ['testdata.yaml']

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
            set(
                Record.objects.exclude(
                    email__date_sent__isnull=False).distinct().values_list(
                        'pk')
            )
        )

    def test_unsent_records_page_displays_all_unsent(self):
        c = Client()
        response = c.get(self.url)
        for record in Record.objects.exclude(email__date_sent__isnull=False):
            # Note that the citation will be auto-HTML-escaped when rendered,
            # so we need to test for the escaped form, not the database form.
            self.assertContains(response, escape(record.citation))


@override_settings(LOGIN_REQUIRED=False)
class ImportViewTest(TestCase):
    fixtures = ['testdata.yaml']
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
            return self.client.post(
                self.url, {'csv_file': csv_file}, follow=True)

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

    def test_records_with_unknown_acq_method_rejected(self):
        orig_count = Record.objects.count()

        self._post_csv('bad_acq_method.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_citation_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.citation, 'Ramos, Itzel, et al. "Phenazines Affect Biofilm Formation by Pseudomonas Aeruginosa in Similar Ways at Various Scales." Research in Microbiology 161 3 (2010): 187-91.')  # noqa

    def test_records_without_citation_rejected(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_citation.csv')

        self.assertEqual(orig_count, Record.objects.count())

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

    @skip
    def test_encodings_handled_properly(self):
        """We should be able to roll with either cp1252 (Windows probable
        default), ascii, or utf-8."""
        assert False

    def test_blank_DLC_handled_correctly_known_author(self):
        # This should cause the author and DLC to exist.
        self._post_csv('single_good_record.csv')
        Record.objects.all().delete()

        # Verify our assumption that we know about this author.
        author = Author.get_by_mit_id('123456789')
        self.assertEqual(author.dlc.name, 'Biology Department')

        self._post_csv('missing_dlc_known_author.csv')

        self.assertEqual(1, Record.objects.count())
        record = Record.objects.latest('pk')
        self.assertEqual(record.author.dlc.name, 'Biology Department')

    def test_blank_DLC_handled_correctly_unknown_author(self):
        orig_count = Record.objects.count()

        # Verify our assumption that we don't know about this author.
        with self.assertRaises(Author.DoesNotExist):
            Author.get_by_mit_id('000000000')

        self._post_csv('missing_dlc_unknown_author.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_DLC_with_comma_handled_correctly(self):
        """Earth, Atmospheric, and Planetary Sciences should not break our
        CSV parsing."""
        # This should not throw an error.
        self._post_csv('eaps.csv')
        record = Record.objects.latest('pk')
        self.assertEqual(record.author.dlc.name,
            "Earth, Atmospheric, and Planetary Sciences")

    def test_emoji_handled_correctly(self):
        """I definitely promise someone will use emoji in their paper titles
        if they haven't already. Might be another decade before one shows up in
        a DLC name, but preparedness is key."""
        orig_count = Record.objects.count()

        self._post_csv('emoji.csv')

        self.assertEqual(orig_count + 1, Record.objects.count())

        record = Record.objects.latest('pk')
        self.assertIn('❤️', record.citation)

    def test_diacritics_handled_correctly(self):
        orig_count = Record.objects.count()

        self._post_csv('diacritics.csv')

        self.assertEqual(orig_count + 1, Record.objects.count())

        record = Record.objects.latest('pk')
        assert 'Díânne Ç' == record.author.first_name
        assert 'Newmån' == record.author.last_name

    def test_nonroman_characters_handled_correctly(self):
        orig_count = Record.objects.count()

        self._post_csv('nonroman_characters.csv')

        self.assertEqual(orig_count + 1, Record.objects.count())

        record = Record.objects.latest('pk')
        assert '平仮名' == record.author.last_name
        assert '훈민정음' == record.author.first_name
        # This is from a Chinese lipsum generator, so not only do I not know
        # what it means, it probably doesn't mean anything.
        assert '医父逃心需者決応術紙女特周保形四困' == record.citation

    def test_math_handled_correctly(self):
        orig_count = Record.objects.count()

        self._post_csv('math_symbols.csv')

        self.assertEqual(orig_count + 1, Record.objects.count())

        record = Record.objects.latest('pk')
        self.assertIn('∫', record.citation)
        self.assertIn('π', record.citation)
        self.assertIn('ℵ', record.citation)
        # This test is keepin' it real.
        self.assertIn('ℝ', record.citation)

    @skip
    def test_paper_id_respected_case_1(self):
        """
        If we re-import an UNSENT record with a known ID, we should edit the
        existing record, not create a new one."""
        with self.assertRaises(Record.DoesNotExist):
            Record.objects.get(paper_id='182960')

        self._post_csv('single_good_record.csv')
        orig_count = Record.objects.count()
        record = Record.objects.latest('pk')

        self.assertEqual(record.paper_id, '182960')  # check assumptions
        self.assertEqual(record.status, Record.UNSENT)
        orig_record = model_to_dict(record)

        self._post_csv('single_good_record.csv')
        self.assertEqual(orig_count, Record.objects.count())
        self.assertEqual(orig_record,
                         model_to_dict(Record.objects.get(paper_id='182960')))

    def test_paper_id_respected_case_2(self):
        """
        If we re-import an already sent record with a known ID & author, we
        should raise a warning and leave the existing record alone, not create
        a new one."""
        orig_count = Record.objects.count()
        with self.assertRaises(Record.DoesNotExist):
            Record.objects.get(paper_id='182960')

        self._post_csv('single_good_record.csv')
        new_count = Record.objects.count()
        self.assertEqual(orig_count + 1, new_count)
        record = Record.objects.latest('pk')

        self.assertEqual(record.paper_id, '182960')
        liaison = Liaison.objects.create(first_name='foo',
            last_name='bar',
            email_address='fake@example.com')

        email = EmailMessage.objects.create(original_text='gjhdka',
            date_sent=date.today(),
            author=record.author,
            _liaison=liaison)

        record.email = email
        record.save()

        orig_record = model_to_dict(record)

        response = self._post_csv('single_good_record.csv')
        self.assertEqual(new_count, Record.objects.count())
        self.assertEqual(orig_record,
                         model_to_dict(Record.objects.get(paper_id='182960')))

        self.assertIn('info',
                      [m.level_tag for m in response.context['messages']])

    @skip
    def test_paper_id_respected_case_3(self):
        """
        If we have an INVALID record and re-import valid data with the same
        paper ID, we should overwrite the existing record with the new
        (hopefully better) data, not create a new record. This includes
        updating the status to UNSENT and notifying the user."""
        with self.assertRaises(Record.DoesNotExist):
            Record.objects.get(paper_id='182960')

        self._post_csv('single_good_record.csv')
        orig_count = Record.objects.count()
        record = Record.objects.latest('pk')

        self.assertEqual(record.paper_id, '182960')
        record.status = Record.INVALID
        record.publisher_name = 'Super dodgy publisher name'
        record.save()

        expected_record = model_to_dict(record)
        expected_record['publisher_name'] = 'Elsevier'
        expected_record['status'] = Record.UNSENT

        response = self._post_csv('single_good_record.csv')
        self.assertEqual(orig_count, Record.objects.count())
        self.assertEqual(expected_record,
                         model_to_dict(Record.objects.get(paper_id='182960')))

        self.assertIn('info',
                      [m.level_tag for m in response.context['messages']])

    @skip
    def test_paper_id_respected_case_4(self):
        """
        If we have an INVALID record and re-import invalid data with the same
        paper ID, we should leave the record alone and warn the user."""
        with self.assertRaises(Record.DoesNotExist):
            Record.objects.get(paper_id='182960')

        self._post_csv('single_good_record.csv')
        orig_count = Record.objects.count()
        record = Record.objects.latest('pk')

        self.assertEqual(record.paper_id, '182960')
        record.status = Record.INVALID
        record.publisher_name = 'Super dodgy publisher name'
        record.save()

        orig_record = model_to_dict(record)

        response = self._post_csv('missing_publisher_name.csv')
        self.assertEqual(orig_count, Record.objects.count())
        self.assertEqual(orig_record,
                         model_to_dict(Record.objects.get(paper_id='182960')))

        self.assertIn('warning',
                      [m.level_tag for m in response.context['messages']])

    def test_paper_id_respected_case_5(self):
        """
        If we re-import an already sent record with a known ID and a new
        author, we should raise a warning and not create a new record."""
        # First, import the basic CSV.
        orig_count = Record.objects.count()
        with self.assertRaises(Record.DoesNotExist):
            Record.objects.get(paper_id='182960')

        self._post_csv('single_good_record.csv')
        new_count = Record.objects.count()
        self.assertEqual(orig_count + 1, new_count)
        record = Record.objects.latest('pk')

        self.assertEqual(record.paper_id, '182960')
        liaison = Liaison.objects.create(first_name='foo',
            last_name='bar',
            email_address='fake@example.com')

        email = EmailMessage.objects.create(original_text='gjhdka',
            date_sent=date.today(),
            author=record.author,
            _liaison=liaison)

        record.email = email
        record.save()

        orig_record = model_to_dict(record)

        # Next, import new CSV of the same paper as recorded under a different
        # author. This should *not* create any new records.
        response = self._post_csv('single_good_record_new_author.csv')
        self.assertEqual(new_count, Record.objects.count())
        self.assertEqual(orig_record,
                         model_to_dict(Record.objects.get(paper_id='182960')))

        self.assertIn('info',
                      [m.level_tag for m in response.context['messages']])

    def test_form_includes_multipart(self):
        """If you forgot to add the enctype to the form, the data won't post
        and the form won't validate even if everything else is correct."""
        response = self.client.get(self.url)
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_special_message_added(self):
        # Case 1: the special message field is blank.
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertFalse(record.message)

        # Case 2: the special message field is not blank.
        # Note that this record has a different paper ID and author than the
        # first one - that's important, as it means we're creating a new record
        # rather than accessing the existing one, which may not have a message,
        # depending on how we ultimately handle citation updates. (Changing
        # PaperID alone isn't enough, since the system would recognize that the
        # records have the same author and citation, and reject the second as
        # a duplicate.)
        self._post_csv('single_good_record_with_message.csv')

        record2 = Record.objects.latest('pk')
        self.assertEqual(record2.message.text, 'special message goes here')

        # Case 3: the special message field is not blank, *and* it's one we've
        # seen before.
        # Note that this CSV is the same as single_good_record_with_message,
        # except for a different paper ID and author.
        self._post_csv('single_good_record_with_message_2.csv')

        record3 = Record.objects.latest('pk')
        self.assertEqual(record3.message.text, 'special message goes here')
        self.assertEqual(record2.message, record3.message)


class RecordModelTest(TestCase):
    fixtures = ['testdata.yaml']

    def test_is_record_creatable(self):
        # Data includes the basics? Good!
        data = {
            Headers.PUBLISHER_NAME: 'foo',
            Headers.ACQ_METHOD: 'random',
            Headers.CITATION: 'nonempty'
        }
        assert Record.is_record_creatable(data)

        # Missing data for required basics? Bad!
        data = {
            Headers.PUBLISHER_NAME: 'foo',
            Headers.ACQ_METHOD: 'random',
            Headers.CITATION: ''
        }
        assert not Record.is_record_creatable(data)

        data = {
            Headers.PUBLISHER_NAME: 'foo',
            Headers.ACQ_METHOD: '',
            Headers.CITATION: 'nonempty'
        }
        assert not Record.is_record_creatable(data)

        data = {
            Headers.PUBLISHER_NAME: '',
            Headers.ACQ_METHOD: 'random',
            Headers.CITATION: 'nonempty'
        }
        assert not Record.is_record_creatable(data)

        # RECRUIT_FROM_AUTHOR_FPV_ACCEPTED requires a DOI.
        data = {
            Headers.PUBLISHER_NAME: 'foo',
            Headers.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED',
            Headers.CITATION: 'nonempty',
            Headers.DOI: ''
        }
        assert not Record.is_record_creatable(data)

        data = {
            Headers.PUBLISHER_NAME: 'foo',
            Headers.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED',
            Headers.CITATION: 'nonempty',
            Headers.DOI: '4217896'
        }
        assert Record.is_record_creatable(data)

    def test_is_valid(self):
        record = Record.objects.get(pk=1)
        record.acq_method = 'NOT_A_METHOD'
        record.save()

        # acq_method not in ACQ_METHODS_LIST: invalid
        assert not record.is_valid

        # RECRUIT_FROM_AUTHOR_FPV_ACCEPTED and no DOI: invalid
        record.acq_method = 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED'
        record.doi = ''
        record.save()
        assert not record.is_valid

        # RECRUIT_FROM_AUTHOR_FPV_ACCEPTED and yes DOI: valid
        record.doi = '53297853'
        record.save()
        assert record.is_valid

        # RECRUIT_FROM_AUTHOR_MANUSCRIPT and no DOI: valid
        record.acq_method = 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'
        record.doi = ''
        record.save()
        assert record.is_valid

        # RECRUIT_FROM_AUTHOR_MANUSCRIPT and yes DOI: valid
        record.doi = '53297853'
        record.save()
        assert record.is_valid

    def test_is_sent(self):
        # Record with an email that hasn't been sent
        record = Record.objects.get(pk=1)
        email = record.email
        email.date_sent = None
        email.save()
        assert not record.is_sent

        # Record with an email that has been sent
        email.date_sent = date.today()
        email.save()
        assert record.is_sent

        # Record with no email
        record = Record.objects.get(pk=2)
        assert not record.is_sent

    def test_fpv_message(self):
        record = Record.objects.get(pk=1)
        record.acq_method = 'not fpv'
        record.save()

        assert record.fpv_message is None

        fake_doi = 'fake_doi'
        publisher_name = 'fake_publisher'
        record.acq_method = 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED'
        record.doi = fake_doi
        record.publisher_name = publisher_name
        record.save()

        msg = Template('<b>[Note: $publisher_name allows authors to download '
                       'and deposit the final published article, but does not '
                       'allow the Libraries to perform the downloading. If you ' # noqa
                       'follow this link, download the article, and attach it '
                       'to an email reply, we can deposit it on your behalf: '
                       '<a href="https://dx.doi.org.libproxy.mit.edu/$doi">https://dx.doi.org.libproxy.mit.edu/$doi</a>]</b>')  # noqa

        assert record.fpv_message == msg.substitute(
            publisher_name=publisher_name, doi=fake_doi)

    def test_get_or_create_from_csv(self):
        author = Author.objects.get(pk=1)
        record, created = Record.get_or_create_from_csv(
            author, {Headers.PAPER_ID: 1})
        assert record.pk == 1
        assert not created

        row = {
            Headers.PUBLISHER_NAME: 'publisher_name',
            Headers.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED',
            Headers.CITATION: 'citation',
            Headers.DOI: 'doi',
            Headers.PAPER_ID: 'paper_id',
            Headers.SOURCE: 'Manual',
            Headers.RECORD_ID: '841-1758293x-15',
        }

        record, created = Record.get_or_create_from_csv(author, row)
        assert created
        assert record.publisher_name == 'publisher_name'
        assert record.acq_method == 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED'
        assert record.citation == 'citation'
        assert record.doi == 'doi'
        assert record.paper_id == 'paper_id'
        assert record.source == 'Manual'
        assert record.elements_id == '841-1758293x-15'

    def test_get_duplicates_1(self):
        """There are no duplicates: this should return None."""

        row = {
            Headers.PUBLISHER_NAME: 'publisher_name',
            Headers.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED',
            Headers.CITATION: 'citation',
            Headers.DOI: 'doi',
            Headers.PAPER_ID: 'paper_id',
            Headers.SOURCE: 'Manual',
            Headers.RECORD_ID: '841-1758293x-15',
        }
        author = Author.objects.get(pk=1)

        assert Record.get_duplicates(author, row) is None

    def test_get_duplicates_2(self):
        """There's a paper with the same citation but a different author;
        this should return None."""

        row = {
            Headers.PUBLISHER_NAME: 'Wiley',
            Headers.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED',
            Headers.CITATION: 'Fermi, Enrico. Paper name. Some journal or other. 145:5 (2016)',
            Headers.DOI: '10.1412/4678156',
            Headers.PAPER_ID: 'paper_id',
            Headers.SOURCE: 'Manual',
            Headers.RECORD_ID: '841-1758293x-15',
            Headers.FIRST_NAME: 'Different',
            Headers.LAST_NAME: 'Author',
            Headers.MIT_ID: 214614,
        }

        # Check assumption - we don't have this author in the db at all, so
        # we can't have a record associated with this author yet
        id_hash = Author.get_hash('214614')
        assert not Author.objects.filter(_mit_id_hash=id_hash)

        author = Author.objects.create(
            first_name='Different',
            last_name='Author',
            _mit_id_hash=id_hash,
            dlc=DLC.objects.first(),
            email='da@example.com'
        )

        assert Record.get_duplicates(author, row) is None

    def test_get_duplicates_3(self):
        """There's a paper with the same citation, the same author, and a
        different paper_id; this should return that duplicate."""
        # Check assumption
        assert not Record.objects.filter(paper_id=24618)

        # This is a duplicate of record #2, except for the paper ID.
        row = {
            Headers.PUBLISHER_NAME: 'Nature',
            Headers.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED',
            Headers.CITATION: 'Tonegawa, Susumu. Paper name. Some journal or other. 31:4 (2012)',
            Headers.DOI: '10.1240.2/4914241',
            Headers.PAPER_ID: '24618',
            Headers.SOURCE: 'Manual',
            Headers.RECORD_ID: '841-1758293x-15',
            Headers.FIRST_NAME: 'Susumu',
            Headers.LAST_NAME: 'Tonegawa',
            Headers.MIT_ID: '2',
        }
        author = Author.objects.get(last_name='Tonegawa')

        dupes = Record.get_duplicates(author, row)
        assert dupes.count() == 1
        assert int(dupes[0].paper_id) == 123141
