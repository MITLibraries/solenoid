import os

from freezegun import freeze_time
import pytest
import requests_mock

from django.conf import settings
from django.utils import timezone

TEST_AUTHOR_ID = '98765'

PAGE_ONE = ("<xml page='1'><object><url position='next' "
            "href='mock://api.com/page2'></url></object></xml>")

PAGE_TWO = ("<xml page='2'><object><url position='this' "
            "href='mock://api.com/page2'></url></object></xml>")


@pytest.fixture()
def author_xml():
    return _get_file('author.xml')


@pytest.fixture()
def author_pubs_xml():
    return _get_file('author-pubs-feed.xml')


@pytest.fixture()
def publication_xml():
    return _get_file('publication.xml')


@pytest.fixture()
def mock_elements():
    with requests_mock.Mocker() as m:
        m.get('mock://api.com', text='Success')
        m.get('mock://api.com/400', status_code=400)
        m.get('http://api.com/409', status_code=409)
        m.get('mock://api.com/500', status_code=500)
        m.get('mock://api.com/504', status_code=504)
        m.get(f'mock://api.com/users/{TEST_AUTHOR_ID}', text=author_xml)
        m.get(f'mock://api.com/users/{TEST_AUTHOR_ID}/'
              f'publications?&detail=full', text=author_pubs_xml)
        m.get('mock://api.com/page1', text=PAGE_ONE)
        m.get('mock://api.com/page2', text=PAGE_TWO)
        m.patch('mock://api.com', text='Success')
        m.patch('mock://api.com/400', status_code=400)
        m.patch('mock://api.com/409', status_code=409)
        m.patch('mock://api.com/500', status_code=500)
        m.patch('mock://api.com/504', status_code=504)

        yield m


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


def _get_file(filename):
    file = os.path.join(settings.FIXTURE_DIRS[0], filename)
    if os.path.isfile(file):
        with open(file, 'r') as f:
            return f.read()
