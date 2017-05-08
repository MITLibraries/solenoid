from ckeditor.widgets import CKEditorWidget

from django.forms import modelformset_factory

from .models import EmailMessage

EmailMessageFormSet = modelformset_factory(
    EmailMessage,
    fields=('latest_text',),
    widgets={'latest_text': CKEditorWidget()},
    extra=0)
