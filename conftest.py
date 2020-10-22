import os

from freezegun import freeze_time
import pytest
from requests.exceptions import Timeout
import requests_mock

from django.conf import settings
from django.utils import timezone

PAGE_ONE = ("<xml page='1'><object><url position='next' "
            "href='mock://api.com/page2'></url></object></xml>")

PAGE_TWO = ("<xml page='2'><object><url position='this' "
            "href='mock://api.com/page2'></url></object></xml>")


@pytest.fixture()
def author_xml():
    return _get_file('author.xml')


@pytest.fixture()
def author_new_xml():
    return _get_file('author-new.xml')


@pytest.fixture()
def author_pubs_xml():
    return _get_file('author-pubs-feed.xml')


@pytest.fixture()
def author_pubs_new_xml():
    return _get_file('author-pubs-feed-new.xml')


@pytest.fixture()
def author_pubs_updated_xml():
    return _get_file('author-pubs-feed-updated.xml')


@pytest.fixture()
def publication_xml():
    return _get_file('publication.xml')


@pytest.fixture()
def publication_new_xml():
    return _get_file('publication-new.xml')


@pytest.fixture()
def publication_no_date_xml():
    return _get_file('publication-no-date.xml')


@pytest.fixture()
def journal_policies_xml():
    return _get_file('journal-policies.xml')


@pytest.fixture()
def publication_updated_xml():
    return _get_file('publication-updated.xml')


@pytest.fixture()
def fun_author_xml():
    return _get_file('fun-author.xml')


@pytest.fixture()
def fun_author_pubs_xml():
    return _get_file('fun-author-pubs-feed.xml')


@pytest.fixture()
def fun_publication_diacritics_xml():
    return _get_file('fun-publication-diacritics.xml')


@pytest.fixture()
def fun_publication_emoji_xml():
    return _get_file('fun-publication-emoji.xml')


@pytest.fixture()
def fun_publication_math_xml():
    return _get_file('fun-publication-math.xml')


@pytest.fixture()
def fun_publication_nonroman_xml():
    return _get_file('fun-publication-nonroman.xml')


@pytest.fixture()
def mock_elements(author_xml, author_new_xml, author_pubs_xml,
                  author_pubs_new_xml, author_pubs_updated_xml, fun_author_xml,
                  fun_author_pubs_xml, fun_publication_diacritics_xml,
                  fun_publication_emoji_xml, fun_publication_math_xml,
                  fun_publication_nonroman_xml, journal_policies_xml,
                  publication_xml, publication_new_xml,
                  publication_no_date_xml,
                  publication_updated_xml):
    with requests_mock.Mocker() as m:
        m.get('mock://api.com', text='Success')
        m.get('mock://api.com/400', status_code=400)
        m.get('mock://api.com/409', status_code=409)
        m.get('mock://api.com/500', status_code=500)
        m.get('mock://api.com/504', status_code=504)
        m.get('mock://api.com/timeout',
              exc=Timeout)
        m.get('mock://api.com/page1', text=PAGE_ONE)
        m.get('mock://api.com/page2', text=PAGE_TWO)

        m.get(f'mock://api.com/users/98765', text=author_xml)
        m.get(f'mock://api.com/users/98765-updated', text=author_xml)
        m.get(f'mock://api.com/users/54321', text=author_new_xml)
        m.get(f'mock://api.com/users/98765/'
              f'publications?&detail=full', text=author_pubs_xml)
        m.get(f'mock://api.com/users/98765-updated/'
              f'publications?&detail=full', text=author_pubs_updated_xml)
        m.get(f'mock://api.com/users/54321/'
              f'publications?&detail=full', text=author_pubs_new_xml)
        m.get(f'mock://api.com/publications/2', text=publication_xml)
        m.get(f'mock://api.com/journals/0000/policies?detail=full',
              text=journal_policies_xml)
        m.get(f'mock://api.com/publications/2-updated',
              text=publication_updated_xml)
        m.get(f'mock://api.com/publications/6', text=publication_no_date_xml)
        m.get(f'mock://api.com/publications/9', text=publication_xml)

        m.get(f'mock://api.com/users/fun', text=fun_author_xml)
        m.get(f'mock://api.com/users/fun/'
              f'publications?&detail=full', text=fun_author_pubs_xml)
        m.get(f'mock://api.com/publications/diacritics',
              text=fun_publication_diacritics_xml)
        m.get(f'mock://api.com/publications/emoji',
              text=fun_publication_emoji_xml)
        m.get(f'mock://api.com/publications/math',
              text=fun_publication_math_xml)
        m.get(f'mock://api.com/publications/nonroman',
              text=fun_publication_nonroman_xml)

        m.patch('mock://api.com', text='Success')
        m.patch('mock://api.com/400', status_code=400)
        m.patch('mock://api.com/409', status_code=409)
        m.patch('mock://api.com/500', status_code=500)
        m.patch('mock://api.com/504', status_code=504)
        m.patch('mock://api.com/timeout', exc=Timeout)

        yield m


@pytest.fixture(params=['409', '500', '504'])
def error(request):
    return f'mock://api.com/{request.param}'


@pytest.fixture()
def patch_xml():
    with freeze_time('2019-01-01'):
        good_xml = (f'<update-object xmlns="http://www.symplectic.co.uk/'
                    f'publications/api"><oa><library-status status="full-'
                    f'text-requested"><last-requested-when>'
                    f'{timezone.now().isoformat()}</last-requested-when>'
                    f'<note-field clear-existing-note="true"><note>'
                    f'Library status changed to Full text requested on '
                    f'{timezone.now().strftime("%-d %B %Y")} '
                    f'by username.</note></note-field></library-status>'
                    f'</oa></update-object>')
    return good_xml


@pytest.fixture()
def test_settings():
    settings.DSPACE_SALT = 'salty'
    settings.EMAIL_TESTING_MODE = True
    settings.ELEMENTS_ENDPOINT = 'mock://api.com/'
    settings.ELEMENTS_USER = 'test_user'
    settings.ELEMENTS_PASSWORD = 'test_password'
    settings.LOGIN_REQUIRED = False
    settings.USE_ELEMENTS = False

    return settings


def _get_file(filename):
    file = os.path.join(settings.FIXTURE_DIRS[0], filename)
    if os.path.isfile(file):
        with open(file, 'r') as f:
            return f.read()
