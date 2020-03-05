# Tests that make sure that the import view correctly verifies the
# imported data and sets record properties accordingly.

import hashlib
from datetime import date

import pytest
from pytest_django.asserts import assertTemplateUsed

from django.forms.models import model_to_dict
from django.template.defaultfilters import escape
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from solenoid.emails.models import EmailMessage
from solenoid.people.models import Liaison
from ..models import Record
from ..views import UnsentList

IMPORT_URL = reverse('records:import')


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


# Import View Tests
def test_import_records_view_renders(client):
    with assertTemplateUsed('records/import.html'):
        client.get(IMPORT_URL)


@pytest.mark.django_db
def test_record_added_correctly(client, mock_elements, test_settings):
    assert 0 == Record.objects.all().count()
    client.post(IMPORT_URL, {'author_id': '98765'}, follow=True)
    record = Record.objects.latest('pk')
    hashed_id = hashlib.md5('saltyMITID'.encode('utf-8')).hexdigest()
    assert 'Person' == record.author.first_name
    assert 'Author' == record.author.last_name
    assert 'PERSONA@ORG.EDU' == record.author.email
    assert hashed_id == record.author.dspace_id
    assert 'Big Publisher' == record.publisher_name
    assert 'doi:123.45' == record.doi


@pytest.mark.django_db
def test_fun_characters_handled_correctly(client, mock_elements,
                                          test_settings):
    orig_count = Record.objects.count()
    client.post(IMPORT_URL, {'author_id': 'fun'}, follow=True)
    assert orig_count + 4 == Record.objects.count()

    diacritics = Record.objects.get(paper_id='diacritics')
    assert 'Newmån, Díânne Ç' in diacritics.citation

    emoji = Record.objects.get(paper_id='emoji')
    assert '❤️' in emoji.citation

    math = Record.objects.get(paper_id='math')
    assert '∫' in math.citation
    assert 'π' in math.citation
    assert 'ℵ' in math.citation
    # This test is keepin' it real.
    assert 'ℝ' in math.citation

    nonroman = Record.objects.get(paper_id='nonroman')
    assert '医父逃心需者決応術紙女特周保形四困' in nonroman.citation


@pytest.mark.django_db
def test_paper_id_respected_case_1(client, mock_elements, test_settings):
    """
    If we re-import an UNSENT record with a known ID, we should leave the
    existing record alone and not create a new one."""
    with pytest.raises(Record.DoesNotExist):
        Record.objects.get(paper_id='12345')

    client.post(IMPORT_URL, {'author_id': '98765'})
    orig_count = Record.objects.count()
    record = Record.objects.latest('pk')

    assert '12345' == record.paper_id  # check assumptions
    orig_record = model_to_dict(record)

    client.post(IMPORT_URL, {'author_id': '98765'})
    assert orig_count == Record.objects.count()
    assert orig_record == model_to_dict(Record.objects.get(paper_id='12345'))


@pytest.mark.django_db
def test_paper_id_respected_case_2(client, mock_elements, test_settings):
    """
    If we re-import an UNSENT record with a known ID and altered data, we
    should update the existing record and not create a new one."""
    with pytest.raises(Record.DoesNotExist):
        Record.objects.get(paper_id='12345')

    client.post(IMPORT_URL, {'author_id': '98765'})
    orig_count = Record.objects.count()
    record = Record.objects.latest('pk')

    assert '12345' == record.paper_id  # check assumptions
    orig_record = model_to_dict(record)
    orig_doi = orig_record.pop('doi')
    orig_record.pop('citation')

    client.post(IMPORT_URL, {'author_id': '98765-updated'})
    assert orig_count == Record.objects.count()
    new_record = model_to_dict(Record.objects.get(paper_id='12345'))
    new_doi = new_record.pop('doi')
    new_record.pop('citation')
    assert orig_record == new_record
    assert orig_doi != new_doi


@pytest.mark.django_db
def test_paper_id_respected_case_3(client, mock_elements, test_settings):
    """
    If we re-import an already sent record with a known ID & author, we
    should raise a warning and leave the existing record alone, not create
    a new one."""
    orig_count = Record.objects.count()

    with pytest.raises(Record.DoesNotExist):
        Record.objects.get(paper_id='12345')

    client.post(IMPORT_URL, {'author_id': '98765'})
    new_count = Record.objects.count()
    assert orig_count + 1 == new_count

    record = Record.objects.latest('pk')
    assert '12345' == record.paper_id

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

    response = client.post(IMPORT_URL, {'author_id': '98765'}, follow=True)
    assert new_count == Record.objects.count()
    assert orig_record == model_to_dict(Record.objects.get(paper_id='12345'))
    assert 'info' in [m.level_tag for m in response.context['messages']]


