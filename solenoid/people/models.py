import hashlib

from django.db import models

from solenoid.records.helpers import Headers


class Liaison(models.Model):

    class Meta:
        verbose_name = "Liaison"
        verbose_name_plural = "Liaisons"

    def __str__(self):
        return "{self.first_name} {self.last_name}".format(self=self)

    first_name = models.CharField(max_length=15)
    last_name = models.CharField(max_length=30)
    email_address = models.EmailField()

    @property
    def dlc_form(self):
        from .forms import LiaisonDLCForm  # Avoid circular imports
        return LiaisonDLCForm(initial={'dlc': self.dlc_set.all()})


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
