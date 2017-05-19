import hashlib

from django.db import models
from django.db.models.signals import pre_delete
from django.db import IntegrityError
from django.dispatch import receiver

from solenoid.records.helpers import Headers


class ActiveLiaisonManager(models.Manager):
    def get_queryset(self):
        return super(ActiveLiaisonManager, self).get_queryset().filter(
            active=True)


class Liaison(models.Model):

    class Meta:
        verbose_name = "Liaison"
        verbose_name_plural = "Liaisons"

    def __str__(self):
        return "{self.first_name} {self.last_name}".format(self=self)

    first_name = models.CharField(max_length=15)
    last_name = models.CharField(max_length=30)
    email_address = models.EmailField()
    # We don't actually want to delete Liaisons who have associated emails.
    # Instead, we create a custom manager to only show active Liaisons.
    active = models.BooleanField(default=True)

    objects_all = models.Manager()  # The default manager.
    objects = ActiveLiaisonManager()  # Our standard manager.

    def save(self, *args, **kwargs):
        if not self.active:
            self.dlc_set.clear()

        return super(Liaison, self).save(*args, **kwargs)

    @property
    def dlc_form(self):
        from .forms import LiaisonDLCForm  # Avoid circular imports
        return LiaisonDLCForm(initial={'dlc': self.dlc_set.all()})


@receiver(pre_delete, sender=Liaison)
def delete_or_hide(sender, instance, **kwargs):
    if instance.emailmessage_set.count():
        # We should hide but not actually delete Liaisons who have associated
        # emails - users don't need to see them, but we don't want to
        # alter the paper trail on associated emails.
        instance.active = False
        instance.save()
        raise IntegrityError('Cannot delete liaison with associated email.')
    else:
        # It's totally legit to delete Liaisons who are not connected to other
        # database options.
        pass


class DLC(models.Model):

    class Meta:
        verbose_name = "DLC"
        verbose_name_plural = "DLCs"

    def __str__(self):
        return self.name

    name = models.CharField(max_length=100, unique=True)
    # DLCs are created as needed during the CSV import process, and we don't
    # have liaison information available at that time.
    liaison = models.ForeignKey(Liaison, blank=True, null=True)


class Author(models.Model):

    class Meta:
        verbose_name = "Author"
        verbose_name_plural = "Authors"

    def __str__(self):
        return "{self.first_name} {self.last_name}/{self.dlc}".format(self=self)  # noqa

    # Authors may have blank DLCs in the CSV, but if that happens we're going
    # to push it back to the Sympletic layer and request that the user fix it
    # there.
    dlc = models.ForeignKey(DLC)
    email = models.EmailField(help_text="Author email address")
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=40)
    _mit_id_hash = models.CharField(max_length=32, help_text="This stores the "
        "*hash* of the MIT ID, not the MIT ID itself. We want to have a "
        "unique identifier for the author but we don't want to be storing "
        "sensitive data offsite. Hashing the ID achieves our goals.")

    @classmethod
    def is_author_creatable(self, row):
        """Expects a row of CSV data from Elements and determines whether an
        author instance can be created from it."""
        return all([bool(row[x]) for x in Headers.AUTHOR_DATA])

    @classmethod
    def get_hash(cls, mit_id):
        # This doesn't have to be cryptographically secure - we just need a
        # reasonable non-collision guarantee.
        return hashlib.md5(mit_id.encode('utf-8')).hexdigest()

    @classmethod
    def get_by_mit_id(cls, mit_id):
        # If this get raises an error, get_by_mit_id will raise the same error;
        # handle it in the same way that you would handle get().
        return Author.objects.get(_mit_id_hash=Author.get_hash(mit_id))

    # These properties allow us to get and set the mit ID using the normal
    # API; in particular, we can directly set the ID from the MTI ID value in
    # the CSV files. However, under the hood, we're throwing out the sensitive
    # data and storing hashes. Hooray!
    @property
    def mit_id(self):
        return self._mit_id_hash

    @mit_id.setter
    def mit_id(self, value):
        self._mit_id_hash = Author.get_hash(value)