@pytest.mark.django_db
def test_paper_id_respected_case_4(client, mock_elements, test_settings):
    """
    If we re-import an already sent record with a known ID and a new
    author, we should raise a warning and not create a new record."""
    orig_count = Record.objects.count()
    with pytest.raises(Record.DoesNotExist):
        Record.objects.get(paper_id='12345')
    client.post(IMPORT_URL, {'author_id': '98765'})

    new_count = Record.objects.count()
    assert orig_count + 1 == new_count

    record = Record.objects.latest('pk')
    assert '12345' == record.paper_id

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

    # Next, import new data about the same paper as recorded under a different
    # author. This should *not* create any new records.
    response = client.post(IMPORT_URL, {'author_id': '54321'}, follow=True)
    assert new_count == Record.objects.count()
    assert orig_record == model_to_dict(Record.objects.get(paper_id='12345'))
    assert 'info' in [m.level_tag for m in response.context['messages']]


# TODO: check with stakeholders to find out if any of the below concerns are
# still relevant in this new API-based import process. If so, rewrite these
# tests accordingly.


#     def test_records_without_publishers_accepted_if_not_fpv(self):
#         orig_count = Record.objects.count()
#
#         self._post_csv('missing_publisher_name_non_fpv.csv')
#
#         self.assertEqual(orig_count + 1, Record.objects.count())


#     def test_records_without_publishers_rejected_if_fpv(self):
#         orig_count = Record.objects.count()
#
#         self._post_csv('missing_publisher_name_fpv.csv')
#
#         self.assertEqual(orig_count, Record.objects.count())


#     def test_acq_method_set_when_present(self):
#         self._post_csv('single_good_record.csv')
#
#         record = Record.objects.latest('pk')
#         self.assertEqual(record.acq_method, 'RECRUIT_FROM_AUTHOR_MANUSCRIPT')


#     def test_records_with_unknown_acq_method_rejected(self):
#         orig_count = Record.objects.count()
#
#         self._post_csv('bad_acq_method.csv')
#
#         self.assertEqual(orig_count, Record.objects.count())


#     def test_records_with_new_acq_methods_accepted(self):
#         orig_count = Record.objects.count()
#
#         self._post_csv('new_acq_methods2.csv')
#
#         self.assertEqual(orig_count + 2, Record.objects.count())


#     def test_citation_set_when_present(self):
#         self._post_csv('single_good_record.csv')
#
#         record = Record.objects.latest('pk')
#         self.assertEqual(record.citation, 'Ramos, Itzel, et al. "Phenazines Affect Biofilm Formation by Pseudomonas Aeruginosa in Similar Ways at Various Scales." Research in Microbiology 161 3 (2010): 187-91.')  # noqa


#     def test_fpv_records_without_doi_rejected(self):
#         orig_count = Record.objects.count()
#
#         self._post_csv('missing_doi_fpv.csv')
#
#         self.assertEqual(orig_count, Record.objects.count())


#     def test_manuscript_records_without_doi_accepted(self):
#         orig_count = Record.objects.count()
#
#         self._post_csv('missing_doi_manuscript.csv')
#
#         self.assertEqual(orig_count + 1, Record.objects.count())
#         record = Record.objects.latest('pk')
#         self.assertEqual(record.doi, '')
#         self.assertEqual(record.acq_method, 'RECRUIT_FROM_AUTHOR_MANUSCRIPT')


#     def test_special_message_added(self):
#         # Case 1: the special message field is blank.
#         self._post_csv('single_good_record.csv')
#
#         record = Record.objects.latest('pk')
#         self.assertFalse(record.message)
#
#         # Case 2: the special message field is not blank.
#         # Note that this record has a different paper ID and author than the
#         # first one - that's important, as it means we're creating a new record
#         # rather than accessing the existing one, which may not have a message,
#         # depending on how we ultimately handle citation updates. (Changing
#         # PaperID alone isn't enough, since the system would recognize that the
#         # records have the same author and citation, and reject the second as
#         # a duplicate.)
#         self._post_csv('single_good_record_with_message.csv')
#
#         record2 = Record.objects.latest('pk')
#         self.assertEqual(record2.message.text, 'special message goes here')
#
#         # Case 3: the special message field is not blank, *and* it's one we've
#         # seen before.
#         # Note that this CSV is the same as single_good_record_with_message,
#         # except for a different paper ID and author.
#         self._post_csv('single_good_record_with_message_2.csv')
#
#         record3 = Record.objects.latest('pk')
#         self.assertEqual(record3.message.text, 'special message goes here')
#         self.assertEqual(record2.message, record3.message)
