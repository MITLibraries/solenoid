from django.db.models.signals import post_save
from django.db import models
from django.dispatch import receiver

from solenoid.emails.models import EmailMessage

from .models import DLC, Liaison


def update_emails_with_dlcs(
    dlcs: models.QuerySet | list, liaison: Liaison | None = None
) -> None:
    """
    For a given liaison and set of DLCs, update all unsent EmailMessages
    associated with those DLCs to have that Liaison.

    We can't make this part of, e.g., the save() method on DLC, because the
    liaison.dlc_set.update() commands used in views.py go straight to SQL,
    bypassing the ORM - save() doesn't get hit, and neither do pre/post-save
    signals. Therefore we make it a standalone function, so it can be used in
    cases where save() is unavailable, but also connect it to the post_save
    signal.
    """
    for dlc in dlcs:
        EmailMessage.objects.filter(
            record__author__dlc=dlc, date_sent__isnull=True
        ).update(_liaison=liaison)


@receiver(post_save, sender=DLC)
def update_emails_with_dlcs_on_save(sender: models.Model, **kwargs) -> None:  # type: ignore[no-untyped-def]
    dlc = kwargs["instance"]
    update_emails_with_dlcs([dlc], dlc.liaison)
