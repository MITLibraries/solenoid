import datetime as dt
import logging
import xml.etree.ElementTree as ET

from typing import Generator

from django.utils import timezone

logger = logging.getLogger(__name__)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "api": "http://www.symplectic.co.uk/publications/api",
}
OA_POLICY_ENACTED_DATE = dt.date(2009, 3, 18)


def extract_attribute(root: ET.Element, search_string: str, attribute: str) -> str:
    element = root.find(search_string, NS)
    if element is not None:
        return element.get(attribute, "")
    else:
        return ""


def extract_field(root: ET.Element, search_string: str) -> str | None:
    element = root.find(search_string, NS)
    if element is None:
        return ""
    if field := element.text:
        return field
    return ""


def get_pub_date(root: ET.Element) -> dt.date | None:
    year_value = extract_field(root, ".//api:field[@name='publication-date']//api:year")
    if year_value:
        try:
            year = int(year_value)
        except ValueError:
            return None
    else:
        return None

    month_value = extract_field(root, ".//api:field[@name='publication-date']//api:month")
    if month_value:
        try:
            month = int(month_value)
        except ValueError:
            month = 1
    else:
        month = 1

    day_value = extract_field(root, ".//api:field[@name='publication-date']//api:day")
    if day_value:
        try:
            day = int(day_value)
        except ValueError:
            day = 1
    else:
        day = 1

    try:
        pub_date = dt.date(year, month, day)
    except ValueError:
        pub_date = dt.date(year, 1, 1)
    return pub_date


def pub_date_is_valid(element: ET.Element, author_data: dict) -> bool:
    """Determine whether an article's publication date is valid for inclusion in request.

    An article's publication date is considered valid for inclusion and the function will
    proceed with other checks if it meets ANY (at least one) of the following criteria:

        1. publication date is unknown (None);
        2. publication date is *after* the date the OA policy was in effect AND
            *during* the author's period of employment with MIT.

    An article's publication date is considered invalid and will be excluded from the
    request if it meets ALL of the following criteria:

        1. publication date is known;
        2. publication date is before (<=) the date the OA policy was in effect;
        3. publication date is outside of author's employment with MIT

    Args:
        element (ET.Element): Element representing an article.
        author_data (dict): Data about the author's start and end dates of MIT employment.

    Returns:
        bool: Flag indicating whether date is valid (True) or invalid (False).
    """
    pub_date = get_pub_date(element)

    if pub_date is None:
        return True
    else:
        author_start_date = dt.date.fromisoformat(author_data["Start Date"])
        author_end_date = dt.date.fromisoformat(author_data["End Date"])
        if pub_date <= OA_POLICY_ENACTED_DATE:
            return False
        elif pub_date < author_start_date or pub_date > author_end_date:
            return False
        else:
            return True


def pub_has_library_status(element: ET.Element) -> bool:
    """Determine if an article is included in a request based on library status.

    An article will not be included in a request if it has a 'library status'.

    Args:
        element (ET.Element): Element representing an article.

    Returns:
        bool: Flag indicating the presence of a library status; present (True)
            or absent (False).
    """
    if element.find(".//api:library-status", NS) is not None:
        return True
    return False


def pub_is_oa_exempt(element: ET.Element) -> bool:
    """Determine if an article is exempt from inclusion in request via OA exceptions.

    An article *is* exempt from inclusion if ALL of the following criteria are met:

        1. At least one (1) OA policy exception, excluding "Waiver",
            applies to the article.

    An article *is not* exempt from inclusion if ANY of the following criteria are met:
        1. Zero (0) OA policy exceptions apply to the article.
        2. If any OA policy exceptions apply to the article, "Waiver" is included.

    Args:
        element (ET.Element): Element representing an article.

    Returns:
        bool: Flag indicating whether article is exempt from OA policy
            (i.e., excluded from request).
    """
    if element.find(".//api:oa-policy-exception", NS) is not None:
        exceptions = [
            e.text for e in element.findall(".//api:oa-policy-exception/api:type", NS)
        ]
        if "Waiver" in exceptions:
            return False
        return True
    return False


def pub_is_on_dspace(element: ET.Element) -> bool:
    # # If paper has a dspace record in Elements, status is not 'Public'
    # # or 'Private' (in either case it has been deposited and should not
    # # be requested)
    if dspace_record := element.find(".//api:record[@source-name='dspace']", NS):
        status = extract_field(
            dspace_record, ".//api:field[@name='repository-status']/api:text"
        )
        if status in ["Public", "Private"]:
            return True
    return False


def pub_manual_entry_is_valid(element: ET.Element) -> bool:
    """Determine if a manual entry (via Symplectic Elements) for an article is valid.

    If data for an article has been manually recorded, the entry must have ALL of the
    following fields marked as "false" to be considered valid:

        1. c-do-not-request
        2. c-optout
        3. c-received
        4. c-requested

    If any of the fields are marked as "true", the entry is considered invalid.

    Args:
        element (ET.Element): Element representing an article.

    Returns:
        bool: Flag indicating whether manually entered data for an article is valid
            (True) or invalid (False).
    """
    do_not_request = element.find(
        ".//api:field[@name='c-do-not-request']/api:boolean", NS
    )
    if do_not_request is not None:
        if do_not_request.text == "true":
            return False

    optout = element.find(".//api:field[@name='c-optout']/api:boolean", NS)
    if optout is not None:
        if optout.text == "true":
            return False

    received = element.find(".//api:field[@name='c-received']/api:boolean", NS)
    if received is not None:
        if received.text == "true":
            return False

    requested = element.find(".//api:field[@name='c-requested']/api:boolean", NS)
    if requested is not None:
        if requested.text == "true":
            return False
    return True


