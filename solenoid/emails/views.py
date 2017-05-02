from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.list import ListView

from solenoid.records.models import Record
from solenoid.userauth.mixins import LoginRequiredMixin

from .models import EmailMessage


def _email_create_one(author, record_list):
    text = EmailMessage.create_original_text(author, record_list)
    EmailMessage.objects.create(
        original_text=text,
        author=author,
        liaison=author.dlc.liaison
    )


def _email_create_many(pk_list):
    """Takes a list of pks of Records and produces Emails which cover all those
    records."""
    # This will be a dict whose keys are authors, and whose values are all
    # records in the pk_list associated with that author.
    email_contexts = {}
    for pk in pk_list:
        record = Record.objects.get(pk=pk)
        if record.author in email_contexts:
            email_contexts[record.author].append(record)
        else:
            email_contexts[record.author] = [record]

    for author, record_list in email_contexts.items():
        _email_create_one(author, record_list)


class EmailCreate(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk_list = request.POST.getlist('records')
        _email_create_many(pk_list)
        return HttpResponseRedirect(reverse('emails:evaluate'))


class EmailEvaluate(LoginRequiredMixin, ListView):
    queryset = EmailMessage.objects.filter(date_sent__isnull=True)
