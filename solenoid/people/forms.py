from django import forms

from .models import Liaison, DLC


class LiaisonCreateForm(forms.ModelForm):
    class Meta:
        model = Liaison
        fields = ("first_name", "last_name", "email_address")

    def __init__(self, *args, **kwargs):
        super(LiaisonCreateForm, self).__init__(*args, **kwargs)
        self.fields["dlc"] = forms.ModelMultipleChoiceField(
            queryset=DLC.objects.all(), required=False
        )  # allow 0 DLCs to be selected
        self.fields["dlc"].widget.attrs["class"] = "field field-select"
        self.fields["first_name"].widget.attrs["class"] = "field field-text"
        self.fields["last_name"].widget.attrs["class"] = "field field-text"
        self.fields["email_address"].widget.attrs["class"] = "field " "field-email"
