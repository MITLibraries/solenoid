import hashlib
import logging

from django.db import models
from django.db.models.query import QuerySet

from solenoid.records.helpers import Headers


logger = logging.getLogger(__name__)


# We want to ensure that Liaisons are not deleted, but merely hidden, if they
# have associated EmailMessages. Liaison.delete() will do this in cases where =
# object.delete() is called; however, we need to override the queryset behavior
# to protect against mass deletions, invoked by QuerySet.delete().
class ProtectiveQueryset(QuerySet):
    def delete(self):
        self.filter(emailmessage__isnull=False).update(active=False)
        self.filter(emailmessage__isnull=True).delete()


class DefaultManager(models.Manager):
    def get_queryset(self):
        return ProtectiveQueryset(self.model, using=self._db)


class ActiveLiaisonManager(models.Manager):
    def get_queryset(self):
        return ProtectiveQueryset(self.model, using=self._db).filter(
            active=True)


class Liaison(models.Model):

    class Meta:
        verbose_name = "Liaison"
        verbose_name_plural = "Liaisons"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return "{self.first_name} {self.last_name}".format(self=self)

    first_name = models.CharField(max_length=15)
    last_name = models.CharField(max_length=30)
    email_address = models.EmailField()
    # We don't actually want to delete Liaisons who have associated emails.
    # Instead, we create a custom manager to only show active Liaisons.
    active = models.BooleanField(default=True)

    # The first listed manager is the internal Django default, used, e.g., by
    # the admin.
    objects_all = DefaultManager()

    # This is the manager we will actually expose; it limits to active
    # Liaisons.
    objects = ActiveLiaisonManager()

    def save(self, *args, **kwargs):
        if not self.active:
            self.dlc_set.clear()

        return super(Liaison, self).save(*args, **kwargs)

    # This prevents object.delete() from deleting liaisons with attached email.
    def delete(self):
        if self.emailmessage_set.count():
            self.active = False
            self.save()
        else:
            super(Liaison, self).delete()

    @property
    def dlc_form(self):
        from .forms import LiaisonDLCForm  # Avoid circular imports
        return LiaisonDLCForm(initial={'dlc': self.dlc_set.all()})


class DLC(models.Model):

    class Meta:
        verbose_name = "DLC"
        verbose_name_plural = "DLCs"
        ordering = ['name']

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
        ordering = ['last_name', 'first_name']

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
