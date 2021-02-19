import hashlib
from datetime import date

import pytest

from django.forms.models import model_to_dict
from django.urls import reverse

from solenoid.emails.models import EmailMessage
from solenoid.people.models import Author, DLC, Liaison
from ..helpers import Fields
from ..models import Record
from ..tasks import task_import_papers_for_author

IMPORT_URL = reverse('records:import')
AUTHOR_URL = 'mock://api.com/users/98765'
AUTHOR_DATA = {
    'Email': 'PERSONA@ORG.EDU',
    'First Name': 'Person',
    'Last Name': 'Author',
    'MIT ID': 'MITID',
    'DLC': 'Department Faculty',
    'Start Date': '2011-01-01',
    'End Date': '2020-06-30',
    'ELEMENTS ID': '98765'
    }


@pytest.mark.django_db(transaction=True)
def test_import_papers_for_author_success(mock_elements, test_settings):
    assert 0 == Record.objects.all().count()

    dlc, _ = DLC.objects.get_or_create(name=AUTHOR_DATA[Fields.DLC])
    author = Author.objects.create(
        first_name=AUTHOR_DATA[Fields.FIRST_NAME],
        last_name=AUTHOR_DATA[Fields.LAST_NAME],
        dlc=dlc,
        email=AUTHOR_DATA[Fields.EMAIL],
        mit_id=AUTHOR_DATA[Fields.MIT_ID],
        dspace_id=AUTHOR_DATA[Fields.MIT_ID]
        )

    task_import_papers_for_author(AUTHOR_URL, AUTHOR_DATA, author.pk)

    record = Record.objects.latest('pk')
    hashed_id = hashlib.md5('saltyMITID'.encode('utf-8')).hexdigest()
    assert 'Person' == record.author.first_name
    assert 'Author' == record.author.last_name
    assert 'PERSONA@ORG.EDU' == record.author.email
    assert hashed_id == record.author.dspace_id
    assert 'Big Publisher' == record.publisher_name
    assert 'doi:123.45' == record.doi


@pytest.mark.django_db(transaction=True)
def test_fun_characters_handled_correctly(mock_elements, test_settings):
    orig_count = Record.objects.count()

    fun_author_url = 'mock://api.com/users/fun'
    fun_author_data = {
        'Email': 'PERSONA@ORG.EDU',
        'First Name': 'Person',
        'Last Name': 'Author',
        'MIT ID': 'MITID',
        'DLC': 'Department Faculty',
        'Start Date': '2011-01-01',
        'End Date': '2020-06-30',
        'ELEMENTS ID': 'fun'
        }
    dlc, _ = DLC.objects.get_or_create(name=fun_author_data[Fields.DLC])
    author = Author.objects.create(
        first_name=fun_author_data[Fields.FIRST_NAME],
        last_name=fun_author_data[Fields.LAST_NAME],
        dlc=dlc,
        email=fun_author_data[Fields.EMAIL],
        mit_id=fun_author_data[Fields.MIT_ID],
        dspace_id=fun_author_data[Fields.MIT_ID]
        )

    task_import_papers_for_author(fun_author_url, fun_author_data, author.pk)

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


@pytest.mark.django_db(transaction=True)
def test_paper_id_respected_case_1(mock_elements, test_settings):
    """
    If we re-import an UNSENT record with a known ID, we should leave the
    existing record alone and not create a new one."""
    with pytest.raises(Record.DoesNotExist):
        Record.objects.get(paper_id='12345')

    dlc, _ = DLC.objects.get_or_create(name=AUTHOR_DATA[Fields.DLC])
    author = Author.objects.create(
        first_name=AUTHOR_DATA[Fields.FIRST_NAME],
        last_name=AUTHOR_DATA[Fields.LAST_NAME],
        dlc=dlc,
        email=AUTHOR_DATA[Fields.EMAIL],
        mit_id=AUTHOR_DATA[Fields.MIT_ID],
        dspace_id=AUTHOR_DATA[Fields.MIT_ID]
        )

    task_import_papers_for_author(AUTHOR_URL, AUTHOR_DATA, author.pk)

    orig_count = Record.objects.count()
    record = Record.objects.latest('pk')
    assert '12345' == record.paper_id  # check assumptions
    orig_record = model_to_dict(record)

    t = task_import_papers_for_author(AUTHOR_URL, AUTHOR_DATA, author.pk)

    assert orig_count == Record.objects.count()
    assert orig_record == model_to_dict(Record.objects.get(paper_id='12345'))
    assert 'Paper already in database, no updates made.' == t['2']


