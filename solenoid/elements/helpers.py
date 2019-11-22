from xml.etree.ElementTree import Element, SubElement

from django.utils import timezone


def make_xml(username):
    top = Element('update-object')
    top.set('xmlns', 'http://www.symplectic.co.uk/publications/api')
    oa_field = SubElement(top, 'oa')

    # Update library status field
    status_field = SubElement(oa_field, 'library-status')
    status_field.set('status', 'full-text-requested')
    date_field = SubElement(status_field, 'last-requested-when')
    date_field.text = timezone.now().isoformat()
    note_field = SubElement(status_field, 'note-field')
    note_field.set('clear-existing-note', 'true')
    note = SubElement(note_field, 'note')
    note.text = "Library status changed to Full text requested on " \
        "{date} by {username}.".format(
            date=timezone.now().strftime('%-d %B %Y'),
            username=username)

    return top
