import csv
import logging

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django.utils.html import format_html
from django.utils.safestring import mark_safe

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
        return Record.objects.exclude(
            email__date_sent__isnull=False).prefetch_related(
                'author', 'author__dlc')


class Import(LoginRequiredMixin, FormView):
    template_name = 'records/import.html'
    form_class = ImportForm
    success_url = reverse_lazy('records:unsent_list')

    def _add_messages(self, successes, updates):
        if successes:
            if successes == 1:
                messages.success(self.request, '1 publication has been '
                    'successfully imported. You can now email its author '
                    'about it.')
            else:
                messages.success(self.request, '{x} publications have '
                    'been successfully imported. You can now generate '
                    'emails to authors about them.'.format(x=successes))

        # Don't add a message tallying failures; we have already sent more
        # specific, useful messages about each one.

        if updates:
            if updates == 1:
                messages.info(self.request, '1 existing publication record '
                    'has been successfully updated.')
            else:
                messages.info(self.request, '{x} existing publication records '
                    'have been successfully updated.'.format(x=updates))

        logger.info('messages added')

    def _get_csv_reader(self, csv_file):
        # This used to be a much more complicated function, when we were
        # dealing with an InMemoryUploadedFile rather than a string. See git
        # commit 0fe569e or previous for fun times.
        return csv.DictReader(csv_file.splitlines())

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
            logger.info('record was creatable')
            return Record.get_or_create_from_csv(author, row)
        else:
            return None, None

    def form_valid(self, form):
        reader = self._get_csv_reader(form.cleaned_data['csv_file'])
        successes = 0
        failures = 0
        updates = 0

        for row in reader:
            logger.info('this row is %s' % row)
            if not Record.is_row_valid(row):
                logger.warning('Invalid record row')
                messages.warning(self.request, 'Publication #{id} by {author} '
                    'is missing required data, so this citation will not be '
                    'imported.'.format(id=row[Headers.PAPER_ID],
                                       author=row[Headers.LAST_NAME]))
                failures += 1
                continue

            author = self._get_author(row)
            logger.info('author was %s' % author)

            if not author:
                logger.warning('No author can be found for record')
                messages.warning(self.request, 'The author for publication '
                    '#{id} is missing required information. This record will '
                    'not be created'.format(id=row[Headers.PAPER_ID]))
                failures += 1
                continue

            if Record.is_row_superfluous(row, author):
                logger.info('Record is superfluous')
                messages.info(self.request, 'Publication #{id} by {author} '
                    'has already been requested (possiby from another author, '
                    'so this record will not be imported. Please add this '
                    'citation manually to an email, and manually mark it as '
                    'requested in Symplectic, if you would like to request it '
                    'from this author also'.format(id=row[Headers.PAPER_ID],
                        author=row[Headers.LAST_NAME]))
                failures += 1
                continue

            dupes = Record.get_duplicates(author, row)
            logger.info('dupes {dupes}'.format(dupes=dupes))

            if dupes:
                dupe_list = [id
                             for id
                             in dupes.values_list('paper_id', flat=True)]
                dupe_list = ', '.join(dupe_list)
                logger.info('dupe_list {dupe_list}'.format(dupe_list=dupe_list))
                messages.warning(self.request, 'Publication #{id} by {author} '
                    'duplicates the following record(s) already in the '
                    'database: {dupes}. Please merge #{id} into an existing '
                    'record in Elements. It will not be imported.'.format(
                        id=row[Headers.PAPER_ID],
                        author=row[Headers.LAST_NAME],
                        dupes=dupe_list))

                failures += 1
                continue

            record, created = self._get_record(row, author)
            logger.info('record was %s' % record)
            logger.info('created was %s' % created)

            if not record:
                logger.warning('Cannot create record for publication {id} '
                    'with author {author}'.format(id=row[Headers.PAPER_ID],
                        author=row[Headers.LAST_NAME]))
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

        self._add_messages(successes, updates)

        return super(Import, self).form_valid(form)

    def form_invalid(self, form):
        msg = format_html('The <a href="{}">instructions</a> for '
            'generating CSV files may help; some Excel export options '
            "don't produce good data, especially if you're using a Mac.",
            mark_safe(reverse_lazy('records:instructions')))

        messages.warning(self.request, msg)
        return super(Import, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(Import, self).get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': '#', 'text': 'import csv'}
        ]
        return context
