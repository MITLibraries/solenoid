from django.views.generic.edit import CreateView

from .models import Liaison


class LiaisonCreate(CreateView):
    model = Liaison
    fields = ('first_name', 'last_name')
