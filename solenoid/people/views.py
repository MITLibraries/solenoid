import logging

from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView

from solenoid.emails.models import EmailMessage
from solenoid.userauth.mixins import ConditionalLoginRequiredMixin

from .forms import LiaisonCreateForm
from .models import Liaison, DLC
from .signals import update_emails_with_dlcs

logger = logging.getLogger(__name__)


class LiaisonCreate(ConditionalLoginRequiredMixin, CreateView):
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
        context['form_id'] = 'liaison-create'
        return context

    def form_valid(self, form):
        liaison = form.save()
        dlcs = form.cleaned_data['dlc']
        liaison.dlc_set.add(*dlcs)
        update_emails_with_dlcs(dlcs, liaison)
        return HttpResponseRedirect(self.success_url)


class LiaisonList(ConditionalLoginRequiredMixin, ListView):
    model = Liaison
    queryset = Liaison.objects.all()

    def get_context_data(self, **kwargs):
        context = super(LiaisonList, self).get_context_data(**kwargs)
        context['dlc_set'] = DLC.objects.all()
        context['title'] = 'Manage liaisons'
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': '#', 'text': 'manage liaisons'}
        ]
        context['unassigned_dlcs'] = DLC.objects.filter(liaison__isnull=True)
        return context


class LiaisonUpdate(ConditionalLoginRequiredMixin, UpdateView):
    model = Liaison
    queryset = Liaison.objects.all()
    form_class = LiaisonCreateForm
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
        context['form_id'] = 'liaison-update'
        return context

    def get_initial(self):
        initial = super(LiaisonUpdate, self).get_initial()
        initial['dlc'] = DLC.objects.filter(liaison=self.get_object())
        return initial

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

            # Clear existing DLCs (and related EmailMessage liaisons)
            EmailMessage.objects.filter(
                record__author__dlc__in=liaison.dlc_set.all(),
                date_sent__isnull=True).update(_liaison=None)
            liaison.dlc_set.clear()

            # Update liaison ane EmailMessages with new DLCs
            liaison.dlc_set.add(*dlcs)
            update_emails_with_dlcs(dlcs, liaison)

            messages.success(request, 'Liaison updated.')
            return self.form_valid(form)

        else:
            messages.warning(request, 'Please correct the errors below.')
            return self.form_invalid(form)


class LiaisonDelete(ConditionalLoginRequiredMixin, DeleteView):
    model = Liaison
    queryset = Liaison.objects.all()

    def get_context_data(self, **kwargs):
        context = super(LiaisonDelete, self).get_context_data(**kwargs)
        context['title'] = 'Delete liaison ({name})'.format(
            name=self.get_object())
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': reverse_lazy('people:liaison_list'),
                'text': 'manage liaisons'},
            {'url': '#', 'text': 'delete liaison'}
        ]
        return context

    def get_success_url(self):
        messages.success(self.request, 'Liaison deleted.')
        return reverse_lazy('people:liaison_list')
