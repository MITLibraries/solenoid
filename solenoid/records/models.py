from datetime import date
import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save

logger = logging.getLogger(__name__)

class Record(models.Model):
    """The Record contains:
        * citation information for an MIT author publication
        * plus all of the other data from Elements we will need to construct an
          email
        * plus any local recordkeeping we are doing about status (i.e. have we
          already solicited the author for this citation)."""

    class Meta:
        ordering = ['dlc', 'last_name']

    ACQ_METHODS = (
        (0, 'RECRUIT_FROM_AUTHOR_MANUSCRIPT')
        #(1, FPV)
    )

    UNSENT = 'Unsent'
    SENT = 'Sent'
    INVALID = 'Invalid'
    STATUS_CHOICES = (
        (0, UNSENT),
        (1, SENT),
        (2, INVALID),
    )

    dlc = models.CharField(max_length=100)
    email = models.EmailField(help_text="Author email address")
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=40)
    publisher_name = models.CharField(max_length=50)
    acq_method = models.IntegerField(choices=ACQ_METHODS)
    citation = models.TextField()
    status = models.IntegerField(default=0, choices=STATUS_CHOICES)
    status_timestamp = models.DateField(default=date.today)
    paper_id = models.CharField(max_length=10, help_text="This is the " \
        "Publication ID field from Elements; it is supposed to be unique but " \
        "we will not be relying on it as a primary key here.")

    ## I don't need ANY of these if I can get full citation.
    #title = models.TextField()
    #journal = models.TextField()
    ## In theory the following fields should be integers, but in practice, let's
    ## not trust unfamiliar metadata
    #volume = models.CharField(max_length=6, blank=True, null=True)
    #issue = models.CharField(max_length=3, blank=True, null=True)
    #year_published = models.DateField()


@receiver(pre_save, sender=Record)
def verify_status(sender, instance, **kwargs):
    """Make sure that any status changes are valid. If so, update the
    status_timestamp."""
    # There are (from, to) tuples representing invalid status transitions
    # (e.g. you may not go from SENT to UNSENT).
    invalid_changes = ((1, 0), (1, 2))

    try:
        original = Record.objects.get(pk=instance.pk)
    except Record.DoesNotExist:
        pass
    else:
        if not original.status == instance.status:
            if (original.status, instance.status) in invalid_changes:
                logger.warning("Attempt make an invalid status change from " \
                    "{x} to {y}".format(x=original.status, y=instance.status))
                raise ValidationError("That status change is not allowed.")
            else:
                instance.status_timestamp = date.today()
