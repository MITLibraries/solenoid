import csv
import io
import logging

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from solenoid.people.models import Author, DLC

from .forms import ImportForm
from .helpers import Headers
from .models import Record

logger = logging.getLogger(__name__)


class UnsentList(ListView):
    def get_context_data(self, **kwargs):
        context = super(UnsentList, self).get_context_data(**kwargs)
        context['page_title'] = 'Unsent Records'
        context['extension_template'] = 'records/_unsent_list.html'
        context['dlcs'] = Author.objects.filter(
            record__in=self.get_queryset()).values_list('dlc', flat=True)
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


class Import(FormView):
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
            author = Author.objects.get(mit_id=row[Headers.MIT_ID])
        except Author.DoesNotExist:
            if self._is_author_creatable(row):
                dlc, _ = DLC.objects.get_or_create(name=row[Headers.DLC])
                author = Author.objects.create(
                    first_name=row[Headers.FIRST_NAME],
                    last_name=row[Headers.LAST_NAME],
                    dlc=dlc,
                    email=row[Headers.EMAIL],
                )
            else:
                author = None
        return author

    def _is_author_creatable(self, row):
        return all([bool(row[x] for x in Headers.AUTHOR_DATA)])

    def _is_row_valid(self, row):
        return all([bool(row[x]) for x in Headers.REQUIRED_DATA])

    def form_valid(self, form):
        reader = self._get_csv_reader(form.cleaned_data['csv_file'])
        successes = 0
        failures = 0

        for row in reader:
            if not self._is_row_valid(row):
                messages.warning(self.request, 'Publication #{id} is missing '
                    'required data, so this citation will not be '
                    'imported.'.format(id=row[Headers.PAPER_ID]))
                failures += 1
                continue

            author = self._get_author(row)

            if not author:
                messages.warning(self.request, 'The author for publication '
                    '#{id} is missing required information.'.format(
                        id=row[Headers.PAPER_ID]))
                failures += 1
                continue

            if not Record.is_record_creatable(row):
                messages.warning(self.request, 'The record for publication '
                    '#{id} is missing required information and will not be '
                    'created.'.format(id=row[Headers.PAPER_ID]))
                failures += 1
                continue

            Record.objects.create(
                author=author,
                publisher_name=row[Headers.PUBLISHER_NAME],
                acq_method=row[Headers.ACQ_METHOD],
                citation=row[Headers.CITATION],
                doi=row[Headers.DOI],
            )
            successes += 1

            if successes:
                messages.success(self.request, '{x} publications have been '
                    'successfully imported. You can now generate emails to '
                    'authors about them.'.format(x=successes))

            if failures:
                messages.info(self.request, '{x} publications could not be '
                    'imported. Please fix them in Sympletic and generate a '
                    'new CSV file.'.format(x=failures))
        return super(Import, self).form_valid(form)
