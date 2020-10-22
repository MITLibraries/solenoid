import logging

from requests.exceptions import HTTPError, Timeout

from django.conf import settings
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from solenoid.elements.elements import get_from_elements, get_paged
from solenoid.elements.xml_handlers import (parse_author_pubs_xml,
                                            parse_author_xml,
                                            parse_journal_policies,
                                            parse_paper_xml)
from solenoid.people.models import DLC, Author
from solenoid.userauth.mixins import ConditionalLoginRequiredMixin

from .forms import ImportForm
from .helpers import Fields
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
                                 'successfully imported. You can now email '
                                 'its author about it.')
            else:
                messages.success(self.request, '{x} new publications have '
                                 'been successfully imported. You can now '
                                 'generate emails to authors about '
                                 'them.'.format(x=successes))

        if updates:
            messages.info(self.request, 'Record(s) updated with new data from '
                          'Elements: {ids}'.format(ids=', '.join(updates)))

        if unchanged:
            messages.info(self.request, 'Duplicate record(s) not changed: '
                          '{ids}'.format(ids=', '.join(unchanged)))

        logger.info('messages added')

    def _check_for_duplicates(self, author, paper_data):
        dupes = Record.get_duplicates(author, paper_data)
        logger.info('dupes {dupes}'.format(dupes=dupes))

        if dupes:
            dupe_list = [id
                         for id
                         in dupes.values_list('paper_id', flat=True)]
            dupe_list = ', '.join(dupe_list)
            logger.info('dupe_list {dupe_list}'.format(dupe_list=dupe_list))
            messages.warning(self.request, 'Publication #{id} by {author} '
                             'duplicates the following record(s) already in '
                             'the database: {dupes}. Please merge #{id} into '
                             'an existing record in Elements. It will not be '
                             'imported.'.format(id=paper_data[Fields.PAPER_ID],
                                                author=paper_data[
                                                    Fields.LAST_NAME],
                                                dupes=dupe_list))
            return False
        return True

    def _check_data_validity(self, paper_data):
        if not Record.is_data_valid(paper_data):
            logger.warning('Invalid record data')
            messages.warning(self.request, 'Publication #{id} by {author} '
                             'is missing required data (one or more of '
                             '{info}), so this citation will not be imported.'
                             .format(id=paper_data[Fields.PAPER_ID],
                                     author=paper_data[Fields.LAST_NAME],
                                     info=', '.join(Fields.REQUIRED_DATA)))
            return False
        return True

    def _check_paper_superfluity(self, author, paper_data):
        if Record.paper_requested(paper_data):
            logger.info('Paper already requested, record not imported')
            messages.info(self.request, 'Publication #{id} by {author} '
                          'has already been requested (possibly from another '
                          'author), so this record will not be imported. '
                          'Please add this citation manually to an email, '
                          'and manually mark it as requested in Symplectic, '
                          'if you would like to request it from this author '
                          'also'.format(id=paper_data[Fields.PAPER_ID],
                                        author=paper_data[Fields.LAST_NAME]))
            return False
        return True

    def _get_author(self, paper_data):
        try:
            author = Author.get_by_mit_id(paper_data[Fields.MIT_ID])
            if not author.dspace_id:
                author.dspace_id = paper_data[Fields.MIT_ID]
                author.save()
        except Author.DoesNotExist:
            if Author.is_author_creatable(paper_data):
                dlc, _ = DLC.objects.get_or_create(name=paper_data[Fields.DLC])
                author = Author.objects.create(
                    first_name=paper_data[Fields.FIRST_NAME],
                    last_name=paper_data[Fields.LAST_NAME],
                    dlc=dlc,
                    email=paper_data[Fields.EMAIL],
                    mit_id=paper_data[Fields.MIT_ID],
                    dspace_id=paper_data[Fields.MIT_ID]
                )
            else:
                author = None
                logger.warning('No author can be found for record')
                messages.warning(self.request, 'The author for publication '
                                 '#{id} is missing required information. '
                                 'This record will not be created'
                                 .format(id=paper_data[Fields.PAPER_ID]))
        logger.info('author was %s' % author)
        return author

    def _get_record(self, paper_data, author):
        if Record.is_record_creatable(paper_data):
            logger.info('record was creatable')
            record, created = Record.get_or_create_from_data(author,
                                                             paper_data)
        else:
            logger.warning(f'Cannot create record for publication '
                           f'{paper_data[Fields.PAPER_ID]} with '
                           f'author {paper_data[Fields.LAST_NAME]}')
            messages.warning(self.request, f'The record for publication '
                             f'#{paper_data[Fields.PAPER_ID]} by '
                             f'{paper_data[Fields.LAST_NAME]} is missing '
                             f'required information and will not be created.')
            record = None
            created = None

        logger.info(f'record was {record}')
        logger.info(f'created was {created}')

        return record, created

    def form_valid(self, form):
        successes = 0
        updates = []
        unchanged = []

        author_id = form.cleaned_data['author_id']
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
        pub_ids = parse_author_pubs_xml(
            get_paged(f'{author_url}/publications?&detail=full'), author_data)

        for paper in pub_ids:
            paper_id = paper['id']
            logger.info('this paper is %s' % paper_id)

            paper_url = f'{settings.ELEMENTS_ENDPOINT}publications/{paper_id}'
            paper_xml = get_from_elements(paper_url)
            paper_data = parse_paper_xml(paper_xml)
            paper_data.update(author_data)

            journal_url = paper_data["Journal-elements-url"]
            if bool(journal_url):
                policy_xml = get_from_elements(f'{journal_url}/'
                                               f'policies?detail=full')
                policy_data = parse_journal_policies(policy_xml)
                paper_data.update(policy_data)

            if not self._check_data_validity(paper_data):
                continue

            author = self._get_author(paper_data)

            if not author:
                continue

            if not self._check_paper_superfluity(author, paper_data):
                continue

            if not self._check_for_duplicates(author, paper_data):
                continue

            record, created = self._get_record(paper_data, author)

            if not record:
                continue

            if created:
                successes += 1
            else:
                updated = record.update_if_needed(author, paper_data)
                if updated:
                    updates.append(record.paper_id)
                else:
                    unchanged.append(record.paper_id)

        self._add_messages(successes, updates, unchanged)

        return super(Import, self).form_valid(form)

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
