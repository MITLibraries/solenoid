# The goal: given a Record, mark it as requested in Elements.

# Current status and next steps:
# * Authentication requires credentials + app whitelist + firewall whitelist;
#   have acquired that for test, and requested firewall whitelist in production
# * The required workflow is:
#   1) GET the object
#   2) find all manual records associated with the object (type 'manual' is not
#      guaranteed to be unique) and get their record IDs
#   3) issue PATCH requests for all records to update their c-requested field
#      (and possibly the date and note fields)
# * Make sure xml validates; then remove validation parameter
# * Integrate with signals so that it's nonblocking
#   * Consider whether you want to do a scheduler dyno later - might have a
#     cost, but would let you rerun all failed updates
# * Consider whether you want any kind of logging/monitoring to notify you when
#   the API fails
# * If we can get the record number from the CSV, do that (and definitely
#   monitor it).

import requests
from urllib.parse import urljoin
from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings

top = Element('update-object')
top.set('xmlns', 'http://www.symplectic.co.uk/publications/api')
fields = SubElement(top, 'fields')
container_field = SubElement(fields, 'field')
container_field.set('name', 'c-requested')
container_field.set('operation', 'set')
bool_field = SubElement(container_field, 'boolean')
bool_field.text = 'true'

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

"""
From response = requests.get(settings.ELEMENTS_ENDPOINT + 'publication/types',
                             params={'validate': 'true'},
                             auth=(settings.ELEMENTS_USER,
                                   settings.ELEMENTS_PASSWORD)):
   <field>
        <name>c-requested</name>
        <display-name>Requested</display-name>
        <type>boolean</type>
        <field-group>metadata</field-group>
        <is-mandatory>false</is-mandatory>
        <update-field-operations>
            <operation type="set"/>
            <operation type="clear"/>
        </update-field-operations>
    </field>
    <field>
        <name>c-reqdate</name>
        <display-name>ReqDate</display-name>
        <type>date</type>
        <field-group>metadata</field-group>
        <is-mandatory>false</is-mandatory>
        <update-field-operations>
            <operation type="set"/>
            <operation type="clear"/>
        </update-field-operations>
    </field>
    <field>
        <name>c-reqnote</name>
        <display-name>ReqNote</display-name>
        <type>text</type>
        <field-group>metadata</field-group>
        <is-mandatory>false</is-mandatory>
        <update-field-operations>
            <operation type="set"/>
            <operation type="clear"/>
        </update-field-operations>
    </field>
"""

"""
Error:
<api:warning associated-field="c-requested">Invalid Field Warning: Field
c-requested does not exist on a Publication object.</api:warning>
"""
