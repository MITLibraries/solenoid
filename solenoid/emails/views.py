import logging

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import close_old_connections, connection
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

    # Because this is outside the request/response cycle, the connections
    # opened here don't close at the end of the function. They may be cleaned
    # when the cycle finishes, but by that time we may have exceeded the number
    # of open connections we're allowed to have on a hobby tier database,
    # resulting in user-visible application failures....so let's close them!
    connection.close()
    return list(set(email_pks))  # remove duplicates, if any


class EmailCreate(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk_list = request.POST.getlist('records')
        email_pks = _get_or_create_emails(pk_list)
        try:
            logger.info('Creating emails for {pks}.'.format(pks=email_pks))
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
        logger.info('Canceling changes to email {pk}'.format(pk=self.kwargs['pk']))
        messages.info(self.request, "Any changes to the email have "
            "been discarded. You may return to the email and update it later.")
        return self._finish_handle()

    def _handle_save(self):
        logger.info('Saving changes to email {pk}'.format(pk=self.kwargs['pk']))
        self.form_valid(self.get_form())
        messages.success(self.request, "Email message updated.")
        return self._finish_handle()

    def _handle_send(self):
        logger.info('Sending email {pk}'.format(pk=self.kwargs['pk']))
        self.form_valid(self.get_form())
        # This should exist, because if it doesn't dispatch() will have already
        # thrown an error and we won't reach this line.
        # If it doesn't exist, users will see a 500, which is also reasonable.
        email = EmailMessage.objects.get(pk=self.kwargs['pk'])
        email.send(self.request.user.username)
        messages.success(self.request, "Email message updated and sent.")
        return self._finish_handle()

    def _update_session(self):
        if not len(self.request.session['email_pks']):
            return None

        try:
            logger.info('Updating email pks in session')
            next_pk = self.request.session['email_pks'].pop(0)
            self.request.session['current_email'] += 1
            return next_pk
        except (KeyError, IndexError):
            logger.exception('Could not update email pks in session')
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

        if self.object.new_citations:
            messages.error(self.request, "New citations for this author "
                "have been imported since last time the email was edited. "
                "They've been added to this email automatically, but please "
                "proofread.")

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
            messages.warning(request, 'This email has been sent; no '
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
        statuses = []
        for pk in pk_list:
            logger.info('Sending email {pk}'.format(pk=pk))
            sent = EmailMessage.objects.get(pk=pk).send(
                self.request.user.username)
            statuses.append(sent)

        if False in statuses:
            logger.warning('Could not send all emails. {bad} of {all} were '
                'not sent.'.format(bad=statuses.count(False),
                                   all=len(pk_list)))
            messages.warning(request,
                'Some emails were not successfully sent. Check to be sure '
                'that a liaison has been assigned for each DLC and try again.')
        else:
            logger.info('All emails successfully sent')
            messages.success(request, 'All emails sent. Hooray!')

        return HttpResponseRedirect(reverse('home'))


class EmailListPending(LoginRequiredMixin, ListView):

    def get_queryset(self):
        qs = EmailMessage.objects.filter(
            date_sent__isnull=True).prefetch_related('author')
        return qs

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

        # Not sure that connection closing is getting triggered properly by the
        # ajax call to here; this can't hurt.
        close_old_connections()
        return HttpResponse(self.object.liaison)
