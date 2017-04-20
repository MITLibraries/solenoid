from django.db import models

class Author(models.Model):

    class Meta:
        verbose_name = "Author"
        verbose_name_plural = "Authors"

    def __str__(self):
        return "{self.first_name} {self.last_name}/{self.dlc}".format(self=self)

    dlc = models.CharField(max_length=100)
    email = models.EmailField(help_text="Author email address")
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=40)
    mit_id = models.CharField(max_length=10) 