def pub_type_is_valid(element: ET.Element) -> bool:
    """Determine whether an article's publication type is valid for inclusion in request.

    An article's publication date is considered valid for inclusion and will
    proceed with other checks if the type is either a journal article, book chapter, or
    conference proceeding.
    """
    pub_type = extract_attribute(
        element, search_string=".//api:object", attribute="type-id"
    )
    if pub_type in ("3", "4", "5"):
        return True
    return False


def include_pub_in_request(element: ET.Element, author_data: dict) -> bool:
    """Perform a series of checks to determine if an article should be requested.

    Args:
        element (ET.Element): Element representing an article.
        author_data (dict): Data about the author's start and end dates of MIT employment.

    Returns:
        bool: Flag indicating whether an article should be included in a request (True)
            or not (False).
    """
    if not pub_date_is_valid(element, author_data):
        return False
    if pub_has_library_status(element):
        return False
    if not pub_type_is_valid(element):
        return False
    if pub_is_oa_exempt(element):
        return False

    if element.find(".//api:record[@source-name='manual']", NS) is not None:
        if not pub_manual_entry_is_valid(element):
            return False

    if pub_is_on_dspace(element):
        return False

    return True


def make_xml(username: str) -> ET.Element:
    top = ET.Element("update-object")
    top.set("xmlns", "http://www.symplectic.co.uk/publications/api")
    oa_field = ET.SubElement(top, "oa")

    # Update library status field
    status_field = ET.SubElement(oa_field, "library-status")
    status_field.set("status", "full-text-requested")
    date_field = ET.SubElement(status_field, "last-requested-when")
    date_field.text = timezone.now().isoformat()
    note_field = ET.SubElement(status_field, "note-field")
    note_field.set("clear-existing-note", "true")
    note = ET.SubElement(note_field, "note")
    note.text = (
        "Library status changed to Full text requested on "
        "{date} by {username}.".format(
            date=timezone.now().strftime("%-d %B %Y"), username=username
        )
    )

    return top


def parse_author_pubs_xml(xml_gen: Generator, author_data: dict) -> list[dict]:
    """Takes a an author-publications record feed from Symplectic
    Elements, parses each record according to local rules for which
    publications should be requested based on certain metadata fields, and
    returns a list of publication IDs that should be imported into Solenoid and
    requested from the author.
    """
    RESULTS = []
    for page in xml_gen:
        root = ET.fromstring(page)
        for element in root.findall("./atom:entry", NS):
            pub_element = element.find(".//api:object[@category='publication']", NS)
            if pub_element is not None:
                pub_id = pub_element.get("id")
            else:
                pub_id = None

            title_element = element.find(".//api:field[@name='title']/api:text", NS)
            if title_element is not None:
                title = title_element.text

            if include_pub_in_request(element, author_data):
                RESULTS.append({"id": pub_id, "title": title})
    return RESULTS


def parse_author_xml(author_xml: str) -> dict:
    root = ET.fromstring(author_xml)

    research_object = root.find(".//api:object", NS)
    if research_object is not None:
        mit_id = research_object.get("proprietary-id")
    else:
        mit_id = None

    AUTHOR_DATA = {
        "Email": extract_field(root, ".//api:email-address"),
        "First Name": extract_field(root, ".//api:first-name"),
        "Last Name": extract_field(root, ".//api:last-name"),
        "MIT ID": mit_id,
        "DLC": extract_field(root, ".//api:primary-group-descriptor"),
        "Start Date": extract_field(root, ".//api:arrive-date"),
    }

    leave_date = root.find(".//api:leave-date", NS)
    if leave_date is not None:
        AUTHOR_DATA["End Date"] = leave_date.text
    else:
        AUTHOR_DATA["End Date"] = "3000-01-01"

    return AUTHOR_DATA


def parse_journal_policies(journal_policies_xml: str) -> dict:
    root = ET.fromstring(journal_policies_xml)
    POLICY_DATA = {
        "C-Method-Of-Acquisition": extract_field(
            root, ".//api:field[@name=" "'c-method-of-acquisition']" "/api:text"
        ),
        "C-Publisher-Related-Email-Message": extract_field(
            root,
            ".//api:field[@name='c-publisher-related-email-message']/api:text",
        ),
    }
    return POLICY_DATA


def parse_paper_xml(paper_xml: str) -> dict:
    root = ET.fromstring(paper_xml)
    if research_object := root.find(".//api:object", NS):
        paper_id = research_object.get("id")
    else:
        paper_id = None

    PAPER_DATA = {
        "Doi": extract_field(root, ".//api:field[@name='doi']/api:text"),
        "Citation": extract_field(root, ".//api:field[@name='c-citation']/api:text"),
        "Publisher-name": extract_field(root, ".//api:field[@name='publisher']/api:text"),
        "C-Method-Of-Acquisition": "",
        "PaperID": paper_id,
        "C-Publisher-Related-Email-Message": "",
        "Year Published": extract_field(
            root, ".//api:field[@name='publication-date']/api:date/api:year"
        ),
        "Title1": extract_field(root, "atom:title"),
        "Journal-name": extract_field(root, ".//api:field[@name='journal']/api:text"),
        "Journal-elements-url": extract_attribute(root, ".//api:journal", "href"),
        "Volume": extract_field(root, ".//api:field[@name='volume']/api:text"),
        "Issue": extract_field(root, ".//api:field[@name='issue']/api:text"),
    }
    return PAPER_DATA
