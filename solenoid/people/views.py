import logging

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView

from solenoid.userauth.mixins import LoginRequiredMixin

from .forms import LiaisonCreateForm, LiaisonDLCForm
from .models import Liaison, DLC

logger = logging.getLogger(__name__)


class LiaisonCreate(LoginRequiredMixin, CreateView):
    model = Liaison
    form_class = LiaisonCreateForm
    success_url = reverse_lazy('people:liaison_list')

    def get_context_data(self, **kwargs):
        context = super(LiaisonCreate, self).get_context_data(**kwargs)
        context['title'] = 'Add liaison'
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': reverse_lazy('people:liaison_list'),
                'text': 'manage liaisons'},
            {'url': '#', 'text': 'edit liaison'}
        ]
        return context

    def form_valid(self, form):
        liaison = form.save()
        liaison.dlc_set.add(*form.cleaned_data['dlc'])
        return HttpResponseRedirect(self.success_url)


class LiaisonList(LoginRequiredMixin, ListView):
    model = Liaison

    def get_context_data(self, **kwargs):
        context = super(LiaisonList, self).get_context_data(**kwargs)
        context['dlc_set'] = DLC.objects.all()
        context['title'] = 'Manage liaisons'
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': '#', 'text': 'manage liaisons'}
        ]
        return context


class LiaisonUpdate(LoginRequiredMixin, UpdateView):
    model = Liaison
    fields = ('first_name', 'last_name', 'email_address')
    success_url = reverse_lazy('people:liaison_list')

    def get_context_data(self, **kwargs):
        context = super(LiaisonUpdate, self).get_context_data(**kwargs)
        context['title'] = 'Edit liaison'
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': reverse_lazy('people:liaison_list'),
                'text': 'manage liaisons'},
            {'url': '#', 'text': 'edit liaison'}
        ]
        context['dlc_form'] = LiaisonDLCForm()
        return context

    def post(self, request, *args, **kwargs):
        # This would normally be set in post(), but we're not calling super, so
        # we need to do it ourselves.
        self.object = self.get_object()

        form = self.get_form()

        if form.is_valid():
            try:
                dlcs = DLC.objects.filter(pk__in=request.POST.getlist('dlc'))
            except KeyError:
                logger.exception()
                raise

            liaison = self.get_object()
            liaison.dlc_set.clear()
            liaison.dlc_set.add(*dlcs)
            messages.success(request, 'Liaison updated.')
            return self.form_valid(form)

        else:
            messages.warning(request, 'Please correct the errors below.')
            return self.form_invalid(form)
