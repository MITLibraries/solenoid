from unittest.mock import patch

from celery.result import AsyncResult
import pytest
from pytest_django.asserts import assertRedirects, assertTemplateUsed

from django.template.defaultfilters import escape
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from ..models import Record
from ..views import UnsentList

IMPORT_URL = reverse('records:import')


@override_settings(LOGIN_REQUIRED=False)
class UnsentRecordsViewsTest(TestCase):
    fixtures = ['testdata.yaml']

    def setUp(self):
        self.url = reverse('records:unsent_list')

    def test_unsent_records_url_exists(self):
        resolve(self.url)

    def test_unsent_records_view_renders(self):
        c = Client()
        with self.assertTemplateUsed('records/record_list.html'):
            c.get(self.url)

    def test_unsent_records_page_has_all_unsent_in_context(self):
        # assertQuerysetEqual never works, so we're just comparing the pks.
        self.assertEqual(
            set(UnsentList().get_queryset().values_list('pk')),
            set(
                Record.objects.exclude(
                    email__date_sent__isnull=False).distinct().values_list(
                        'pk')
            )
        )

    def test_unsent_records_page_displays_all_unsent(self):
        c = Client()
        response = c.get(self.url)
        for record in Record.objects.exclude(email__date_sent__isnull=False):
            # Note that the citation will be auto-HTML-escaped when rendered,
            # so we need to test for the escaped form, not the database form.
            self.assertContains(response, escape(record.citation))


# Import View Tests
def test_import_records_view_renders(client):
    with assertTemplateUsed('records/import.html'):
        client.get(IMPORT_URL)


@pytest.mark.django_db()
@patch('solenoid.records.tasks.task_import_papers_for_author.delay')
def test_import_form_valid_calls_task_with_correct_args_and_redirects(
    mock_patch, client, mock_elements, test_settings
        ):
    result = AsyncResult('555-444-333')
    mock_patch.return_value = result
    author_url = 'mock://api.com/users/98765'
    author_data = {
            'Email': 'PERSONA@ORG.EDU',
            'First Name': 'Person',
            'Last Name': 'Author',
            'MIT ID': 'MITID',
            'DLC': 'Department Faculty',
            'Start Date': '2011-10-01',
            'End Date': '2020-06-30',
            'ELEMENTS ID': '98765'
        }
    r = client.post(IMPORT_URL, {'author_id': '98765'}, follow=True)
    mock_patch.assert_called_once_with(author_url, author_data, 1)
    assertRedirects(r, reverse('records:status',
                               kwargs={'task_id': '555-444-333'}
                               )
                    )


# Status View Tests
def test_status_view_renders(client):
    with assertTemplateUsed('records/status.html'):
        client.get(reverse('records:status', kwargs={'task_id': '12345'}))
