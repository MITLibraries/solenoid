from datetime import date
import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView

from solenoid.people.models import Author
from solenoid.userauth.mixins import LoginRequiredMixin

from .forms import EmailMessageForm
from .models import EmailMessage


logger = logging.getLogger(__name__)


def _get_or_create_emails(pk_list):
    """Takes a list of pks of Records and gets or creates EmailMessages to all
    associated Authors."""
    email_pks = []

    for author in Author.objects.filter(record__pk__in=pk_list):
        email_pks.append(EmailMessage.get_or_create_by_author(author).pk)

    return email_pks


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
        email_pks = _get_or_create_emails(pk_list)
        try:
            first_pk = email_pks.pop(0)
            request.session["email_pks"] = email_pks
            request.session["total_email"] = len(email_pks)
            request.session["current_email"] = 1
            return HttpResponseRedirect(reverse('emails:evaluate',
                args=(first_pk,)))
        except IndexError:
            logger.exception('No email pks found; email cannot be created.')
            messages.warning('No email messages found.')
            return HttpResponseRedirect(reverse('home'))


class EmailEvaluate(LoginRequiredMixin, UpdateView):
    """EmailEvaluate lets the user see, edit, and send a single email.
    Because workflows may involve queuing up multiple unsent emails (e.g. after
    importing a large number of citations), get_success_url will decide where
    to redirect the user as follows:
    1) If there is a list of email_pks in the session, get_success_url will
       send the user to the pk of the next email (and remove that pk from the
       list).
    2) If there isn't, or if it's empty, users will be redirected to the
       dashboard.
    """
    form_class = EmailMessageForm
    model = EmailMessage

    def _handle_cancel(self):
        messages.info(self.request, "Any changes to the email have "
            "been discarded. You may return to the email and update it later.")
        return self.get_success_url()

    def _handle_save(self):
        self.form_valid(self.get_form())
        messages.success(self.request, "Email message updated.")
        return self.get_success_url()

    def _handle_send(self):
        self.form_valid(self.get_form())
        _email_send(self.kwargs['pk'])
        messages.success(self.request, "Email message updated and sent.")
        return self.get_success_url()

    def _update_session(self):
        try:
            next_pk = self.request.session['email_pks'].pop(0)
            self.request.session['current_email'] += 1
            return next_pk
        except KeyError:
            return None

    def get_context_data(self, **kwargs):
        context = super(EmailEvaluate, self).get_context_data(**kwargs)
        context['title'] = 'Send email'
        try:
            context['progress'] = '#{k} of {n}'.format(
                k=self.request.session['current_email'],
                n=self.request.session['total_email'])
        except KeyError:
            pass

        context['breadcrumbs'] = [
            {'url': reverse('home'), 'text': 'dashboard'},
            {'url': reverse('emails:list_pending'),
                'text': 'view pending emails'},
            {'url': '#', 'text': 'send email'}
        ]
        return context

    def get_success_url(self):
        next_pk = self._update_session()
        if next_pk:
            return HttpResponseRedirect(reverse('emails:evaluate',
                args=(next_pk,)))
        else:
            return HttpResponseRedirect(reverse('home'))

    def post(self, request, *args, **kwargs):
        if 'submit_cancel' in request.POST:
            return self._handle_cancel()
        elif 'submit_save' in request.POST:
            return self._handle_save()
        elif 'submit_send' in request.POST:
            return self._handle_send()
        else:
            messages.warning(request,
                "I'm sorry; I can't tell what you meant to do.")
            return self.form_invalid(self.get_form())


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


class EmailListPending(LoginRequiredMixin, ListView):
    queryset = EmailMessage.objects.filter(date_sent__isnull=True)
