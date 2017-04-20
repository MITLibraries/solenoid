import logging

from django.views.generic.list import ListView

from solenoid.people.models import Author
from .models import Record

logger = logging.getLogger(__name__)


class UnsentList(ListView):
    def get_context_data(self, **kwargs):
        context = super(UnsentList, self).get_context_data(**kwargs)
        context['page_title'] = 'Unsent Records'
        context['extension_template'] = 'records/_unsent_list.html'
        context['dlcs'] = Author.objects.filter(record__in=self.get_queryset()).values_list('dlc', flat=True)
        return context

    def get_queryset(self):
        return Record.objects.filter(status=Record.UNSENT)


class InvalidList(ListView):
    def get_context_data(self, **kwargs):
        context = super(InvalidList, self).get_context_data(**kwargs)
        context['page_title'] = 'Invalid Records'
        context['extension_template'] = 'records/_invalid_list.html'
        return context

    def get_queryset(self):
        return Record.objects.filter(status=Record.INVALID)
