from datetime import date
import logging
from string import Template

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from solenoid.emails.models import EmailMessage
from solenoid.people.models import Author

from .helpers import Headers

logger = logging.getLogger(__name__)


class Record(models.Model):
    """The Record contains:
        * citation information for an MIT author publication
        * plus all of the other data from Elements we will need to construct an
          email
        * plus any local recordkeeping we are doing about status (i.e. have we
          already solicited the author for this citation)."""

    class Meta:
        ordering = ['author__dlc', 'author__last_name']

    ACQ_MANUSCRIPT = "RECRUIT_FROM_AUTHOR_MANUSCRIPT"
    ACQ_FPV = "RECRUIT_FROM_AUTHOR_FPV_ACCEPTED"
    ACQ_METHODS = (
        (ACQ_MANUSCRIPT, ACQ_MANUSCRIPT),
        (ACQ_FPV, ACQ_FPV),
    )
    ACQ_METHODS_LIST = [tuple[0] for tuple in ACQ_METHODS]

    UNSENT = 'Unsent'
    SENT = 'Sent'
    INVALID = 'Invalid'
    STATUS_CHOICES = (
        (UNSENT, UNSENT),
        (SENT, SENT),
        (INVALID, INVALID),
    )
    STATUS_CHOICES_LIST = [tuple[0] for tuple in STATUS_CHOICES]

    author = models.ForeignKey(Author)
    email = models.ForeignKey(EmailMessage, blank=True, null=True)
    publisher_name = models.CharField(max_length=50)
    acq_method = models.CharField(choices=ACQ_METHODS, max_length=32)
    citation = models.TextField()
    status = models.CharField(default=UNSENT,
        choices=STATUS_CHOICES, max_length=7)
    status_timestamp = models.DateField(default=date.today)
    doi = models.CharField(max_length=30, blank=True)
    paper_id = models.CharField(max_length=10)

    def save(self, *args, **kwargs):
        if not self.is_valid:
            self.status = Record.INVALID
        return super(Record, self).save(*args, **kwargs)

    def __str__(self):
        return "{self.author.last_name}, {self.author.first_name} ({self.paper_id})".format( # noqa
            self=self)

    @property
    def is_valid(self):
        return all([self.acq_method in self.ACQ_METHODS_LIST,
                    # If acq_method is FPV, we must have the DOI. If not, it
                    # doesn't matter. That's what this truth table says.
                    self.acq_method != Record.ACQ_FPV or bool(self.doi)])

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

    @property
    def is_sendable(self):
        """We define this here to avoid circular imports in
        solenoid.emails.models, where EmailMessage needs to check whether the
        record has been sent."""
        return self.status == self.UNSENT

    @staticmethod
    def get_or_create_from_csv(author, row):
        """This expects an author instance and a row of data from a CSV import,
        and returns (record, created), in the manner of objects.get_or_create.
        It does not validate data; you should do that before invoking this.
        """
        try:
            record = Record.objects.get(paper_id=row[Headers.PAPER_ID])
            if record.status == Record.INVALID:
                record.author = author
                record.publisher_name = row[Headers.PUBLISHER_NAME]
                record.acq_method = row[Headers.ACQ_METHOD]
                record.citation = row[Headers.CITATION]
                record.doi = row[Headers.DOI]

                # save() will validate the record and set this back to INVALID
                # if needed.
                record.status = Record.UNSENT
                record.save()
            return record, False
        except Record.DoesNotExist:
            return Record.objects.create(
                author=author,
                publisher_name=row[Headers.PUBLISHER_NAME],
                acq_method=row[Headers.ACQ_METHOD],
                citation=row[Headers.CITATION],
                doi=row[Headers.DOI],
                paper_id=row[Headers.PAPER_ID]), True


@receiver(pre_save, sender=Record)
def verify_status(sender, instance, **kwargs):
    """Make sure that any status changes are valid. If so, update the
    status_timestamp."""
    if instance.status not in instance.STATUS_CHOICES_LIST:
        logger.warning("Attempt to set an unrecognized record status "
            "{value}".format(value=instance.status))
        raise ValueError("{value} is not a permissible status".format(
            value=instance.status))
    # There are (from, to) tuples representing invalid status transitions
    # (e.g. you may not go from SENT to UNSENT).
    invalid_changes = [(Record.SENT, Record.UNSENT),
                       (Record.SENT, Record.INVALID)]

    try:
        original = Record.objects.get(pk=instance.pk)
    except Record.DoesNotExist:
        pass
    else:
        if not original.status == instance.status:
            if (original.status, instance.status) in invalid_changes:
                logger.warning("Tried to make an invalid status change from "
                    "{x} to {y}".format(x=original.status, y=instance.status))
                raise ValueError("That status change is not allowed.")
            else:
                instance.status_timestamp = date.today()
