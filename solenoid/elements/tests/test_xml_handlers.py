import xml.etree.ElementTree as ET

from freezegun import freeze_time

from solenoid.elements.xml_handlers import (extract_field, make_xml,
                                            parse_author_pubs_xml,
                                            parse_author_xml, parse_paper_xml)

USERNAME = 'username'


def test_extract_field_exists(publication_xml):
    pub_root = ET.fromstring(publication_xml)
    field = extract_field(pub_root, 'atom:title')
    assert field == 'I am the Title of a Publication'


def test_extract_field_not_exists(publication_xml):
    pub_root = ET.fromstring(publication_xml)
    field = extract_field(pub_root, 'notafield')
    assert field == ''


@freeze_time('20190101')
def test_make_xml(patch_xml):
    xml = make_xml('username')
    assert patch_xml == ET.tostring(xml, encoding='unicode')


def test_parse_author_pubs_xml(author_pubs_xml):
    pubs = parse_author_pubs_xml([author_pubs_xml])
    assert pubs == [{'id': '2',
                    'title': 'Publication Two'}]


def test_parse_author_xml(author_xml):
    author_data = parse_author_xml(author_xml)
    assert author_data == {
        'Email': 'PERSONA@ORG.EDU',
        'First Name': 'Person',
        'Last Name': 'Author',
        'MIT ID': 'MITID',
        'DLC': 'Department Faculty'
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
        'Volume': '95',
        'Issue': ''
    }