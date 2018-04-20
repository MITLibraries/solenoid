import csv
import logging

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from solenoid.people.models import Author, DLC
from solenoid.userauth.mixins import ConditionalLoginRequiredMixin

from .forms import ImportForm
from .helpers import Headers
from .models import Record

logger = logging.getLogger(__name__)


class UnsentList(ConditionalLoginRequiredMixin, ListView):
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


class Import(ConditionalLoginRequiredMixin, FormView):
    template_name = 'records/import.html'
    form_class = ImportForm
    success_url = reverse_lazy('records:unsent_list')

    def _add_messages(self, successes, updates, unchanged):
        if successes:
            if successes == 1:
                messages.success(self.request, '1 new publication has been '
                    'successfully imported. You can now email its author '
                    'about it.')
            else:
                messages.success(self.request, '{x} new publications have '
                    'been successfully imported. You can now generate '
                    'emails to authors about them.'.format(x=successes))

        if updates:
            messages.info(self.request, 'Record(s) updated with new data from '
                'csv: {ids}'.format(ids=', '.join(updates)))

        if unchanged:
            messages.info(self.request, 'Duplicate record(s) not changed: '
                '{ids}'.format(ids=', '.join(unchanged)))

        logger.info('messages added')

    def _check_acq_method(self, row):
        if not Record.is_acq_method_known(row):
            logger.warning('Invalid acquisition method')
            messages.warning(self.request, 'Publication #{id} by {author} '
                'has an unrecognized acquisition method, so this citation '
                'will not be imported.'.format(id=row[Headers.PAPER_ID],
                                   author=row[Headers.LAST_NAME]))
            return False
        return True

    def _check_for_duplicates(self, author, row):
        dupes = Record.get_duplicates(author, row)
        logger.info('dupes {dupes}'.format(dupes=dupes))

        if dupes:
            dupe_list = [id
                         for id
                         in dupes.values_list('paper_id', flat=True)]
            dupe_list = ', '.join(dupe_list)
            logger.info('dupe_list {dupe_list}'.format(dupe_list=dupe_list))  # noqa
            messages.warning(self.request, 'Publication #{id} by {author} '
                'duplicates the following record(s) already in the '
                'database: {dupes}. Please merge #{id} into an existing '
                'record in Elements. It will not be imported.'.format(
                    id=row[Headers.PAPER_ID],
                    author=row[Headers.LAST_NAME],
                    dupes=dupe_list))
            return False
        return True

    def _check_row_validity(self, row):
        if not Record.is_row_valid(row):
            logger.warning('Invalid record row')
            messages.warning(self.request, 'Publication #{id} by {author} '
                'is missing required data (one or more of {info}), so '
                'this citation will not be imported.'.format(
                    id=row[Headers.PAPER_ID],
                    author=row[Headers.LAST_NAME],
                    info=', '.join(Headers.REQUIRED_DATA)))
            return False
        return True

    def _check_row_superfluity(self, author, row):
        if Record.is_row_superfluous(row, author):
            logger.info('Record is superfluous')
            messages.info(self.request, 'Publication #{id} by {author} '
                'has already been requested (possibly from another '
                'author), so this record will not be imported. Please add '
                'this citation manually to an email, and manually mark it '
                'as requested in Symplectic, if you would like to request '
                'it from this author also'.format(id=row[Headers.PAPER_ID],
                    author=row[Headers.LAST_NAME]))
            return False
        return True

    def _get_csv_reader(self, csv_file):
        # This used to be a much more complicated function, when we were
        # dealing with an InMemoryUploadedFile rather than a string. See git
        # commit 0fe569e or previous for fun times.
        # Now it just validates the delimiter, since usually csv is comma-
        # delimited, but csv reports exported from Tableau are tab-delimited.
        dialect = csv.Sniffer().sniff(csv_file)
        return csv.DictReader(csv_file.splitlines(),
                              delimiter=dialect.delimiter)

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
                logger.warning('No author can be found for record')
                messages.warning(self.request, 'The author for publication '
                    '#{id} is missing required information. This record will '
                    'not be created'.format(id=row[Headers.PAPER_ID]))
        logger.info('author was %s' % author)
        return author

    def _get_record(self, row, author):
        if Record.is_record_creatable(row):
            logger.info('record was creatable')
            record, created = Record.get_or_create_from_csv(author, row)
        else:
            logger.warning('Cannot create record for publication {id} '
                'with author {author}'.format(id=row[Headers.PAPER_ID],
                    author=row[Headers.LAST_NAME]))
            messages.warning(self.request, 'The record for publication '
                '#{id} by {author} is missing required information and '
                'will not be created.'.format(id=row[Headers.PAPER_ID],
                    author=row[Headers.LAST_NAME]))
            record = None
            created = None

        logger.info('record was %s' % record)
        logger.info('created was %s' % created)

        return record, created

    def form_valid(self, form):
        reader = self._get_csv_reader(form.cleaned_data['csv_file'])
        successes = 0
        updates = []
        unchanged = []

        for row in reader:
            logger.info('this row is %s' % row)

            if not self._check_row_validity(row):
                continue

            if not self._check_acq_method(row):
                continue

            author = self._get_author(row)

            if not author:
                continue

            if not self._check_row_superfluity(author, row):
                continue

            if not self._check_for_duplicates(author, row):
                continue

            record, created = self._get_record(row, author)

            if not record:
                continue

            if created:
                successes += 1
            else:
                updated = record.update_if_needed(row, author)
                if updated:
                    updates.append(record.paper_id)
                else:
                    unchanged.append(record.paper_id)

        self._add_messages(successes, updates, unchanged)

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
