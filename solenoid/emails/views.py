from datetime import date
import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import View, DetailView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView

from solenoid.people.models import Author
from solenoid.records.models import Record
from solenoid.userauth.mixins import LoginRequiredMixin

from .forms import EmailMessageForm
from .models import EmailMessage


logger = logging.getLogger(__name__)


def _get_or_create_emails(pk_list):
    """Takes a list of pks of Records and gets or creates associated
    EmailMessages."""
    email_pks = []

    for author in Author.objects.filter(record__pk__in=pk_list).distinct():
        records = Record.objects.filter(pk__in=pk_list, author=author)
        email_pks.append(EmailMessage.get_or_create_for_records(records).pk)

    return list(set(email_pks))  # remove duplicates, if any


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

    try:
        # Can't send the email if there isn't a liaison.
        assert email.liaison
    except AssertionError:
        logger.exception('Attempt to send email {pk}, which is missing a '
            'liaison'.format(pk=pk))
        return False

    # Then, send.
    try:
        recipients = [email.liaison.email_address]
        if settings.SCHOLCOMM_MOIRA_LIST:
            recipients.append(settings.SCHOLCOMM_MOIRA_LIST)

        send_mail(
            'Subject here',
            email.plaintext,
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
            request.session["total_email"] = len(email_pks) + 1
            request.session["current_email"] = 1
            return HttpResponseRedirect(reverse('emails:evaluate',
                args=(first_pk,)))
        except IndexError:
            logger.exception('No email pks found; email cannot be created.')
            messages.warning(request, 'No email messages found.')
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

    def _finish_handle(self):
        next_pk = self._update_session()
        if next_pk:
            self.kwargs['next_pk'] = next_pk
        else:
            try:
                del self.kwargs['next_pk']
            except:
                pass

        return HttpResponseRedirect(self.get_success_url())

    def _handle_cancel(self):
        messages.info(self.request, "Any changes to the email have "
            "been discarded. You may return to the email and update it later.")
        return self._finish_handle()

    def _handle_save(self):
        self.form_valid(self.get_form())
        messages.success(self.request, "Email message updated.")
        return self._finish_handle()

    def _handle_send(self):
        self.form_valid(self.get_form())
        _email_send(self.kwargs['pk'])
        messages.success(self.request, "Email message updated and sent.")
        return self._finish_handle()

    def _update_session(self):
        try:
            next_pk = self.request.session['email_pks'].pop(0)
            self.request.session['current_email'] += 1
            return next_pk
        except (KeyError, IndexError):
            # If we don't have email_pks in session, or we have run off the end
            # of the list and have no more to pop, then we should clean up any
            # other email-pk-related stuff that still exists.
            try:
                del self.request.session['current_email']
                del self.request.session['total_email']
            except KeyError:
                pass

            return None

    def get_context_data(self, **kwargs):
        context = super(EmailEvaluate, self).get_context_data(**kwargs)
        if self.object.date_sent:
            context['title'] = 'View sent email'
        else:
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
        if 'next_pk' in self.kwargs:
            return reverse('emails:evaluate', args=(self.kwargs['next_pk'],))
        else:
            return reverse('home')

    def get_template_names(self):
        if self.object.date_sent:
            return ['emails/evaluate_sent.html']
        else:
            return super(EmailEvaluate, self).get_template_names()

    def post(self, request, *args, **kwargs):
        # This would normally be set by post(); since we're not calling super
        # we are responsible for setting it.
        self.object = self.get_object()

        if self.object.date_sent:
            messages.warning(request, 'This email has already been sent; no '
                'further changes can be made.')
            return HttpResponseRedirect(reverse('emails:evaluate',
                args=(self.kwargs['pk'])))

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

    def get_context_data(self, **kwargs):
        context = super(EmailListPending, self).get_context_data(**kwargs)
        context['title'] = 'Unsent emails'
        context['breadcrumbs'] = [
            {'url': reverse('home'), 'text': 'dashboard'},
            {'url': '#', 'text': 'view pending emails'},
        ]
        return context


class EmailLiaison(LoginRequiredMixin, DetailView):
    """
    A simple API to let the front end ask the back end who the liaison for an
    email is.

    We need this on the email evaluation page, so that we can figure out the
    outcome of the assign-liaison process that happens in the modal.
    """
    model = EmailMessage

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return HttpResponse(self.object.liaison)
