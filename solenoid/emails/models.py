from django.db import models

class Email(models.Model):

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
    to_email = models.EmailField()
