from datetime import date
import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.list import ListView

from solenoid.records.models import Record
from solenoid.userauth.mixins import LoginRequiredMixin

from .forms import EmailMessageFormSet
from .models import EmailMessage


logger = logging.getLogger(__name__)


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


def _email_send(pk):
    """
    Validates and sends the EmailMessage with the given pk. Returns True if
    successful; False otherwise.
    """
    # First, validate.
    try:
        email = EmailMessage.objects.get(pk=pk)
        assert not email.date_sent
    except (EmailMessage.DoesNotExist, AssertionError):
        logger.exception('Attempt to send invalid email')
        return False

    # Then, send.
    try:
        recipients = [email.liaison.email_address]
        if settings.SCHOLCOMM_MOIRA_LIST:
            recipients.append(settings.SCHOLCOMM_MOIRA_LIST)

        send_mail(
            'Subject here',
            email.latest_text,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            html_message=email.latest_text,
            fail_silently=False,
        )
        email.date_sent = date.today()
        email.save()
    except SMTPException:
        return False

    return True


class EmailCreate(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk_list = request.POST.getlist('records')
        _email_create_many(pk_list)
        return HttpResponseRedirect(reverse('emails:evaluate'))


class EmailEvaluate(LoginRequiredMixin, ListView):
    queryset = EmailMessage.objects.filter(date_sent__isnull=True)

    def get_context_data(self, **kwargs):
        context = super(EmailEvaluate, self).get_context_data(**kwargs)
        context['formset'] = EmailMessageFormSet(queryset=self.get_queryset())
        return context

    def post(self, request, *args, **kwargs):
        formset = EmailMessageFormSet(
            request.POST, request.FILES,
            queryset=self.get_queryset(),
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Emails updated.')
        else:
            messages.warning(request, 'Could not update emails.')

        return HttpResponseRedirect(reverse('emails:evaluate'))


class EmailRevert(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        try:
            email = EmailMessage.objects.get(pk=pk)
            assert not email.date_sent
            email.revert()
        except AssertionError:
            logger.exception('Attempt to revert an already-sent email')
            messages.warning(request, 'Cannot revert the text of an email '
                'that has already been sent')
        except EmailMessage.DoesNotExist:
            messages.error(request, 'There is no such email message.')
            logger.exception('Attempt to revert text of nonexistent email')
        return HttpResponseRedirect(reverse('emails:evaluate'))


class EmailSend(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk_list = request.POST.getlist('emails')
        statuses = [_email_send(pk) for pk in pk_list]
        if False in statuses:
            messages.warning(request,
                'Some emails were not successfully sent.')
        else:
            messages.success(request, 'All emails sent. Hooray!')

        return HttpResponseRedirect(reverse('home'))
