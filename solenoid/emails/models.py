from bs4 import BeautifulSoup
from ckeditor.fields import RichTextField
from datetime import date
import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.dispatch import Signal
from django.template.loader import render_to_string

from solenoid.people.models import Liaison, Author

logger = logging.getLogger(__name__)

email_sent = Signal()


class EmailMessage(models.Model):

    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Emails"

    def __str__(self):
        if self.date_sent:
            return "In re {self.author} (sent {self.date_sent})".format(self=self)  # noqa
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
    _liaison = models.ForeignKey(Liaison, blank=True, null=True)

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
            if not record.email:
                citations += '<p>'
                citations += record.citation

                if record.message:
                    citations += '<b>[{msg}]</b>'.format(msg=record.message.text)  # noqa

                if record.fpv_message:
                    citations += record.fpv_message
                citations += '</p>'
        return citations

    @classmethod
    def create_original_text(cls, record_list):
        """Given a queryset of records, creates the default text of an email
        about them.

        Will discard records that already have an email, and raise an error if
        that leaves zero records. Will also verify that all records have the
        same author and raise a ValidationError if not."""
        if not record_list:
            raise ValidationError('No records provided.')

        available_records = record_list.filter(email__isnull=True)
        if not available_records:
            raise ValidationError('All records already have emails.')

        try:
            authors = record_list.values_list('author')
            # list(set()) removes duplicates.
            assert len(list(set(authors))) == 1
        except AssertionError:
            raise ValidationError('All records must have the same author.')

        author = record_list.first().author
        citations = cls._create_citations(record_list)

        return render_to_string('emails/author_email_template.html',
            context={'author': author,
                     'liaison': author.dlc.liaison,
                     'citations': citations})

    @classmethod
    def get_or_create_for_records(cls, records):
        """Given a queryset of records, finds or creates an *unsent* email to
        their author (there should not be more than one of these at a time).
        Records must all be by the same author."""
        # First, throw out all emails that have already been sent.
        records = records.filter(email__date_sent__isnull=True)

        if records.count() == 0:
            return None

        count = Author.objects.filter(record__in=records).distinct().count()
        if count == 0:
            return None
        elif count > 1:
            raise ValidationError('Records do not all have the same author.')
        else:
            author = Author.objects.filter(record__in=records)[0]

        emails = cls.objects.filter(
            record__author=author, date_sent__isnull=True).distinct()

        try:
            assert len(emails) in [0, 1]
        except AssertionError:
            logger.exception('Multiple unsent emails found for %s' % author)
            raise ValidationError('Multiple unsent emails found.')

        if emails:
            email = emails[0]
        else:
            email = cls(original_text=cls.create_original_text(records),
                _liaison=author.dlc.liaison)
            email.save()

        # Make sure to create the ForeignKey relation from those records to
        # the email! Otherwise this method will only ever create new emails
        # rather than finding existing ones.
        records.update(email=email)
        return email

    def _is_valid_for_sending(self):
        try:
            assert not self.date_sent
        except AssertionError:
            logger.exception('Attempt to send invalid email')
            return False

        try:
            # Can't send the email if there isn't a liaison.
            assert self.liaison
        except AssertionError:
            logger.exception('Attempt to send email {pk}, which is missing a '
                'liaison'.format(pk=self.pk))
            return False

        return True

    def _update_after_sending(self):
        """Set the metadata that should be set after sending an email."""
        self.date_sent = date.today()
        self._liaison = self.liaison
        self.save()

    def _inner_send(self):
        """Actually perform the sending of an EmailMessage. Return True on
        success, False otherwise."""
        try:
            recipients = [self.liaison.email_address]
            if settings.SCHOLCOMM_MOIRA_LIST:
                recipients.append(settings.SCHOLCOMM_MOIRA_LIST)

            send_mail(
                self.subject,
                self.plaintext,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                html_message=self.latest_text,
                fail_silently=False,
            )
        except SMTPException:
            return False

        return True

    def send(self):
        """
        Validates and sends an EmailMessage with the given pk. Upon send,
        updates sending-related metadata. Returns True if successful; False
        otherwise.
        """
        # First, validate.
        if not self._is_valid_for_sending():
            return False

        # Then, send.
        if not self._inner_send():
            return False

        self._update_after_sending()
        email_sent.send(sender=self)

        return True

    def revert(self):
        """Ensure that the display text of the email is the original text.

        Right now we implement this by setting the latest text to the original,
        but we explicitly don't guarantee any particular implementation."""

        self.latest_text = self.original_text
        self.save()

    @property
    def author(self):
        try:
            return self.record_set.first().author
        except:
            return None

    @property
    def dlc(self):
        try:
            return self.record_set.first().author.dlc
        except:
            return None

    @property
    def liaison(self):
        """For *sent* emails, returns the liaison to whom we actually sent the
        email (regardless of whether that is the current one).
        For *unsent* emails, returns the liaison to whom we expect to send the
        email. This can and should change if DLC/liaison pairings are updated.
        """
        if self._liaison:
            return self._liaison
        else:
            try:
                return self.dlc.liaison
            except AttributeError:
                # This happens when there is no DLC.
                return None

    @property
    def plaintext(self):
        """Returns the latest_text in plaintext format, suitable for
        constructing a multipart alternative email (as the html stored in
        latest_text is properly the second part, not the main text)."""
        soup = BeautifulSoup(self.latest_text, "html.parser")
        return soup.get_text().replace('\n', '\n\n')

    @property
    def subject(self):
        # This will throw an exception if there is no author for the email.
        # That's fine - we *shouldn't* be able to send emails with no author,
        # and we *should* notice if this problem happens - but we should log
        # it.
        try:
            return 'OA outreach message to forward: {author}'.format(
                author=self.author.last_name)
        except AttributeError:
            logger.exception('Could not find author for email #{pk}'.format(
                pk=self.pk))
            raise
