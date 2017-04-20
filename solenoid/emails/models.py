from django.db import models

from solenoid.people.models import Author

class EmailMessage(models.Model):

    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Emails"

    def __str__(self):
        if self.date_sent:
            return "To {self.to_email} (sent {self.date_sent})".format(self=self)
        else:
            return "To {self.to_email} (unsent)".format(self=self)

    original_text = models.TextField()
    latest_text = models.TextField(blank=True, null=True)
    date_sent = models.DateField(blank=True, null=True)
    author = models.ForeignKey(Author)