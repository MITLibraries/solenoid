from django.db import models


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

    name = models.CharField(max_length=100)
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
    mit_id = models.CharField(max_length=10)
