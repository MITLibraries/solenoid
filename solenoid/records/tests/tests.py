# -*- coding: utf-8 -*-
import copy
import hashlib
import os
from datetime import date
from string import Template

from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.template.defaultfilters import escape
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse
from solenoid.emails.models import EmailMessage
from solenoid.people.models import DLC, Author, Liaison

from ..forms import _validate_csv
from ..helpers import Fields
from ..models import Record
from ..views import UnsentList


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

        # Fields don't match data
        self._check_validation('invalid.csv')

        # A required field is missing
        self._check_validation('missing_fields.csv')

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
            dspace_id='123456789',
            dlc=dlc,
            email='fake@example.com'
        )
        self._post_csv('missing_author_first_name.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.author.first_name, 'Fake')
        self.assertEqual(record.author.last_name, 'Author')

    def test_author_dspace_id_added_if_needed(self):
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
        self.assertEqual(record.author.dspace_id,
                         hashlib.md5((os.getenv('DSPACE_AUTHOR_ID_SALT',
                                                'salty') +
                                     '123456789').encode('utf-8')).hexdigest())

    def test_publisher_name_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.publisher_name, 'Elsevier')

    def test_records_without_publishers_accepted_if_not_fpv(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_publisher_name_non_fpv.csv')

        self.assertEqual(orig_count + 1, Record.objects.count())

    def test_records_without_publishers_rejected_if_fpv(self):
        orig_count = Record.objects.count()

        self._post_csv('missing_publisher_name_fpv.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_acq_method_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.acq_method, 'RECRUIT_FROM_AUTHOR_MANUSCRIPT')

    def test_records_with_unknown_acq_method_rejected(self):
        orig_count = Record.objects.count()

        self._post_csv('bad_acq_method.csv')

        self.assertEqual(orig_count, Record.objects.count())

    def test_records_with_new_acq_methods_accepted(self):
        orig_count = Record.objects.count()

        self._post_csv('new_acq_methods2.csv')

        self.assertEqual(orig_count + 2, Record.objects.count())

    def test_citation_set_when_present(self):
        self._post_csv('single_good_record.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.citation, 'Ramos, Itzel, et al. "Phenazines Affect Biofilm Formation by Pseudomonas Aeruginosa in Similar Ways at Various Scales." Research in Microbiology 161 3 (2010): 187-91.')  # noqa

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

    # We don't need to test ASCII encoding because single_good_record.csv is
    # ascii-encoded, so it is implicitly tested throughout this file.

    def test_encodings_handled_properly_utf_8(self):
        # The delete statement in tearDown is insufficient because it will
        # actually just truncate; then the post may refuse to import the
        # record because it has the same author and citation as an existing
        # record. Let's make sure to find and delete any such records before
        # posting.
        Record.objects.filter(doi='10.2105/12zh1').delete()
        self._post_csv('single_good_record_utf_8.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.doi, '10.2105/12zh1')

    def test_encodings_handled_properly_utf_8_sig(self):
        Record.objects.filter(doi='10.2105/12zh1').delete()
        self._post_csv('single_good_record_utf_8_sig.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.doi, '10.2105/12zh1')

    def test_encodings_handled_properly_iso_8859_1(self):
        Record.objects.filter(doi='10.2105/12zh1').delete()
        self._post_csv('single_good_record_iso_8859_1.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.doi, '10.2105/12zh1')

    def test_encodings_handled_properly_windows_1252(self):
        Record.objects.filter(doi='10.2105/12zh1').delete()
        self._post_csv('single_good_record_windows_1252.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.doi, '10.2105/12zh1')

    def test_encodings_handled_properly_windows_1254(self):
        Record.objects.filter(doi='10.2105/12zh1').delete()
        self._post_csv('single_good_record_windows_1254.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.doi, '10.2105/12zh1')

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

    def test_paper_id_respected_case_1(self):
        """
        If we re-import an UNSENT record with a known ID, we should leave the
        existing record alone and not create a new one."""
        with self.assertRaises(Record.DoesNotExist):
            Record.objects.get(paper_id='182960')

        self._post_csv('single_good_record.csv')
        orig_count = Record.objects.count()
        record = Record.objects.latest('pk')

        self.assertEqual(record.paper_id, '182960')  # check assumptions
        orig_record = model_to_dict(record)

        self._post_csv('single_good_record.csv')
        self.assertEqual(orig_count, Record.objects.count())
        self.assertEqual(orig_record,
                         model_to_dict(Record.objects.get(paper_id='182960')))

    def test_paper_id_respected_case_2(self):
        """
        If we re-import an UNSENT record with a known ID and altered data, we
        should update the existing record and not create a new one."""
        with self.assertRaises(Record.DoesNotExist):
            Record.objects.get(paper_id='182960')

        self._post_csv('single_good_record.csv')
        orig_count = Record.objects.count()
        record = Record.objects.latest('pk')

        self.assertEqual(record.paper_id, '182960')  # check assumptions
        orig_record = model_to_dict(record)
        orig_doi = orig_record.pop('doi')

        self._post_csv('single_good_record_new_doi.csv')
        self.assertEqual(orig_count, Record.objects.count())
        new_record = model_to_dict(Record.objects.get(paper_id='182960'))
        new_doi = new_record.pop('doi')
        self.assertEqual(orig_record, new_record)
        self.assertNotEqual(new_doi, orig_doi)

    def test_paper_id_respected_case_3(self):
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

    def test_paper_id_respected_case_4(self):
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

    def test_tableau_file(self):
        """Make sure that uploading utf-16le works, since that's what we get
        from Tableau crosstab exports."""
        self._post_csv('utf16le.csv')

        record = Record.objects.latest('pk')
        self.assertEqual(record.doi, '10.7717/peerj.1234')
        self.assertEqual(record.author.first_name, 'Tanja')
        self.assertEqual(record.author.last_name, 'Bosak')


class RecordModelTest(TestCase):
    fixtures = ['testdata.yaml']

    def setUp(self):
        # A dict containing all the EXPECTED_FIELDS.
        self.paper_data = {
            Fields.EMAIL: 'test@example.com',
            Fields.DOI: '10.5137/527va',
            Fields.FIRST_NAME: 'William Barton',
            Fields.LAST_NAME: 'Rogers',
            Fields.MIT_ID: '1',
            Fields.PUBLISHER_NAME: 'Haus of Books',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.DLC: "President's Office",
            Fields.PAPER_ID: '895327',
            Fields.MESSAGE: '',
        }

        # MIT physics professor Frank Wilczek coauthored this paper, for which
        # he won the Nobel prize in 2004.
        self.citation_data = {
            Fields.FIRST_NAME: 'Frank',
            Fields.LAST_NAME: 'Wilczek',
            Fields.PUBDATE: '19730625',
            Fields.VOLUME: '30',
            Fields.ISSUE: '26',
            Fields.DOI: '10.1103/PhysRevLett.30.1343',
            Fields.JOURNAL: 'Physical Review Letters',
            Fields.TITLE: 'Ultraviolet behavior of non-abelian gauge theories'
        }

    # need to actually test create_citation
    def test_is_metadata_valid_yes_citation_no_citation_data(self):
        metadata = copy.copy(self.paper_data)
        metadata[Fields.CITATION] = 'This is a citation'
        metadata[Fields.TITLE] = None
        metadata[Fields.JOURNAL] = None
        assert Record.is_data_valid(metadata)

    def test_is_metadata_valid_no_citation_yes_citation_data(self):
        metadata = copy.copy(self.paper_data)
        metadata[Fields.CITATION] = None
        metadata[Fields.TITLE] = 'This is a paper title'
        metadata[Fields.JOURNAL] = 'Journal of Awesomeness'
        assert Record.is_data_valid(metadata)

    def test_is_metadata_valid_no_citation_no_citation_data(self):
        metadata = copy.copy(self.paper_data)
        metadata[Fields.CITATION] = None
        metadata[Fields.TITLE] = None
        metadata[Fields.JOURNAL] = None
        assert not Record.is_data_valid(metadata)

    def test_is_record_creatable(self):
        # Data includes the basics? Good!
        data = {
            Fields.PUBLISHER_NAME: 'foo',
            Fields.ACQ_METHOD: Record.ACQ_MANUSCRIPT,
            Fields.CITATION: 'nonempty'
        }
        assert Record.is_record_creatable(data)

        data = {
            Fields.PUBLISHER_NAME: 'foo',
            Fields.ACQ_METHOD: '',
            Fields.CITATION: 'nonempty'
        }
        assert Record.is_record_creatable(data)

        # Missing data for required basics? Bad!
        data = copy.copy(self.paper_data)
        data.update(self.citation_data)
        data[Fields.CITATION] = ''
        data[Fields.FIRST_NAME] = ''
        assert not Record.is_record_creatable(data)

        data = {
            Fields.PUBLISHER_NAME: '',
            Fields.ACQ_METHOD: 'random',
            Fields.CITATION: 'nonempty'
        }
        assert not Record.is_record_creatable(data)

        data = {
            Fields.PUBLISHER_NAME: 'foo',
            # No acq method column at all
            Fields.CITATION: 'nonempty'
        }

        # RECRUIT_FROM_AUTHOR_FPV requires a DOI.
        data = {
            Fields.PUBLISHER_NAME: 'foo',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'nonempty',
            Fields.DOI: ''
        }
        assert not Record.is_record_creatable(data)

        data = {
            Fields.PUBLISHER_NAME: 'foo',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'nonempty',
            Fields.DOI: '4217896'
        }
        assert Record.is_record_creatable(data)

    def test_is_valid_unknown_acq(self):
        record = Record.objects.get(pk=1)
        record.acq_method = 'NOT_A_METHOD'
        record.save()

        # acq_method not in ACQ_METHODS_LIST: invalid
        assert not record.is_valid

    def test_is_valid_fpv_but_no_doi(self):
        record = Record.objects.get(pk=1)
        # RECRUIT_FROM_AUTHOR_FPV and no DOI: invalid
        record.acq_method = 'RECRUIT_FROM_AUTHOR_FPV'
        record.doi = ''
        record.save()
        assert not record.is_valid

    def test_is_valid_fpv_but_has_doi(self):
        record = Record.objects.get(pk=1)
        # RECRUIT_FROM_AUTHOR_FPV and yes DOI: valid
        record.doi = '53297853'
        record.save()
        assert record.is_valid

    def test_is_valid_not_fpv_and_no_doi(self):
        record = Record.objects.get(pk=1)
        # RECRUIT_FROM_AUTHOR_MANUSCRIPT and no DOI: valid
        record.acq_method = 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'
        record.doi = ''
        record.save()
        assert record.is_valid

    def test_is_valid_not_fpv_and_not_doi(self):
        record = Record.objects.get(pk=1)
        # RECRUIT_FROM_AUTHOR_MANUSCRIPT and yes DOI: valid
        record.doi = '53297853'
        record.save()
        assert record.is_valid

    def test_is_valid_no_citation(self):
        record = Record.objects.get(pk=1)
        record.citation = None
        with self.assertRaises(ValidationError):
            record.save()

    def test_is_valid_blank_citation(self):
        record = Record.objects.get(pk=1)
        record.citation = ''
        with self.assertRaises(ValidationError):
            record.save()

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
        record.acq_method = 'RECRUIT_FROM_AUTHOR_FPV'
        record.doi = fake_doi
        record.publisher_name = publisher_name
        record.save()

        msg = Template('<b>[Note: $publisher_name allows authors to download '
                       'and deposit the final published article, but does not '
                       'allow the Libraries to perform the downloading. If you ' # noqa
                       'follow this link, download the article, and attach it '
                       'to an email reply, we can deposit it on your behalf: '
                       '<a href="http://libproxy.mit.edu/login?url=https://dx.doi.org/$doi">http://libproxy.mit.edu/login?url=https://dx.doi.org/$doi</a>]</b>')  # noqa

        assert record.fpv_message == msg.substitute(
            publisher_name=publisher_name, doi=fake_doi)

    def test_get_or_create_from_data(self):
        author = Author.objects.get(pk=1)
        record, created = Record.get_or_create_from_data(
            author, {Fields.PAPER_ID: 1})
        assert record.pk == 1
        assert not created

        row = {
            Fields.PUBLISHER_NAME: 'publisher_name',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'citation',
            Fields.DOI: 'doi',
            Fields.PAPER_ID: 'paper_id',
        }

        record, created = Record.get_or_create_from_data(author, row)
        assert created
        assert record.publisher_name == 'publisher_name'
        assert record.acq_method == 'RECRUIT_FROM_AUTHOR_FPV'
        assert record.citation == 'citation'
        assert record.doi == 'doi'
        assert record.paper_id == 'paper_id'

    def test_get_duplicates_1(self):
        """There are no duplicates: this should return None."""

        metadata = {
            Fields.PUBLISHER_NAME: 'publisher_name',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'citation',
            Fields.DOI: 'doi',
            Fields.PAPER_ID: 'paper_id',
        }
        author = Author.objects.get(pk=1)

        assert Record.get_duplicates(author, metadata) is None

    def test_get_duplicates_2(self):
        """There's a paper with the same citation but a different author;
        this should return None."""

        metadata = {
            Fields.PUBLISHER_NAME: 'Wiley',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'Fermi, Enrico. Paper name. Some journal or other. 145:5 (2016)',  # noqa
            Fields.DOI: '10.1412/4678156',
            Fields.PAPER_ID: 'paper_id',
            Fields.FIRST_NAME: 'Different',
            Fields.LAST_NAME: 'Author',
            Fields.MIT_ID: 214614,
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

        assert Record.get_duplicates(author, metadata) is None

    def test_get_duplicates_3(self):
        """There's a paper with the same citation, the same author, and a
        different paper_id; this should return that duplicate."""
        # Check assumption
        assert not Record.objects.filter(paper_id=24618)

        # This is a duplicate of record #2, except for the paper ID.
        metadata = {
            Fields.PUBLISHER_NAME: 'Nature',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'Tonegawa, Susumu. Paper name. Some journal or other. 31:4 (2012)',  # noqa
            Fields.DOI: '10.1240.2/4914241',
            Fields.PAPER_ID: '24618',
            Fields.FIRST_NAME: 'Susumu',
            Fields.LAST_NAME: 'Tonegawa',
            Fields.MIT_ID: '2',
        }
        author = Author.objects.get(last_name='Tonegawa')

        dupes = Record.get_duplicates(author, metadata)
        assert dupes.count() == 1
        assert int(dupes[0].paper_id) == 123141

    def test_create_citation_case_1(self):
        """Minimal citation plus:
        publication date: YES
        volume & issue: NO
        doi: NO """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.VOLUME,
                                   Fields.ISSUE,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. (1973). Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_create_citation_case_2(self):
        """Minimal citation plus:
        publication date: YES
        volume & issue: YES
        doi: NO """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. (1973). Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters, 30(26).'  # noqa
        )

    def test_create_citation_case_3(self):
        """Minimal citation plus:
        publication date: YES
        volume & issue: NO
        doi: YES """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.VOLUME,
                                   Fields.ISSUE],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. (1973). Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters. doi:10.1103/PhysRevLett.30.1343'  # noqa
        )

    def test_create_citation_case_4(self):
        """Minimal citation plus:
        publication date: YES
        volume & issue: YES
        doi: YES """
        citation = Record.create_citation(self.citation_data)
        self.assertEqual(citation,
            'Wilczek, F. (1973). Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters, 30(26). doi:10.1103/PhysRevLett.30.1343'  # noqa
        )

    def test_create_citation_case_5(self):
        """Minimal citation plus:
        publication date: NO
        volume & issue: NO
        doi: NO """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.VOLUME,
                                   Fields.ISSUE,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_create_citation_case_6(self):
        """Minimal citation plus:
        publication date: NO
        volume & issue: YES
        doi: NO """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters, 30(26).'  # noqa
        )

    def test_create_citation_case_7(self):
        """Minimal citation plus:
        publication date: NO
        volume & issue: NO
        doi: YES """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.VOLUME,
                                   Fields.ISSUE],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters. doi:10.1103/PhysRevLett.30.1343'  # noqa
        )

    def test_create_citation_case_8(self):
        """Minimal citation plus:
        publication date: NO
        volume & issue: YES
        doi: YES """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters, 30(26). doi:10.1103/PhysRevLett.30.1343'  # noqa
        )

    def test_create_citation_error_case_1(self):
        """Minimal citation; has volume, lacks issue."""
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.ISSUE,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_create_citation_error_case_2(self):
        """Minimal citation; has issue, lacks volume."""
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.VOLUME,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_create_citation_error_case_3(self):
        """Minimal citation and pubdate, but pubdate is incorrectly formatted
        (too few characters)."""
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.VOLUME,
                                   Fields.ISSUE,
                                   Fields.DOI],
                    None))
        data[Fields.PUBDATE] = '12341'
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_create_citation_error_case_4(self):
        """Minimal citation and pubdate, but pubdate is incorrectly formatted
        (not all numbers)."""
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.VOLUME,
                                   Fields.ISSUE,
                                   Fields.DOI],
                    None))
        data[Fields.PUBDATE] = '1234m714'
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_update_if_needed_case_1(self):
        """update_if_needed alters the record when it sees a new author."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.CITATION] = r1.citation
        author = Author.objects.get(pk=2)  # not the author of r1
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.author == author

    def test_update_if_needed_case_2(self):
        """update_if_needed alters the record when it sees a new publisher."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        new_publisher = r1.publisher_name + 'new'
        metadata[Fields.PUBLISHER_NAME] = new_publisher
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.CITATION] = r1.citation
        author = r1.author
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.publisher_name == new_publisher

    def test_update_if_needed_case_3(self):
        """update_if_needed alters the record when it sees a new acquisition
        method."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.CITATION] = r1.citation
        author = r1.author
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.acq_method == 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'

    def test_update_if_needed_case_4(self):
        """update_if_needed alters the record when it sees a new DOI."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        new_doi = r1.doi + 'new'
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = new_doi
        metadata[Fields.CITATION] = r1.citation
        author = r1.author
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.doi == new_doi

    def test_update_if_needed_case_5(self):
        """update_if_needed alters the record when it sees a new citation
        that is not blank."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        new_citation = r1.citation + 'new'
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.CITATION] = new_citation
        author = r1.author
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.citation == new_citation

    def test_update_if_needed_case_6(self):
        """update_if_needed does NOT alter the record if nothing has
        changed."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.LAST_NAME] = 'Fermi'
        metadata[Fields.FIRST_NAME] = 'Enrico'
        metadata[Fields.PUBDATE] = '20160815'
        metadata[Fields.TITLE] = 'Paper name'
        metadata[Fields.JOURNAL] = 'Some journal or other'
        metadata[Fields.VOLUME] = '145'
        metadata[Fields.ISSUE] = '5'
        author = r1.author

        # Ensure that the citation will not have changed
        r1.citation = Record.create_citation(metadata)
        r1.save()
        metadata[Fields.CITATION] = r1.citation

        assert not r1.update_if_needed(author, metadata)

    def test_update_if_needed_case_7(self):
        """update_if_needed does alter the record if the citation is blank,
        but other data from which we would generate a citation leads to a
        different citation than the currently existing one."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.LAST_NAME] = 'Fermi'
        metadata[Fields.FIRST_NAME] = 'Enrico'
        metadata[Fields.PUBDATE] = '20160815'
        metadata[Fields.TITLE] = 'Paper name'
        metadata[Fields.JOURNAL] = 'Some journal or other'
        metadata[Fields.VOLUME] = '145'
        metadata[Fields.ISSUE] = '5'
        metadata[Fields.CITATION] = ''
        author = r1.author

        assert r1.citation != Record.create_citation(metadata)  # check assumption

        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.citation == Record.create_citation(metadata)
