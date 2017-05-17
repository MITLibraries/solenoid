from ckeditor.fields import RichTextField
import logging

from django.db import models
from django.template.loader import render_to_string

from solenoid.people.models import Liaison

from .helpers import SPECIAL_MESSAGES

logger = logging.getLogger(__name__)


class EmailMessage(models.Model):

    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Emails"

    def __str__(self):
        if self.date_sent:
            return "In re {self.author} (sent {self.date_sent})".format(self=self)
        else:
            return "In re {self.author} (unsent)".format(self=self)

    original_text = RichTextField(editable=False)
    latest_text = RichTextField(blank=True, null=True)
    date_sent = models.DateField(blank=True, null=True)
    # Although we can derive Liaison from Author via DLC, we're going to
    # record it here because liaisons can change over time; we want to record
    # the actual liaison to whom the email was sent. We allow it to be blank
    # because this allows users to use certain bits of the workflow that don't
    # require knowledge of the liaison (e.g. editing email text). This means
    # downstream functions that depend on the liaison's existence are
    # responsible for handling exceptions.
    liaison = models.ForeignKey(Liaison, blank=True, null=True)

    def save(self, *args, **kwargs):
        # One might have a display_text property that showed latest_text if
        # non-null and original_text otherwise...but there's no way to set
        # initial values for modelformset fields (as needed on the email
        # evaluate page), so it's easiest to just ensure that the latest text
        # reflects whatever we want users to see.
        if not self.latest_text:
            self.latest_text = self.original_text
        super(EmailMessage, self).save(*args, **kwargs)

    @classmethod
    def _create_citations(cls, record_list):
        citations = ''
        for record in record_list:
            if record.is_sendable:
                citations += '<p>'
                citations += record.citation
                try:
                    msg_template = SPECIAL_MESSAGES[record.publisher_name]
                    msg = msg_template.format(doi=record.doi)
                    citations += '<b>[{msg}]</b>'.format(msg=msg)
                except KeyError:
                    # If the publisher doesn't have a corresponding special
                    # message, that's fine; just keep going.
                    pass
                if record.fpv_message:
                    citations += record.fpv_message
                citations += '</p>'
        return citations

    @classmethod
    def create_original_text(cls, author, record_list):
        citations = cls._create_citations(record_list)
        return render_to_string('emails/author_email_template.html',
            context={'author': author,
                     'liaison': author.dlc.liaison,
                     'citations': citations})

    @classmethod
    def get_or_create_by_author(cls, author):
        """Given an author, finds or creates an *unsent* email to that author
        (there should not be more than one of these at a time)."""
        email = cls.objects.filter(
            record__author=author, date_sent__isnull=True).distinct()

        try:
            assert len(email) in [0, 1]
        except AssertionError:
            logger.exception('Multiple unsent emails found for %s' % author)
            raise

        if email:
            return email[0]
        else:
            return cls(original_text=cls.create_original_text(author),
                liaison=author.dlc.liaison)

    def revert(self):
        """Ensure that the display text of the email is the original text.

        Right now we implement this by setting the latest text to the original,
        but we explicitly don't guarantee any particular implementation."""

        self.latest_text = self.original_text
        self.save()

    @property
    def author(self):
        try:
            return self.records.first().author
        except:
            return None
