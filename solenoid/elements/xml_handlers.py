import logging
import xml.etree.ElementTree as ET

from django.utils import timezone

logger = logging.getLogger(__name__)

NS = {'atom': 'http://www.w3.org/2005/Atom',
      'api': 'http://www.symplectic.co.uk/publications/api'}


def extract_field(root, search_string):
    try:
        field = root.find(search_string, NS).text
    except AttributeError:
        field = ''
    return field


def make_xml(username):
    top = ET.Element('update-object')
    top.set('xmlns', 'http://www.symplectic.co.uk/publications/api')
    oa_field = ET.SubElement(top, 'oa')

    # Update library status field
    status_field = ET.SubElement(oa_field, 'library-status')
    status_field.set('status', 'full-text-requested')
    date_field = ET.SubElement(status_field, 'last-requested-when')
    date_field.text = timezone.now().isoformat()
    note_field = ET.SubElement(status_field, 'note-field')
    note_field.set('clear-existing-note', 'true')
    note = ET.SubElement(note_field, 'note')
    note.text = "Library status changed to Full text requested on " \
        "{date} by {username}.".format(
            date=timezone.now().strftime('%-d %B %Y'),
            username=username)

    return top


def parse_author_pubs_xml(xml_gen):
    '''Takes a an author-publications record feed from Symplectic
    Elements, parses each record according to local rules for which
    publications should be requested based on certain metadata fields, and
    returns a list of publication IDs that should be imported into Solenoid and
    requested from the author.
    '''
    RESULTS = []
    for page in xml_gen:
        root = ET.fromstring(page)
        for entry in root.findall("./atom:entry", NS):
            pub_id = entry.find(".//api:object[@category='publication']",
                                NS).get('id')
            title = entry.find(".//api:field[@name='title']/api:text", NS).text
            if entry.find(".//api:record[@source-name='manual']", NS):
                if (entry.find(".//api:field[@name='c-do-not-request']"
                               "/api:boolean",
                               NS).text == 'true' or
                    entry.find(".//api:field[@name='c-optout']/api:boolean",
                               NS).text == 'true' or
                    entry.find(".//api:field[@name='c-received']/api:boolean",
                               NS).text == 'true' or
                    entry.find(".//api:field[@name='c-requested']/api:boolean",
                               NS).text == 'true'):
                    continue
            if entry.find(".//api:library-status", NS):
                continue
            if int(entry.find(".//api:field[@name='publication-date']"
                              "//api:year", NS).text) < 2009:
                continue
            else:
                RESULTS.append({'id': pub_id,
                                'title': title})
    return RESULTS


def parse_author_xml(author_xml):
    root = ET.fromstring(author_xml)
    AUTHOR_DATA = {
        'Email': extract_field(root, ".//api:email-address"),
        'First Name': extract_field(root, ".//api:first-name"),
        'Last Name': extract_field(root, ".//api:last-name"),
        'MIT ID': root.find(".//api:object",
                            NS).get('proprietary-id'),
        'DLC': extract_field(root, ".//api:primary-group-descriptor")
    }
    return AUTHOR_DATA


def parse_paper_xml(paper_xml):
    root = ET.fromstring(paper_xml)
    PAPER_DATA = {
        'Doi': extract_field(root, ".//api:field[@name='doi']/api:text"),
        'Citation': extract_field(root, ".//api:field[@name='c-citation']"
                                  "/api:text"),
        'Publisher-name': extract_field(root, ".//api:field[@name='publisher']"
                                        "/api:text"),
        'C-Method-Of-Acquisition': extract_field(root, ".//api:field[@name="
                                                 "'c-method-of-acquisition']"
                                                 "/api:text"),
        'PaperID': root.find(".//api:object", NS).get('id'),
        'C-Publisher-Related-Email-Message': extract_field(root,
                                                           ".//api:field["
                                                           "@name='c-publisher"
                                                           "-related-email-"
                                                           "message']/"
                                                           "api:text"),
        'Year Published': extract_field(root, ".//api:field[@name='publication"
                                        "-date']/api:date/api:year"),
        'Title1': extract_field(root, 'atom:title'),
        'Journal-name': extract_field(root, ".//api:field[@name='journal']/"
                                      "api:text"),
        'Volume': extract_field(root, ".//api:field[@name='volume']/api:text"),
        'Issue': extract_field(root, ".//api:field[@name='issue']/api:text")
    }
    return PAPER_DATA
