from datetime import date
import logging

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from solenoid.people.models import Author

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
    publisher_name = models.CharField(max_length=50)
    acq_method = models.CharField(choices=ACQ_METHODS, max_length=32)
    citation = models.TextField()
    status = models.CharField(default=UNSENT,
        choices=STATUS_CHOICES, max_length=7)
    status_timestamp = models.DateField(default=date.today)
    paper_id = models.CharField(max_length=10, help_text="This is the "
        "Publication ID field from Elements; it is supposed to be unique but "
        "we will not be relying on it as a primary key here.")

    # # I don't need ANY of these if I can get full citation.
    # title = models.TextField()
    # journal = models.TextField()
    # # In theory the following fields should be integers, but in practice,
    # # let's not trust unfamiliar metadata
    # volume = models.CharField(max_length=6, blank=True, null=True)
    # issue = models.CharField(max_length=3, blank=True, null=True)
    # year_published = models.DateField()

    def save(self, *args, **kwargs):
        if self.acq_method not in self.ACQ_METHODS_LIST:
            self.status = self.INVALID
        return super(Record, self).save(*args, **kwargs)

    def __str__(self):
        return "{self.last_name}, {self.first_name} ({self.paper_id})".format(
            self=self)


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
                logger.warning("Attempt make an invalid status change from "
                    "{x} to {y}".format(x=original.status, y=instance.status))
                raise ValueError("That status change is not allowed.")
            else:
                instance.status_timestamp = date.today()
