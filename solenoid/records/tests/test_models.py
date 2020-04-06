import copy
from datetime import date
from string import Template

from django.core.exceptions import ValidationError
from django.test import TestCase
from solenoid.people.models import DLC, Author

from ..helpers import Fields
from ..models import Record


class RecordModelTest(TestCase):
    fixtures = ['testdata.yaml']

    def setUp(self):
        # A dict containing all the EXPECTED_FIELDS.
        self.paper_data = {
            Fields.EMAIL: 'test@example.com',
            Fields.DOI: '10.5137/527va',
            Fields.FIRST_NAME: 'William Barton',
            Fields.LAST_NAME: 'Rogers',
            Fields.MIT_ID: '1',
            Fields.PUBLISHER_NAME: 'Haus of Books',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.DLC: "President's Office",
            Fields.PAPER_ID: '895327',
            Fields.MESSAGE: '',
        }

        # MIT physics professor Frank Wilczek coauthored this paper, for which
        # he won the Nobel prize in 2004.
        self.citation_data = {
            Fields.FIRST_NAME: 'Frank',
            Fields.LAST_NAME: 'Wilczek',
            Fields.PUBDATE: '19730625',
            Fields.VOLUME: '30',
            Fields.ISSUE: '26',
            Fields.DOI: '10.1103/PhysRevLett.30.1343',
            Fields.JOURNAL: 'Physical Review Letters',
            Fields.TITLE: 'Ultraviolet behavior of non-abelian gauge theories'
        }

    # need to actually test create_citation
    def test_is_metadata_valid_yes_citation_no_citation_data(self):
        metadata = copy.copy(self.paper_data)
        metadata[Fields.CITATION] = 'This is a citation'
        metadata[Fields.TITLE] = None
        metadata[Fields.JOURNAL] = None
        assert Record.is_data_valid(metadata)

    def test_is_metadata_valid_no_citation_yes_citation_data(self):
        metadata = copy.copy(self.paper_data)
        metadata[Fields.CITATION] = None
        metadata[Fields.TITLE] = 'This is a paper title'
        metadata[Fields.JOURNAL] = 'Journal of Awesomeness'
        assert Record.is_data_valid(metadata)

    def test_is_metadata_valid_no_citation_no_citation_data(self):
        metadata = copy.copy(self.paper_data)
        metadata[Fields.CITATION] = None
        metadata[Fields.TITLE] = None
        metadata[Fields.JOURNAL] = None
        assert not Record.is_data_valid(metadata)

    def test_is_record_creatable(self):
        # Data includes the basics? Good!
        data = {
            Fields.PUBLISHER_NAME: 'foo',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_MANUSCRIPT',
            Fields.CITATION: 'nonempty'
        }
        assert Record.is_record_creatable(data)

        data = {
            Fields.PUBLISHER_NAME: 'foo',
            Fields.ACQ_METHOD: '',
            Fields.CITATION: 'nonempty'
        }
        assert Record.is_record_creatable(data)

        # Missing data for required basics? Bad!
        data = copy.copy(self.paper_data)
        data.update(self.citation_data)
        data[Fields.CITATION] = ''
        data[Fields.FIRST_NAME] = ''
        assert not Record.is_record_creatable(data)

        data = {
            Fields.PUBLISHER_NAME: 'foo',
            # No acq method column at all
            Fields.CITATION: 'nonempty'
        }
        assert not Record.is_record_creatable(data)

        # RECRUIT_FROM_AUTHOR_FPV requires a DOI.
        data = {
            Fields.PUBLISHER_NAME: 'foo',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'nonempty',
            Fields.DOI: ''
        }
        assert not Record.is_record_creatable(data)

        data = {
            Fields.PUBLISHER_NAME: 'foo',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'nonempty',
            Fields.DOI: '4217896'
        }
        assert Record.is_record_creatable(data)

    def test_is_valid_fpv_but_no_doi(self):
        record = Record.objects.get(pk=1)
        # RECRUIT_FROM_AUTHOR_FPV and no DOI: invalid
        record.acq_method = 'RECRUIT_FROM_AUTHOR_FPV'
        record.doi = ''
        record.save()
        assert not record.is_valid

    def test_is_valid_fpv_but_has_doi(self):
        record = Record.objects.get(pk=1)
        # RECRUIT_FROM_AUTHOR_FPV and yes DOI: valid
        record.doi = '53297853'
        record.save()
        assert record.is_valid

    def test_is_valid_not_fpv_and_no_doi(self):
        record = Record.objects.get(pk=1)
        # RECRUIT_FROM_AUTHOR_MANUSCRIPT and no DOI: valid
        record.acq_method = 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'
        record.doi = ''
        record.save()
        assert record.is_valid

    def test_is_valid_not_fpv_and_not_doi(self):
        record = Record.objects.get(pk=1)
        # RECRUIT_FROM_AUTHOR_MANUSCRIPT and yes DOI: valid
        record.doi = '53297853'
        record.save()
        assert record.is_valid

    def test_is_valid_no_citation(self):
        record = Record.objects.get(pk=1)
        record.citation = None
        with self.assertRaises(ValidationError):
            record.save()

    def test_is_valid_blank_citation(self):
        record = Record.objects.get(pk=1)
        record.citation = ''
        with self.assertRaises(ValidationError):
            record.save()

    def test_is_sent(self):
        # Record with an email that hasn't been sent
        record = Record.objects.get(pk=1)
        email = record.email
        email.date_sent = None
        email.save()
        assert not record.is_sent

        # Record with an email that has been sent
        email.date_sent = date.today()
        email.save()
        assert record.is_sent

        # Record with no email
        record = Record.objects.get(pk=2)
        assert not record.is_sent

    def test_fpv_message(self):
        record = Record.objects.get(pk=1)
        record.acq_method = 'not fpv'
        record.save()

        assert record.fpv_message is None

        fake_doi = 'fake_doi'
        publisher_name = 'fake_publisher'
        record.acq_method = 'RECRUIT_FROM_AUTHOR_FPV'
        record.doi = fake_doi
        record.publisher_name = publisher_name
        record.save()

        msg = Template('<b>[Note: $publisher_name allows authors to download '
                       'and deposit the final published article, but does not '
                       'allow the Libraries to perform the downloading. If you ' # noqa
                       'follow this link, download the article, and attach it '
                       'to an email reply, we can deposit it on your behalf: '
                       '<a href="http://libproxy.mit.edu/login?url=https://dx.doi.org/$doi">http://libproxy.mit.edu/login?url=https://dx.doi.org/$doi</a>]</b>')  # noqa

        assert record.fpv_message == msg.substitute(
            publisher_name=publisher_name, doi=fake_doi)

    def test_get_or_create_from_data(self):
        author = Author.objects.get(pk=1)
        record, created = Record.get_or_create_from_data(
            author, {Fields.PAPER_ID: 1})
        assert record.pk == 1
        assert not created

        row = {
            Fields.PUBLISHER_NAME: 'publisher_name',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'citation',
            Fields.DOI: 'doi',
            Fields.PAPER_ID: 'paper_id',
            Fields.MESSAGE: ''
        }

        record, created = Record.get_or_create_from_data(author, row)
        assert created
        assert record.publisher_name == 'publisher_name'
        assert record.acq_method == 'RECRUIT_FROM_AUTHOR_FPV'
        assert record.citation == 'citation'
        assert record.doi == 'doi'
        assert record.paper_id == 'paper_id'
        assert record.message == ''

    def test_get_duplicates_1(self):
        """There are no duplicates: this should return None."""

        metadata = {
            Fields.PUBLISHER_NAME: 'publisher_name',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'citation',
            Fields.DOI: 'doi',
            Fields.PAPER_ID: 'paper_id',
        }
        author = Author.objects.get(pk=1)

        assert Record.get_duplicates(author, metadata) is None

    def test_get_duplicates_2(self):
        """There's a paper with the same citation but a different author;
        this should return None."""

        metadata = {
            Fields.PUBLISHER_NAME: 'Wiley',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'Fermi, Enrico. Paper name. Some journal or other. 145:5 (2016)',  # noqa
            Fields.DOI: '10.1412/4678156',
            Fields.PAPER_ID: 'paper_id',
            Fields.FIRST_NAME: 'Different',
            Fields.LAST_NAME: 'Author',
            Fields.MIT_ID: 214614,
        }

        # Check assumption - we don't have this author in the db at all, so
        # we can't have a record associated with this author yet
        id_hash = Author.get_hash('214614')
        assert not Author.objects.filter(_mit_id_hash=id_hash)

        author = Author.objects.create(
            first_name='Different',
            last_name='Author',
            _mit_id_hash=id_hash,
            dlc=DLC.objects.first(),
            email='da@example.com'
        )

        assert Record.get_duplicates(author, metadata) is None

    def test_get_duplicates_3(self):
        """There's a paper with the same citation, the same author, and a
        different paper_id; this should return that duplicate."""
        # Check assumption
        assert not Record.objects.filter(paper_id=24618)

        # This is a duplicate of record #2, except for the paper ID.
        metadata = {
            Fields.PUBLISHER_NAME: 'Nature',
            Fields.ACQ_METHOD: 'RECRUIT_FROM_AUTHOR_FPV',
            Fields.CITATION: 'Tonegawa, Susumu. Paper name. Some journal or other. 31:4 (2012)',  # noqa
            Fields.DOI: '10.1240.2/4914241',
            Fields.PAPER_ID: '24618',
            Fields.FIRST_NAME: 'Susumu',
            Fields.LAST_NAME: 'Tonegawa',
            Fields.MIT_ID: '2',
        }
        author = Author.objects.get(last_name='Tonegawa')

        dupes = Record.get_duplicates(author, metadata)
        assert dupes.count() == 1
        assert int(dupes[0].paper_id) == 123141

    def test_create_citation_case_1(self):
        """Minimal citation plus:
        publication date: YES
        volume & issue: NO
        doi: NO """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.VOLUME,
                                   Fields.ISSUE,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. (1973). Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_create_citation_case_2(self):
        """Minimal citation plus:
        publication date: YES
        volume & issue: YES
        doi: NO """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. (1973). Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters, 30(26).'  # noqa
        )

    def test_create_citation_case_3(self):
        """Minimal citation plus:
        publication date: YES
        volume & issue: NO
        doi: YES """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.VOLUME,
                                   Fields.ISSUE],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. (1973). Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters. doi:10.1103/PhysRevLett.30.1343'  # noqa
        )

    def test_create_citation_case_4(self):
        """Minimal citation plus:
        publication date: YES
        volume & issue: YES
        doi: YES """
        citation = Record.create_citation(self.citation_data)
        self.assertEqual(citation,
            'Wilczek, F. (1973). Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters, 30(26). doi:10.1103/PhysRevLett.30.1343'  # noqa
        )

    def test_create_citation_case_5(self):
        """Minimal citation plus:
        publication date: NO
        volume & issue: NO
        doi: NO """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.VOLUME,
                                   Fields.ISSUE,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_create_citation_case_6(self):
        """Minimal citation plus:
        publication date: NO
        volume & issue: YES
        doi: NO """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters, 30(26).'  # noqa
        )

    def test_create_citation_case_7(self):
        """Minimal citation plus:
        publication date: NO
        volume & issue: NO
        doi: YES """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.VOLUME,
                                   Fields.ISSUE],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters. doi:10.1103/PhysRevLett.30.1343'  # noqa
        )

    def test_create_citation_case_8(self):
        """Minimal citation plus:
        publication date: NO
        volume & issue: YES
        doi: YES """
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters, 30(26). doi:10.1103/PhysRevLett.30.1343'  # noqa
        )

    def test_create_citation_error_case_1(self):
        """Minimal citation; has volume, lacks issue."""
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.ISSUE,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_create_citation_error_case_2(self):
        """Minimal citation; has issue, lacks volume."""
        data = copy.copy(self.citation_data)
        data.update(dict.fromkeys([Fields.PUBDATE,
                                   Fields.VOLUME,
                                   Fields.DOI],
                    None))
        citation = Record.create_citation(data)
        self.assertEqual(citation,
            'Wilczek, F. Ultraviolet behavior of non-abelian gauge theories. Physical Review Letters.'  # noqa
        )

    def test_update_if_needed_case_1(self):
        """update_if_needed alters the record when it sees a new author."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.CITATION] = r1.citation
        author = Author.objects.get(pk=2)  # not the author of r1
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.author == author

    def test_update_if_needed_case_2(self):
        """update_if_needed alters the record when it sees a new publisher."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        new_publisher = r1.publisher_name + 'new'
        metadata[Fields.PUBLISHER_NAME] = new_publisher
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.CITATION] = r1.citation
        author = r1.author
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.publisher_name == new_publisher

    def test_update_if_needed_case_3(self):
        """update_if_needed alters the record when it sees a new acquisition
        method."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.CITATION] = r1.citation
        author = r1.author
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.acq_method == 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'

    def test_update_if_needed_case_4(self):
        """update_if_needed alters the record when it sees a new DOI."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        new_doi = r1.doi + 'new'
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = new_doi
        metadata[Fields.CITATION] = r1.citation
        author = r1.author
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.doi == new_doi

    def test_update_if_needed_case_5(self):
        """update_if_needed alters the record when it sees a new citation
        that is not blank."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        new_citation = r1.citation + 'new'
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.CITATION] = new_citation
        author = r1.author
        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.citation == new_citation

    def test_update_if_needed_case_6(self):
        """update_if_needed does NOT alter the record if nothing has
        changed."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.LAST_NAME] = 'Fermi'
        metadata[Fields.FIRST_NAME] = 'Enrico'
        metadata[Fields.PUBDATE] = '20160815'
        metadata[Fields.TITLE] = 'Paper name'
        metadata[Fields.JOURNAL] = 'Some journal or other'
        metadata[Fields.VOLUME] = '145'
        metadata[Fields.ISSUE] = '5'
        author = r1.author

        # Ensure that the citation will not have changed
        r1.citation = Record.create_citation(metadata)
        r1.save()
        metadata[Fields.CITATION] = r1.citation

        assert not r1.update_if_needed(author, metadata)

    def test_update_if_needed_case_7(self):
        """update_if_needed does alter the record if the citation is blank,
        but other data from which we would generate a citation leads to a
        different citation than the currently existing one."""
        r1 = Record.objects.get(pk=1)
        metadata = {}
        metadata[Fields.PUBLISHER_NAME] = r1.publisher_name
        metadata[Fields.ACQ_METHOD] = r1.acq_method
        metadata[Fields.DOI] = r1.doi
        metadata[Fields.LAST_NAME] = 'Fermi'
        metadata[Fields.FIRST_NAME] = 'Enrico'
        metadata[Fields.PUBDATE] = '20160815'
        metadata[Fields.TITLE] = 'Paper name'
        metadata[Fields.JOURNAL] = 'Some journal or other'
        metadata[Fields.VOLUME] = '145'
        metadata[Fields.ISSUE] = '5'
        metadata[Fields.CITATION] = ''
        author = r1.author

        assert r1.citation != Record.create_citation(metadata)  # check assumption

        assert r1.update_if_needed(author, metadata)
        r1.refresh_from_db()
        assert r1.citation == Record.create_citation(metadata)
