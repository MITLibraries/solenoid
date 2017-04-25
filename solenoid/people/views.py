from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

from .forms import LiaisonCreateForm
from .models import Liaison


class LiaisonCreate(CreateView):
    model = Liaison
    form_class = LiaisonCreateForm
    success_url = reverse_lazy('people:liaison_list')

    def form_valid(self, form):
        liaison = form.save()
        liaison.dlc_set.add(*form.cleaned_data['dlc'])
        return HttpResponseRedirect(self.success_url)


class LiaisonList(ListView):
    model = Liaison
