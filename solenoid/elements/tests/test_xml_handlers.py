import datetime
import xml.etree.ElementTree as ET

from freezegun import freeze_time

from solenoid.elements.xml_handlers import (extract_attribute, extract_field,
                                            get_pub_date, make_xml,
                                            parse_author_pubs_xml,
                                            parse_author_xml,
                                            parse_journal_policies,
                                            parse_paper_xml)


def test_extract_attribute_exists(publication_xml):
    pub_root = ET.fromstring(publication_xml)
    value = extract_attribute(pub_root, './/api:object', 'id')
    assert value == '12345'


def test_extract_attribute_does_not_exist(publication_xml):
    pub_root = ET.fromstring(publication_xml)
    value = extract_attribute(pub_root, './/api:object', 'notanattribute')
    assert value == ''


def test_extract_field_exists(publication_xml):
    pub_root = ET.fromstring(publication_xml)
    field = extract_field(pub_root, 'atom:title')
    assert field == 'I am the Title of a Publication'


def test_extract_field_not_exists(publication_xml):
    pub_root = ET.fromstring(publication_xml)
    field = extract_field(pub_root, 'notafield')
    assert field == ''


def test_get_pub_date(publication_xml):
    pub_root = ET.fromstring(publication_xml)
    date = get_pub_date(pub_root)
    assert date == datetime.date(2017, 2, 1)


def test_get_pub_date_no_date(publication_no_date_xml):
    pub_root = ET.fromstring(publication_no_date_xml)
    date = get_pub_date(pub_root)
    assert date is None


def test_parse_journal_policies(journal_policies_xml):
    policy_data = parse_journal_policies(journal_policies_xml)
    assert policy_data == {
        'C-Method-Of-Acquisition': 'RECRUIT_FROM_AUTHOR_FPV',
        'C-Publisher-Related-Email-Message': ('Big Publisher allows authors '
                                              'to download and deposit the '
                                              'final published article, but '
                                              'does not allow the Libraries '
                                              'to perform the downloading. '
                                              'If you attach the final '
                                              'published version to an email '
                                              'reply, we can deposit it on '
                                              'your behalf. (See http://big-'
                                              'publisher-info-url.com)')
        }


@freeze_time('20190101')
def test_make_xml(patch_xml):
    xml = make_xml('username')
    assert patch_xml == ET.tostring(xml, encoding='unicode')


def test_parse_author_pubs_xml(author_pubs_xml):
    author_data = {
        'Start Date': datetime.date(2011, 10, 1),
        'End Date': datetime.date(2020, 6, 30)
    }
    pubs = parse_author_pubs_xml([author_pubs_xml], author_data)
    assert pubs == [{'id': '2', 'title': 'Publication Two'},
                    {'id': '6', 'title': 'Publication Six'},
                    {'id': '9', 'title': 'Publication Nine'}]


def test_parse_author_xml(author_xml):
    author_data = parse_author_xml(author_xml)
    assert author_data == {
        'Email': 'PERSONA@ORG.EDU',
        'First Name': 'Person',
        'Last Name': 'Author',
        'MIT ID': 'MITID',
        'DLC': 'Department Faculty',
        'Start Date': datetime.date(2011, 10, 1),
        'End Date': datetime.date(2020, 6, 30)
    }


def test_parse_author_xml_no_end_date(author_new_xml):
    author_data = parse_author_xml(author_new_xml)
    assert author_data == {
        'Email': 'PTWONA@ORG.EDU',
        'First Name': 'Person Two',
        'Last Name': 'New Author',
        'MIT ID': 'MITID02',
        'DLC': 'Department Faculty',
        'Start Date': datetime.date(2011, 10, 1),
        'End Date': datetime.date(3000, 1, 1)
    }


def test_parse_paper_xml(publication_xml):
    pub_data = parse_paper_xml(publication_xml)
    assert pub_data == {
        'Doi': 'doi:123.45',
        'Citation': '',
        'Publisher-name': 'Big Publisher',
        'C-Method-Of-Acquisition': '',
        'PaperID': '12345',
        'C-Publisher-Related-Email-Message': '',
        'Year Published': '2017',
        'Title1': 'I am the Title of a Publication',
        'Journal-name': 'A Very Important Journal',
        'Journal-elements-url': 'mock://api.com/journals/0000',
        'Volume': '95',
        'Issue': ''
    }
