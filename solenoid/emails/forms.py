from ckeditor.widgets import CKEditorWidget

from django import forms

from .models import EmailMessage


class EmailMessageForm(forms.ModelForm):
    class Meta:
        model = EmailMessage
        fields = ['latest_text']
        widgets = {'latest_text': CKEditorWidget()}
