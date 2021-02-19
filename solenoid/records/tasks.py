from celery import shared_task
from celery.utils.log import get_task_logger
from celery_progress.backend import ProgressRecorder

from django.conf import settings

from solenoid.elements.elements import get_from_elements, get_paged
from solenoid.elements.errors import RetryError
from solenoid.elements.xml_handlers import (
    parse_author_pubs_xml,
    parse_journal_policies,
    parse_paper_xml
    )
from solenoid.people.models import Author

from .helpers import Fields
from .models import Record


logger = get_task_logger(__name__)


@shared_task(bind=True,
             autoretry_for=(RetryError,),
             retry_backoff=True)
def task_import_papers_for_author(self, author_url, author_data, author):
    RESULTS = {}
    logger.info("Import task started")
    if not self.request.called_directly:
        progress_recorder = ProgressRecorder(self)
        progress_recorder.set_progress(0, 0)

    logger.info("Parsing author publications list")
    pub_ids = parse_author_pubs_xml(
        get_paged(f'{author_url}/publications?&detail=full'),
        author_data
        )
    total = len(pub_ids)
    logger.info(f"Finished retrieving publication IDs to import for author.")

    for i, paper in enumerate(pub_ids):
        paper_id = paper['id']
        if not self.request.called_directly:
            progress_recorder.set_progress(
                i, total, description=f'Importing paper #{paper_id} by {author_data[Fields.LAST_NAME]}, {i} of {total}'
                )
        paper_data = _get_paper_data_from_elements(paper_id, author_data)
        author_record = Author.objects.get(pk=author)
        checks = _run_checks_on_paper(paper_data, author_record)
        if checks is not None:
            RESULTS[paper_id] = checks
            continue

        result = _create_or_update_record_from_paper_data(
            paper_data, author_record
            )
        RESULTS[paper_id] = result
        logger.info(f'Finished importing paper #{paper_id}')

    logger.info(f"Import of all papers by author "
                f"{author_data['ELEMENTS ID']} completed")
    return RESULTS


def _create_or_update_record_from_paper_data(paper_data, author):
    paper_id = paper_data[Fields.PAPER_ID]
    author_name = paper_data[Fields.LAST_NAME]

    if Record.is_record_creatable(paper_data):
        record, created = Record.get_or_create_from_data(author, paper_data)
        if created:
            logger.info(f'Record {record} was created from paper {paper_id}')
            return 'Paper was successfully imported.'
        else:
            updated = record.update_if_needed(author, paper_data)
            if updated:
                return 'Record updated with new data from Elements.'
            else:
                return 'Paper already in database, no updates made.'

    logger.warning(f'Cannot create record for paper {paper_id} '
                   f'with author {author_name}')
    return ('Paper could not be added to the database. Please make '
            'sure data is correct in Elements and try again.')


def _get_paper_data_from_elements(paper_id, author_data):
    logger.info(f'Importing data for paper {paper_id}')

    paper_url = f'{settings.ELEMENTS_ENDPOINT}publications/{paper_id}'
    paper_xml = get_from_elements(paper_url)
    paper_data = parse_paper_xml(paper_xml)
    paper_data.update(author_data)

    journal_url = paper_data["Journal-elements-url"]
    if bool(journal_url):
        policy_xml = get_from_elements(
            f'{journal_url}/policies?detail=full'
            )
        policy_data = parse_journal_policies(policy_xml)
        paper_data.update(policy_data)

    return paper_data


def _run_checks_on_paper(paper_data, author):
    paper_id = paper_data[Fields.PAPER_ID]
    author_name = paper_data[Fields.LAST_NAME]

    # Check that data provided from Elements is complete
    if not Record.is_data_valid(paper_data):
        logger.info(f'Invalid data for paper {paper_id}')
        return (f'Publication #{paper_id} by '
                f'{author_name} is missing required data '
                f'(one or more of {", ".join(Fields.REQUIRED_DATA)}), so '
                f'this citation will not be imported.')

    # Check that paper hasn't already been requested
    if Record.paper_requested(paper_data):
        logger.info(f'Paper {paper_id} already requested, '
                    f'record not imported')
        return (f'Publication #{paper_id} by '
                f'{author_name} has already been requested '
                f'(possibly from another author), so this record will not '
                f'be imported. Please add this citation manually to an '
                f'email, and manually mark it as requested in Symplectic, '
                'if you would like to request it from this author also.')

    # Check that paper doesn't already exist in database
    dupes = Record.get_duplicates(author, paper_data)
    if dupes:
        dupe_list = [id for id in dupes.values_list('paper_id', flat=True)]
        logger.info(f'Duplicates of paper {paper_id}: {dupes}')
        return (f'Publication #{paper_id} by {author_name} duplicates the '
                f'following record(s) already in the database: '
                f'{", ".join(dupe_list)}. Please merge #{paper_id} into an '
                f'existing record in Elements. It will not be imported.')
