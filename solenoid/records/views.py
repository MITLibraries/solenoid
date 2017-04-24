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

    def form_valid(self, form):
        reader = self._get_csv_reader(form.cleaned_data['csv_file'])
        authors_no_dlc = []

        for row in reader:
            # Reject any records with missing DLCs, and notify the user.
            if not row[Headers.DLC]:
                if not row[Headers.LAST_NAME] in authors_no_dlc:
                    messages.warning(self.request, 'Author {first} {last} is '
                        'missing a DLC; not importing records for this '
                        'author. Please add a DLC in Symplectic and generate '
                        'a new CSV file.'.format(first=row[Headers.FIRST_NAME],
                            last=row[Headers.LAST_NAME]))
                continue

            dlc, _ = DLC.objects.get_or_create(name=row[Headers.DLC])
            try:
                Author.objects.get(mit_id=row[Headers.MIT_ID])
            except Author.DoesNotExist:
                author = Author.objects.create(
                    first_name=row[Headers.FIRST_NAME],
                    last_name=row[Headers.LAST_NAME],
                    dlc=dlc,
                    email=row[Headers.EMAIL],
                )

            Record.objects.create(
                author=author,
                publisher_name=row[Headers.PUBLISHER_NAME],
                acq_method=row[Headers.ACQ_METHOD],
                citation=row[Headers.CITATION],
                doi=row[Headers.DOI],
            )
        return super(Import, self).form_valid(form)
