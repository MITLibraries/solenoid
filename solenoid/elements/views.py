# The goal: given a Record, mark it as requested in Elements.

# Todo:
# Get the requests call to work
#       It's refusing connections due to an error that Elements is having
#       communicating with readcube. ...
# Make sure xml validates; then remove validation parameter
# Ask if you also need to update date
# Integrate with signals so that it's nonblocking
#       Consider whether you want to do a scheduler dyno later - might have a
#       cost, but would let you rerun all failed updates

import requests
from urllib.parse import urljoin
from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings

top = Element('update-record')
top.set('xmlns', 'http://www.symplectic.co.uk/publications/api')
fields = SubElement(top, 'fields')
field = SubElement(fields, 'field')
field.set('name', 'c-requested')
field.set('operation', 'set')
field.text = 'true'  # try this, but you might need a SubElement 'text'

# https://pubdata-dev.mit.edu/viewobject.html?id=307811&cid=1
pub_id = 307811  # get this from actual record later
headers = {'Content-Type': 'application/xml'}
url = urljoin(settings.ELEMENTS_ENDPOINT,
              'publications/{id}'.format(id=pub_id))

requests.patch(url,
               data=tostring(top).decode('utf-8'),
               params={'validate': 'true'},  # take this out once it's verified
               headers=headers,
               # Passing in an auth parameter makes requests handle HTTP Basic
               # Auth transparently.
               auth=(settings.ELEMENTS_USER, settings.ELEMENTS_PASSWORD))
