import logging

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.edit import CreateView, FormView
from django.views.generic.list import ListView

from solenoid.userauth.mixins import LoginRequiredMixin

from .forms import LiaisonCreateForm, DLCUpdateFormSet
from .models import Liaison, DLC

logger = logging.getLogger(__name__)


class LiaisonCreate(LoginRequiredMixin, CreateView):
    model = Liaison
    form_class = LiaisonCreateForm
    success_url = reverse_lazy('people:liaison_list')

    def form_valid(self, form):
        liaison = form.save()
        liaison.dlc_set.add(*form.cleaned_data['dlc'])
        return HttpResponseRedirect(self.success_url)


class LiaisonList(LoginRequiredMixin, ListView):
    model = Liaison

    def get_context_data(self, **kwargs):
        context = super(LiaisonList, self).get_context_data(**kwargs)
        context['dlc_set'] = DLC.objects.all()
        return context


class LiaisonUpdate(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            dlcs = DLC.objects.filter(pk__in=request.POST.getlist('dlc'))
        except KeyError:
            logger.exception()
            raise

        try:
            liaison = Liaison.objects.get(pk=self.kwargs['pk'])
        except (KeyError, Liaison.DoesNotExist):
            logger.exception()
            raise

        liaison.dlc_set.clear()
        liaison.dlc_set.add(*dlcs)
        messages.success(request, 'DLCs updated for {l.first_name} '
            '{l.last_name}.'.format(l=liaison))

        return HttpResponseRedirect(reverse_lazy('people:liaison_list'))


class DLCUpdateView(LoginRequiredMixin, FormView):
    form_class = DLCUpdateFormSet
    template_name = 'people/dlc_form.html'
    success_url = reverse_lazy('people:liaison_list')

    def form_valid(self, form):
        DLCUpdateFormSet(self.request.POST).save()
        messages.success(self.request, 'DLCs updated.')
        return HttpResponseRedirect(reverse_lazy('people:liaison_list'))
