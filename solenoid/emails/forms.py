from ckeditor.widgets import CKEditorWidget

from django import forms

from .models import EmailMessage


class EmailMessageForm(forms.ModelForm):
    class Meta:
        model = EmailMessage
        fields = ["latest_text"]
        widgets = {"latest_text": CKEditorWidget()}

    def __init__(self, *args, **kwargs):
        super(EmailMessageForm, self).__init__(*args, **kwargs)
        self.fields["latest_text"].label = ""

    def save(self, *args, **kwargs):
        self.instance.new_citations = False
        super(EmailMessageForm, self).save()
