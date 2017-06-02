import csv
import io
import logging

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from solenoid.people.models import Author, DLC
from solenoid.userauth.mixins import LoginRequiredMixin

from .forms import ImportForm
from .helpers import Headers
from .models import Record

logger = logging.getLogger(__name__)


class UnsentList(LoginRequiredMixin, ListView):
    def get_context_data(self, **kwargs):
        context = super(UnsentList, self).get_context_data(**kwargs)
        context['title'] = 'Unsent citations'
        context['extension_template'] = 'records/_unsent_list.html'
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': '#', 'text': 'view unsent citations'}
        ]
        authors = Author.objects.filter(
            record__in=self.get_queryset()).distinct()
        context['authors'] = authors
        context['dlcs'] = DLC.objects.filter(author__in=authors).distinct()
        return context

    def get_queryset(self):
        return Record.objects.exclude(email__date_sent__isnull=False)


class Import(LoginRequiredMixin, FormView):
    template_name = 'records/import.html'
    form_class = ImportForm
    success_url = reverse_lazy('records:unsent_list')

    def _get_csv_reader(self, csv_file):
        # What's going on in these next two lines?
        # First, we have to make sure we're at the beginning of the file - our
        # previous validation steps may have gotten the pointer to the end, in
        # which case there's nothing left for us to read.
        # Second, we can't feed the csv_file directly into DictReader, because
        # DictReader expects str but in python3 it will get bytes. read()
        # exposes a decode() method, which will coerce its output to str. Then
        # we need to wrap it in StringIO so that it will respond to iteration,
        # as required by DictReader.
        csv_file.seek(0)
        return csv.DictReader(io.StringIO(csv_file.read().decode('utf-8')))

    def _get_author(self, row):
        try:
            author = Author.get_by_mit_id(row[Headers.MIT_ID])
        except Author.DoesNotExist:
            if Author.is_author_creatable(row):
                dlc, _ = DLC.objects.get_or_create(name=row[Headers.DLC])
                author = Author.objects.create(
                    first_name=row[Headers.FIRST_NAME],
                    last_name=row[Headers.LAST_NAME],
                    dlc=dlc,
                    email=row[Headers.EMAIL],
                    mit_id=row[Headers.MIT_ID]
                )
            else:
                author = None
        return author

    def _get_record(self, row, author):
        if Record.is_record_creatable(row):
            return Record.get_or_create_from_csv(author, row)
        else:
            return None, None

    def _is_row_valid(self, row):
        return all([bool(row[x]) for x in Headers.REQUIRED_DATA])

    def _is_row_superfluous(self, row, author):
        """If we have already requested this paper from another author, let's
        not import it."""

        # Find records of the same paper with different authors, if any.
        records = Record.objects.filter(
            paper_id=row[Headers.PAPER_ID]
        ).exclude(
            author=author
        )

        # Return True if we've already sent an email for any of those papers;
        # False otherwise.
        return any([record.email.date_sent
                    for record in records
                    if record.email])

    def form_valid(self, form):
        reader = self._get_csv_reader(form.cleaned_data['csv_file'])
        successes = 0
        failures = 0
        updates = 0

        for row in reader:
            if not self._is_row_valid(row):
                messages.warning(self.request, 'Publication #{id} by {author} '
                    'is missing required data, so this citation will not be '
                    'imported.'.format(id=row[Headers.PAPER_ID],
                                       author=row[Headers.LAST_NAME]))
                failures += 1
                continue

            author = self._get_author(row)

            if self._is_row_superfluous(row, author):
                messages.info(self.request, 'Publication #{id} by {author} '
                    'has already been requested from another author, so this '
                    'record will not be imported. Please add this citation '
                    'manually to an email, and manually mark it as requested '
                    'in Sympletic, if you would like to request it from this '
                    'author also'.format(id=row[Headers.PAPER_ID],
                                         author=row[Headers.LAST_NAME]))
                failures += 1
                continue

            if not author:
                messages.warning(self.request, 'The author for publication '
                    '#{id} is missing required information. This record will '
                    'not be created'.format(id=row[Headers.PAPER_ID]))
                failures += 1
                continue

            record, created = self._get_record(row, author)

            if not record:
                messages.warning(self.request, 'The record for publication '
                    '#{id} by {author} is missing required information and '
                    'will not be created.'.format(id=row[Headers.PAPER_ID],
                        author=row[Headers.LAST_NAME]))
                failures += 1
                continue

            if created:
                successes += 1
            else:
                updates += 1

            if successes:
                if successes == 1:
                    messages.success(self.request, '{x} publication has been '
                        'successfully imported. You can now email its author'
                        'about it.'.format(x=successes))
                else:
                    messages.success(self.request, '{x} publications have '
                        'been successfully imported. You can now generate '
                        'emails to authors about them.'.format(x=successes))

            if failures:
                if failures == 1:
                    messages.info(self.request, '{x} publication could not be '
                        'imported. Please fix it in Sympletic and generate a '
                        'new CSV file.'.format(x=failures))
                else:
                    messages.info(self.request, '{x} publications could not '
                        'be imported. Please fix them in Sympletic and '
                        'generate a new CSV file.'.format(x=failures))

            if updates:
                messages.info(self.request, '{x} existing publication records '
                    'have been successfully updated.'.format(x=updates))

        return super(Import, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(Import, self).get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': '#', 'text': 'import csv'}
        ]
        return context
