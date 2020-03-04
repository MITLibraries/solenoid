import logging

from django import forms

logger = logging.getLogger(__name__)


class ImportForm(forms.Form):
    author_id = forms.CharField(label="Author ID", max_length=20)
