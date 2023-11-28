import logging
from typing import Any


from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse

from requests.exceptions import HTTPError, Timeout

from solenoid.elements.elements import get_from_elements
from solenoid.elements.xml_handlers import parse_author_xml
from solenoid.people.models import DLC, Author
from .helpers import Fields


logger = logging.getLogger(__name__)


class ImportForm(forms.Form):
    author_id = forms.CharField(label="Author ID", max_length=20)

    def get_author_from_elements(self, author_id: forms.CharField) -> dict:
        author_url = f"{settings.ELEMENTS_ENDPOINT}users/{author_id}"
        try:
            author_xml = get_from_elements(author_url)
        except HTTPError as e:
            logger.info(e)
            if "404 Client Error" in str(e):
                msg = (
                    f"Author with ID {author_id} not found in Elements. "
                    "Please confirm the Elements ID and try again."
                )
                raise ValidationError(message=msg)
        except Timeout as e:
            logger.info(e)
            msg = (
                "Unable to connect to Symplectic "
                "Elements. Please wait a few "
                "minutes and try again."
            )
            raise ValidationError(message=msg)

        author_data = parse_author_xml(author_xml)
        return author_data

    def get_author_from_solenoid(self, author_data: dict) -> Author:
        try:
            author = Author.get_by_mit_id(author_data[Fields.MIT_ID])
        except Author.DoesNotExist:
            if not Author.is_author_creatable(author_data):
                logger.info(
                    f"Author #{author_data['ELEMENTS ID']} was missing data "
                    "from Elements"
                )
                msg = (
                    f"Author with ID {author_data['ELEMENTS ID']} is "
                    f"missing required information. Please check the "
                    f"author record in Elements and confirm that all of "
                    f"the following information is present: "
                    f"{', '.join(Fields.AUTHOR_DATA)}"
                )
                raise ValidationError(message=msg)
        return author

    def clean(self) -> dict[str, Any]:
        author_data = self.get_author_from_elements(self.data["author_id"])
        author = self.get_author_from_solenoid(author_data)
        return self.cleaned_data
