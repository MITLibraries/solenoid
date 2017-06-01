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
# Make sure to validate for the record ID when you ingest CSV.

# Note: Christine has figured out how to include record ID (YAY), so we only
# have to issue the patch call. However, I'm not sure how to validate the date
# field.

from datetime import date
import logging
import requests
from urllib.parse import urljoin
from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver

from solenoid.emails.models import email_sent

from .models import ElementsAPICall


logger = logging.getLogger(__name__)


@receiver(email_sent)
def issue_elements_api_call(sender):
    """Notifies Elements when a record has been requested.

    Note that this wants to be a *signal receiver* and not anything that could
    conceivably block a view, since the latency on the response may be high
    (it may even time out)."""
    if not settings.USE_ELEMENTS:
        return

    if not settings.ELEMENTS_PASSWORD:
        logger.warning('Tried to issue Elements API call without password')
        raise ImproperlyConfigured

    # Construct XML. (This is the same for all records in the email.)
    xml = ElementsAPICall.make_xml()

    for record in sender.record_set.all():
        # Get endpoint for this record
        url = urljoin(settings.ELEMENTS_ENDPOINT,
                      'publication/records/{source}/{id}'.format(
                          source=record.source, id=record.elements_id))

        # Send request
        response = requests.patch(url,
            data=tostring(xml).decode('utf-8'),
            headers=headers,
            # Passing in an auth parameter makes requests handle HTTP Basic
            # Auth transparently.
            auth=(settings.ELEMENTS_USER, settings.ELEMENTS_PASSWORD))

        # Record response
        ElementsAPICall.objects.create(
            request_data=xml,
            request_url=url,
            response_content=response.content,
            response_status=response.status_code
        )

        # * error handling???


top = Element('update-record')
top.set('xmlns', 'http://www.symplectic.co.uk/publications/api')
fields = SubElement(top, 'fields')

# Update c-requested field
container_field = SubElement(fields, 'field')
container_field.set('name', 'c-requested')
container_field.set('operation', 'set')
bool_field = SubElement(container_field, 'boolean')
bool_field.text = 'true'

# Update c-reqdate field
container_field = SubElement(fields, 'field')
container_field.set('name', 'c-reqdate')
container_field.set('operation', 'set')
date_field = SubElement(container_field, 'date')
date_field.text = date.today().strftime('%d/-%m-%Y')

# Update c-reqnote field
container_field = SubElement(fields, 'field')
container_field.set('name', 'c-reqdate')
container_field.set('operation', 'set')
date_field = SubElement(container_field, 'text')
date_field.text = 'Email sent by solenoid'

# https://pubdata-dev.mit.edu/viewobject.html?id=307811&cid=1
record_id = 22667  # get this from actual record later
source = "Manual"  # this too
headers = {'Content-Type': 'application/xml'}
url = urljoin(settings.ELEMENTS_ENDPOINT,
              'publication/records/{source}/{id}'.format(source=source, id=record_id))

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
