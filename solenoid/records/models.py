import logging
from string import Template

from django.core.exceptions import ValidationError
from django.db import models
from solenoid.emails.models import EmailMessage
from solenoid.people.models import Author

from .helpers import Fields

logger = logging.getLogger(__name__)


class Record(models.Model):
    """The Record contains:
        * citation information for an MIT author publication
        * plus all of the other data from Elements we will need to construct an
          email
    """

    class Meta:
        ordering = ['author__dlc', 'author__last_name']
        # PaperID is not unique, because papers with multiple MIT authors may
        # show up in data imports multiple times. However, we should only see
        # them once per author.
        unique_together = (('author', 'paper_id'))

    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE)
    email = models.ForeignKey(
        EmailMessage,
        blank=True,
        null=True,
        on_delete=models.CASCADE)
    publisher_name = models.CharField(max_length=255)
    acq_method = models.CharField(
        max_length=255,
        blank=True)
    citation = models.TextField()
    doi = models.CharField(max_length=255, blank=True)
    # This is the unique ID within Elements, which is NOT the same as the
    # proprietary data source ID - those are unique IDs within Scopus, Web of
    # Science, etc. We may have multiple records with the same paper ID
    # because there will be one record per author (hence the unique_together
    # constraint). The unique ID on pubdata-dev does not match that on the
    # production server.
    paper_id = models.CharField(max_length=255)
    message = models.TextField(blank=True)

    def __str__(self):
        return ("{self.author.last_name}, {self.author.first_name} "
                "({self.paper_id})".format(self=self))

    def save(self, *args, **kwargs):
        # blank=False by default in TextFields, but this applies only to *form*
        # validation, not to *instance* validation - django will happily save
        # blank strings to the database, and we don't want it to.
        if not self.citation:
            raise ValidationError('Citation cannot be blank')
        return super(Record, self).save(*args, **kwargs)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ STATIC METHODS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def create_citation(paper_data):
        """Create text suitable for the citation field.

        Some Elements papers include the citation field in their metadata,
        but some leave it blank; in those cases we need to build our own
        citation text. Stakeholders have indicated that it doesn't matter what
        citation format we use or whether the citation is complete (as long as
        it includes author, title, and journal title).

        This method assumes that the supplied paper metadata has already been
        validated; it does not perform any validation.

        APA format is:
            Author, F.M. (Publication year). Article Title. Journal Title,
            Volume(Issue), pp.-pp. doi:XX.XXXXX.
        We don't appear to get page number information, so we'll skip that.
        """
        citation = '{last}, {first_init}. '.format(
            last=paper_data[Fields.LAST_NAME],
            first_init=paper_data[Fields.FIRST_NAME][0])

        if paper_data[Fields.PUBDATE]:
            citation += f'({paper_data[Fields.PUBDATE][0:4]}). '

        citation += '{title}. {journal}'.format(
            title=paper_data[Fields.TITLE],
            journal=paper_data[Fields.JOURNAL])

        if paper_data[Fields.VOLUME] and paper_data[Fields.ISSUE]:
            citation += ', {volume}({issue})'.format(
                volume=paper_data[Fields.VOLUME],
                issue=paper_data[Fields.ISSUE])

        citation += '.'

        if paper_data[Fields.DOI]:
            citation += (' <a href="https://doi.org/{doi}">doi:{doi}'
                         '</a>'.format(doi=paper_data[Fields.DOI]))
        return citation

    @staticmethod
    def _get_citation(paper_data):
        if paper_data[Fields.CITATION]:
            citation = paper_data[Fields.CITATION]
        else:
            citation = Record.create_citation(paper_data)

        return citation

    @staticmethod
    def get_or_create_from_data(author, paper_data):
        """This expects an author instance and metadata about a single paper
        (retrieved via the Elements API), and returns (record, created),
        in the manner of objects.get_or_create. It does not validate data;
        you should do that before invoking this. If it finds discrepancies
        between the data it knows about and the imported data, it updates
        the record.
        """
        try:
            record = Record.objects.get(paper_id=paper_data[Fields.PAPER_ID],
                                        author=author)
            logger.info('Got an existing record')
            return record, False
        except Record.DoesNotExist:
            citation = Record._get_citation(paper_data)

            record = Record.objects.create(
                author=author,
                publisher_name=paper_data[Fields.PUBLISHER_NAME],
                acq_method=paper_data[Fields.ACQ_METHOD],
                citation=citation,
                doi=paper_data[Fields.DOI],
                paper_id=paper_data[Fields.PAPER_ID],
                message=paper_data[Fields.MESSAGE])
            logger.info('record created')

            return record, True

    @staticmethod
    def get_duplicates(author, paper_data):
        """See if this paper's metadata would duplicate a record already in the
        database.

        A _duplicate_ is a record with a different PaperID but the same author
        and citation. We want to reject these so they can be fixed in Elements.

        (Same citation doesn't suffice, as we may legitimately receive a paper
        with the same citation multiple times, once per author.)"""

        dupes = Record.objects.filter(author=author,
                                      citation=paper_data[Fields.CITATION]
                                      ).exclude(
                                          paper_id=paper_data[Fields.PAPER_ID])
        if dupes:
            return dupes
        else:
            return None

    @staticmethod
    def is_record_creatable(paper_data):
        """Determines whether a valid Record can be created from supplied data.

        Args:
            paper_data (dict): A dict of metadata fields about a single paper.
        Returns:
            bool: True if record can be created, False otherwise.
        """
        try:
            if paper_data[Fields.ACQ_METHOD] == 'RECRUIT_FROM_AUTHOR_FPV':
                assert bool(paper_data[Fields.DOI])
                assert bool(paper_data[Fields.PUBLISHER_NAME])

            if not paper_data[Fields.CITATION]:
                assert all([bool(paper_data[x]) for x in Fields.CITATION_DATA])

            return True
        except (AssertionError, KeyError):
            return False

    @staticmethod
    def paper_requested(paper_data):
        """Checks whether we have already sent an email request for this paper.

        Args:
            paper_data (dict:[str, str]): A dict of metadata fields about a
                single paper.

        Returns:
            bool: True if we've already requested this paper (from any author),
                False otherwise.
        """

        # Find all records of the same paper, if any.
        records = Record.objects.filter(
            paper_id=paper_data[Fields.PAPER_ID]
        )

        # Return True if we've already sent an email for any of those records;
        # False otherwise.
        return any([record.email.date_sent
                    for record in records
                    if record.email])

    @staticmethod
    def is_data_valid(paper_data):
        """Returns True if this metadata has the required data fields for
        making a Record; False otherwise.

        For citation data, we'll accept *either* a preconstructed citation,
        *or* enough data to construct a minimal citation ourselves."""
        citable = bool(paper_data[Fields.CITATION]) or \
            all([bool(paper_data[x]) for x in Fields.CITATION_DATA])
        return (all([bool(paper_data[x]) for x in Fields.REQUIRED_DATA]) and
                citable)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~ INSTANCE METHODS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def update_if_needed(self, author, paper_data):
        """Checks a paper's supplied metadata to see if there are any
        discrepancies with the existing record. If so, updates it and returns
        True. If not, returns False."""
        changed = False
        if not all([self.author == author,
                    self.publisher_name == paper_data[Fields.PUBLISHER_NAME],
                    self.acq_method == paper_data[Fields.ACQ_METHOD],
                    self.doi == paper_data[Fields.DOI]]):
            self.author = author
            self.publisher_name = paper_data[Fields.PUBLISHER_NAME]
            self.acq_method = paper_data[Fields.ACQ_METHOD]
            self.doi = paper_data[Fields.DOI]
            changed = True

        # Don't update records with blank citation information - that will
        # cause ValidationErrors. Instead, update them with nonblank info, or
        # check if updates to other info merit an update to the citation if the
        # citation is blank.
        if paper_data[Fields.CITATION]:
            if self.citation != paper_data[Fields.CITATION]:
                self.citation = paper_data[Fields.CITATION]
                changed = True
        else:
            new_cite = Record.create_citation(paper_data)
            if self.citation != new_cite:
                self.citation = new_cite
                changed = True

        if changed:
            self.save()
            return True
        return False

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PROPERTIES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @property
    def fpv_message(self):
        msg = Template('<b>[Note: $publisher_name allows authors to download '
                       'and deposit the final published article, but does not '
                       'allow the Libraries to perform the downloading. If '
                       'you follow this link, download the article, and '
                       'attach it to an email reply, we can deposit it on '
                       'your behalf: <a href="http://libproxy.mit.edu/'
                       'login?url=https://dx.doi.org/$doi">http://'
                       'libproxy.mit.edu/login?url=https://dx.doi.org/'
                       '$doi</a>]</b>')
        if self.acq_method == 'RECRUIT_FROM_AUTHOR_FPV':
            return msg.substitute(publisher_name=self.publisher_name,
                                  doi=self.doi)
        else:
            return None

    @property
    def is_sent(self):
        if self.email:
            return bool(self.email.date_sent)
        else:
            return False

    @property
    def is_valid(self):
        # If acq_method is FPV, we must have the DOI.
        return (self.acq_method != 'RECRUIT_FROM_AUTHOR_FPV' or bool(self.doi))
