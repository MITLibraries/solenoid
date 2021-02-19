import logging

from requests.exceptions import HTTPError, Timeout

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from solenoid.elements.elements import get_from_elements
from solenoid.elements.xml_handlers import parse_author_xml
from solenoid.people.models import DLC, Author
from solenoid.userauth.mixins import ConditionalLoginRequiredMixin

from .forms import ImportForm
from .helpers import Fields
from .models import Record
from .tasks import task_import_papers_for_author

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
    success_url = reverse_lazy('records:status')

    def _get_author_data(self, form, author_id):
        author_url = f'{settings.ELEMENTS_ENDPOINT}users/{author_id}'
        try:
            author_xml = get_from_elements(author_url)
        except HTTPError as e:
            logger.info(e)
            if '404 Client Error' in str(e):
                msg = (f'Author with ID {author_id} not found in Elements. '
                       'Please confirm the Elements ID and try again.')
                messages.warning(self.request, msg)
                return super(Import, self).form_invalid(form)
        except Timeout as e:
            logger.info(e)
            msg = ('Unable to connect to Symplectic '
                   'Elements. Please wait a few '
                   'minutes and try again.')
            messages.warning(self.request, msg)
            return super(Import, self).form_invalid(form)
        author_data = parse_author_xml(author_xml)
        author_data['ELEMENTS ID'] = author_id
        return author_data

    def _get_author_record_id(self, form, author_data):
        try:
            author = Author.get_by_mit_id(author_data[Fields.MIT_ID])
            if not author.dspace_id:
                author.dspace_id = author_data[Fields.MIT_ID]
                author.save()
        except Author.DoesNotExist:
            if Author.is_author_creatable(author_data):
                dlc, _ = DLC.objects.get_or_create(
                    name=author_data[Fields.DLC]
                    )
                author = Author.objects.create(
                    first_name=author_data[Fields.FIRST_NAME],
                    last_name=author_data[Fields.LAST_NAME],
                    dlc=dlc,
                    email=author_data[Fields.EMAIL],
                    mit_id=author_data[Fields.MIT_ID],
                    dspace_id=author_data[Fields.MIT_ID]
                    )
            else:
                logger.info(
                    f"Author #{author_data['ELEMENTS ID']} was missing data "
                    "from Elements"
                    )
                msg = (f"Author with ID {author_data['ELEMENTS ID']} is "
                       f"missing required information. Please check the "
                       f"author record in Elements and confirm that all of "
                       f"the following information is present: "
                       f"{', '.join(Fields.AUTHOR_DATA)}")
                messages.warning(self.request, msg)
                return super(Import, self).form_invalid(form)

        return author.id

    def form_valid(self, form, **kwargs):
        author_id = form.cleaned_data['author_id']
        author_url = f'{settings.ELEMENTS_ENDPOINT}users/{author_id}'
        author_data = self._get_author_data(form, author_id)
        author = self._get_author_record_id(form, author_data)
        result = task_import_papers_for_author.delay(
            author_url,
            author_data,
            author)
        task_id = result.task_id
        return redirect('records:status', task_id=task_id)

    def form_invalid(self, form):
        msg = format_html('Something went wrong. Please try again, and if it '
                          'still doesn\'t work, contact <a mailto="{}">'
                          'a Solenoid admin</a>.',
                          mark_safe(settings.ADMINS[0][1])),

        messages.warning(self.request, msg)
        return super(Import, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(Import, self).get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'url': reverse_lazy('home'), 'text': 'dashboard'},
            {'url': '#', 'text': 'import data'}
        ]
        return context


def status(request, task_id):
    return render(request, 'records/status.html', context={'task_id': task_id})
