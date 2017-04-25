from django import forms

from .models import Liaison, DLC


class LiaisonCreateForm(forms.ModelForm):
    class Meta:
        model = Liaison
        fields = ('first_name', 'last_name', 'email_address')

    def __init__(self, *args, **kwargs):
        super(LiaisonCreateForm, self).__init__(*args, **kwargs)
        self.fields['dlc'] = forms.ModelMultipleChoiceField(
            queryset=DLC.objects.all())
