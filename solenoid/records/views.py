import logging

from django.views.generic.list import ListView

from .models import Record

logger = logging.getLogger(__name__)


class UnsentList(ListView):
    def get_queryset(self):
        return Record.objects.filter(status=Record.UNSENT)


class InvalidList(ListView):
    def get_queryset(self):
        return Record.objects.filter(status=Record.INVALID)
