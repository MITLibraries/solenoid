from django.db import models

from solenoid.people.models import Author, Liaison

class EmailMessage(models.Model):

    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Emails"

    def __str__(self):
        if self.date_sent:
            return "To {self.author} (sent {self.date_sent})".format(self=self)
        else:
            return "To {self.author} (unsent)".format(self=self)

    original_text = models.TextField()
    latest_text = models.TextField(blank=True, null=True)
    date_sent = models.DateField(blank=True, null=True)
    author = models.ForeignKey(Author)
    # Although we can derive Liaison from Author via DLC, we're going to
    # record it here because liaisons can change over time; we want to record
    # the actual liaison to whom the email was sent.
    liaison = models.ForeignKey(Liaison)
