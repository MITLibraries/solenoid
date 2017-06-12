import logging
from string import Template

from django.db import models

from solenoid.emails.models import EmailMessage
from solenoid.people.models import Author

from .helpers import Headers

logger = logging.getLogger(__name__)


class Message(models.Model):
    """The text of special messages associated with publishers.

    This is stored in class instances and not in a helpers file because we are
    getting it from CSV imports. However, we're not just making it a field on
    Record because we expect a great deal of duplication (since special
    messages will likely be the same for all records by a given publisher, at
    least over some period of time)."""
    text = models.TextField()


class Record(models.Model):
    """The Record contains:
        * citation information for an MIT author publication
        * plus all of the other data from Elements we will need to construct an
          email
    This information is extracted from CSV files at time of import (not, e.g.,
    pulled from Elements by API).
    """

    class Meta:
        ordering = ['author__dlc', 'author__last_name']
        # PaperID is not unique, because papers with multiple MIT authors may
        # show up in the CSV multiple times. However, we should only see them
        # once per author.
        unique_together = (('author', 'paper_id'))

    ACQ_MANUSCRIPT = "RECRUIT_FROM_AUTHOR_MANUSCRIPT"
    ACQ_FPV = "RECRUIT_FROM_AUTHOR_FPV_ACCEPTED"
    ACQ_METHODS = (
        (ACQ_MANUSCRIPT, ACQ_MANUSCRIPT),
        (ACQ_FPV, ACQ_FPV),
    )
    ACQ_METHODS_LIST = [tuple[0] for tuple in ACQ_METHODS]

    author = models.ForeignKey(Author)
    email = models.ForeignKey(EmailMessage, blank=True, null=True)
    publisher_name = models.CharField(max_length=50)
    acq_method = models.CharField(choices=ACQ_METHODS, max_length=32)
    citation = models.TextField()
    doi = models.CharField(max_length=30, blank=True)
    paper_id = models.CharField(max_length=10)
    message = models.ForeignKey(Message, blank=True, null=True)
    source = models.CharField(max_length=15)
    elements_id = models.CharField(max_length=50)

    def __str__(self):
        return "{self.author.last_name}, {self.author.first_name} ({self.paper_id})".format( # noqa
            self=self)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ STATIC METHODS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def get_or_create_from_csv(author, row):
        """This expects an author instance and a row of data from a CSV import,
        and returns (record, created), in the manner of objects.get_or_create.
        It does not validate data; you should do that before invoking this.
        If it finds discrepancies between the data it knows about and the
        imported data, it updates the record.
        """
        try:
            record = Record.objects.get(paper_id=row[Headers.PAPER_ID],
                                        author=author)
            """
            if not all([record.author == author,
                        record.publisher_name == row[Headers.PUBLISHER_NAME],
                        record.acq_method == row[Headers.ACQ_METHOD],
                        record.citation == row[Headers.CITATION],
                        record.doi == row[Headers.DOI]]):
                record.update(author=author,
                              publisher_name=row[Headers.PUBLISHER_NAME],
                              acq_method=row[Headers.ACQ_METHOD],
                              citation=row[Headers.CITATION],
                              doi=row[Headers.DOI]
                              )
            """
            logger.info('Got an existing record')
            return record, False
        except Record.DoesNotExist:
            try:
                message = row[Headers.MESSAGE]
            except KeyError:
                message = None
            logger.info('Message text was %s' % message)

            if message:
                try:
                    msg = Message.objects.get(text=message)
                    logger.info('got message %s' % msg)
                except Message.DoesNotExist:
                    msg = Message.objects.create(text=message)
                    msg.save()
                    logger.info('created message %s' % msg)
            else:
                logger.info('no message')
                msg = None

            record = Record.objects.create(
                author=author,
                publisher_name=row[Headers.PUBLISHER_NAME],
                acq_method=row[Headers.ACQ_METHOD],
                citation=row[Headers.CITATION],
                doi=row[Headers.DOI],
                paper_id=row[Headers.PAPER_ID],
                message=msg,
                source=row[Headers.SOURCE],
                elements_id=row[Headers.RECORD_ID])
            logger.info('record created')

            return record, True

    @staticmethod
    def get_duplicates(author, row):
        """See if this CSV row would duplicate a record already in the
        database.

        A _duplicate_ is a record with a different PaperID but the same author
        and citation. We want to reject these so they can be fixed in Elements.

        (Same citation doesn't suffice, as we may legitimately receive a paper
        with the same citation multiple times, once per author.)"""

        dupes = Record.objects.filter(author=author,
                                      citation=row[Headers.CITATION]
                                      ).exclude(paper_id=row[Headers.PAPER_ID])
        if dupes:
            return dupes
        else:
            return None

    @staticmethod
    def is_record_creatable(row):
        """This expects a row of data from a CSV import and determines whether
        a valid record can be created from that data. It is not responsible for
        confirming that the foreign-keyed Author exists or can be created.
        """
        try:
            desiderata = [Headers.PUBLISHER_NAME, Headers.ACQ_METHOD,
                          Headers.CITATION]
            assert all([bool(row[x]) for x in desiderata])

            if row[Headers.ACQ_METHOD] == 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED':
                assert bool(row[Headers.DOI])

            return True
        except AssertionError:
            return False

    @staticmethod
    def is_row_superfluous(row, author):
        """Return True if we have already requested this paper (possibly from
        another author), False otherwise."""

        # Find records of the same paper (whether under the same or  different
        # authors), if any.
        records = Record.objects.filter(
            paper_id=row[Headers.PAPER_ID]
        )

        # Return True if we've already sent an email for any of those papers;
        # False otherwise.
        return any([record.email.date_sent
                    for record in records
                    if record.email])

    @staticmethod
    def is_row_valid(row):
        """Returns True if this row of CSV has the required data for making a
        Record; False otherwise."""
        return all([bool(row[x]) for x in Headers.REQUIRED_DATA])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PROPERTIES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @property
    def fpv_message(self):
        msg = Template('<b>[Note: $publisher_name allows authors to download '
                       'and deposit the final published article, but does not '
                       'allow the Libraries to perform the downloading. If you ' # noqa
                       'follow this link, download the article, and attach it '
                       'to an email reply, we can deposit it on your behalf: '
                       '<a href="https://dx.doi.org.libproxy.mit.edu/$doi">https://dx.doi.org.libproxy.mit.edu/$doi</a>]</b>') # noqa
        if self.acq_method == self.ACQ_FPV:
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
        return all([self.acq_method in self.ACQ_METHODS_LIST,
                    # If acq_method is FPV, we must have the DOI. If not, it
                    # doesn't matter. That's what this truth table says.
                    self.acq_method != Record.ACQ_FPV or bool(self.doi)])