@pytest.mark.django_db(transaction=True)
def test_paper_id_respected_case_2(mock_elements, test_settings):
    """
    If we re-import an UNSENT record with a known ID and altered data, we
    should update the existing record and not create a new one."""
    with pytest.raises(Record.DoesNotExist):
        Record.objects.get(paper_id='12345')

    dlc, _ = DLC.objects.get_or_create(name=AUTHOR_DATA[Fields.DLC])
    author = Author.objects.create(
        first_name=AUTHOR_DATA[Fields.FIRST_NAME],
        last_name=AUTHOR_DATA[Fields.LAST_NAME],
        dlc=dlc,
        email=AUTHOR_DATA[Fields.EMAIL],
        mit_id=AUTHOR_DATA[Fields.MIT_ID],
        dspace_id=AUTHOR_DATA[Fields.MIT_ID]
        )

    task_import_papers_for_author('mock://api.com/users/98765-updated',
                                  AUTHOR_DATA, author.pk)

    orig_count = Record.objects.count()
    record = Record.objects.latest('pk')

    assert '12345' == record.paper_id  # check assumptions
    orig_record = model_to_dict(record)
    orig_doi = orig_record.pop('doi')
    orig_record.pop('citation')

    t = task_import_papers_for_author(AUTHOR_URL, AUTHOR_DATA, author.pk)

    assert orig_count == Record.objects.count()
    new_record = model_to_dict(Record.objects.get(paper_id='12345'))
    new_doi = new_record.pop('doi')
    new_record.pop('citation')
    assert orig_record == new_record
    assert orig_doi != new_doi

    assert 'Record updated with new data from Elements.' == t['2']


@pytest.mark.django_db(transaction=True)
def test_paper_id_respected_case_3(mock_elements, test_settings):
    """
    If we re-import an already sent record with a known ID & author, we
    should raise a warning and leave the existing record alone, not create
    a new one."""
    orig_count = Record.objects.count()

    with pytest.raises(Record.DoesNotExist):
        Record.objects.get(paper_id='12345')

    dlc, _ = DLC.objects.get_or_create(name=AUTHOR_DATA[Fields.DLC])
    author = Author.objects.create(
        first_name=AUTHOR_DATA[Fields.FIRST_NAME],
        last_name=AUTHOR_DATA[Fields.LAST_NAME],
        dlc=dlc,
        email=AUTHOR_DATA[Fields.EMAIL],
        mit_id=AUTHOR_DATA[Fields.MIT_ID],
        dspace_id=AUTHOR_DATA[Fields.MIT_ID]
        )

    task_import_papers_for_author(AUTHOR_URL, AUTHOR_DATA, author.pk)

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

    t = task_import_papers_for_author(AUTHOR_URL, AUTHOR_DATA, author.pk)

    assert new_count == Record.objects.count()
    assert orig_record == model_to_dict(Record.objects.get(paper_id='12345'))
    assert 'Publication #12345 by Author has already been requested' in t['2']


@pytest.mark.django_db(transaction=True)
def test_paper_id_respected_case_4(mock_elements, test_settings):
    """
    If we re-import an already sent record with a known ID and a new
    author, we should raise a warning and not create a new record."""
    orig_count = Record.objects.count()
    with pytest.raises(Record.DoesNotExist):
        Record.objects.get(paper_id='12345')

    dlc, _ = DLC.objects.get_or_create(name=AUTHOR_DATA[Fields.DLC])
    author = Author.objects.create(
        first_name=AUTHOR_DATA[Fields.FIRST_NAME],
        last_name=AUTHOR_DATA[Fields.LAST_NAME],
        dlc=dlc,
        email=AUTHOR_DATA[Fields.EMAIL],
        mit_id=AUTHOR_DATA[Fields.MIT_ID],
        dspace_id=AUTHOR_DATA[Fields.MIT_ID]
        )

    task_import_papers_for_author(AUTHOR_URL, AUTHOR_DATA, author.pk)

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
    new_author_url = 'mock://api.com/users/54321'
    new_author_data = {
        'Email': 'PTWONA@ORG.EDU',
        'First Name': 'Person Two',
        'Last Name': 'New Author',
        'MIT ID': 'MITID02',
        'DLC': 'Department Faculty',
        'Start Date': '2011-01-01',
        'End Date': '3000-01-01',
        'ELEMENTS ID': '54321'
        }
    new_author = Author.objects.create(
        first_name=new_author_data[Fields.FIRST_NAME],
        last_name=new_author_data[Fields.LAST_NAME],
        dlc=dlc,
        email=new_author_data[Fields.EMAIL],
        mit_id=new_author_data[Fields.MIT_ID],
        dspace_id=new_author_data[Fields.MIT_ID]
        )

    t = task_import_papers_for_author(new_author_url, new_author_data,
                                      new_author.pk)

    assert new_count == Record.objects.count()
    assert orig_record == model_to_dict(Record.objects.get(paper_id='12345'))
    assert 'Publication #12345 by New Author has already been requested' in t['2']


@pytest.mark.django_db(transaction=True)
def test_acq_method_set_when_present(mock_elements, test_settings):
    dlc, _ = DLC.objects.get_or_create(name=AUTHOR_DATA[Fields.DLC])
    author = Author.objects.create(
        first_name=AUTHOR_DATA[Fields.FIRST_NAME],
        last_name=AUTHOR_DATA[Fields.LAST_NAME],
        dlc=dlc,
        email=AUTHOR_DATA[Fields.EMAIL],
        mit_id=AUTHOR_DATA[Fields.MIT_ID],
        dspace_id=AUTHOR_DATA[Fields.MIT_ID]
        )

    task_import_papers_for_author(AUTHOR_URL, AUTHOR_DATA, author.pk)

    record = Record.objects.latest('pk')
    assert record.acq_method == 'RECRUIT_FROM_AUTHOR_FPV'
