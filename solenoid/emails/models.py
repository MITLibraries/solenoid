from django.db import models
from django.template.loader import render_to_string

from solenoid.people.models import Author, Liaison

from .helpers import SPECIAL_MESSAGES

class EmailMessage(models.Model):

    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Emails"

    def __str__(self):
        if self.date_sent:
            return "To {self.author} (sent {self.date_sent})".format(self=self)
        else:
            return "To {self.author} (unsent)".format(self=self)

    original_text = models.TextField(editable=False)
    latest_text = models.TextField(blank=True, null=True)
    date_sent = models.DateField(blank=True, null=True)
    author = models.ForeignKey(Author)
    # Although we can derive Liaison from Author via DLC, we're going to
    # record it here because liaisons can change over time; we want to record
    # the actual liaison to whom the email was sent.
    liaison = models.ForeignKey(Liaison)

    @classmethod
    def _create_citations(cls, record_list):
        citations = ''
        for record in record_list:
            citations += '<p>'
            citations += record.citation
            try:
                msg_template = SPECIAL_MESSAGES[record.publisher_name]
                msg = msg_template.format(doi=record.doi)
                citations += '<b>[{msg}]</b>'.format(msg=msg)
            except KeyError:
                # If the publisher doesn't have a corresponding special message,
                # that's fine; just keep going.
                pass
            citations += '</p>'
        return citations

    @classmethod
    def create_original_text(cls, author, record_list):
        citations = cls._create_citations(record_list)
        return render_to_string('emails/author_email_template.html',
            context={'author': author,
                     'liaison': author.dlc.liaison,
                     'citations': citations})
