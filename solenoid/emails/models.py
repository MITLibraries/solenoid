from bs4 import BeautifulSoup
from ckeditor.fields import RichTextField
from datetime import date
import logging
import re
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string

from solenoid.people.models import Liaison, Author

from .signals import email_sent

logger = logging.getLogger(__name__)


class EmailMessage(models.Model):
    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Emails"

    def __str__(self):
        if self.date_sent:
            return "In re {self.author} (sent " "{self.date_sent})".format(self=self)
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
    # responsible for handling exceptions. DO NOT SET until email send.
    _liaison = models.ForeignKey(Liaison, blank=True, null=True, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    # This should be set to True when people import new citations for this
    # email's author after starting the email, but before sending it. It should
    # be set to False after people edit the email (save or send).
    new_citations = models.BooleanField(default=False)

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
        """Creates a text block of citations for this record list. Does NOT
        validate the citations - make sure you have done any needed sanitizing
        first."""
        logger.info("Creating citations for {list}".format(list=record_list))
        citations = ""
        for record in record_list:
            citations += "<p>"
            citations += record.citation

            if record.message:
                citations += f"<br /><b>[{record.message}]</b>"
            elif record.fpv_message:
                citations += f"<br /><b>{record.fpv_message}</b>"

            citations += "</p>"
        logger.info("Citations created")

        # This is the unicode replacement character. It shows up sometimes in
        # our imports; we should just remove it.
        citations = re.sub("\ufffd", " ", citations)
        return citations

    @classmethod
    def create_original_text(cls, record_list):
        """Given a queryset of records, creates the default text of an email
        about them.

        Will discard records that already have an email, and raise an error if
        that leaves zero records. Will also verify that all records have the
        same author and raise a ValidationError if not."""

        logger.info("Creating original text of email for {list}".format(list=record_list))
        if not record_list:
            logger.warning("Could not create email text - no record_list")
            raise ValidationError("No records provided.")

        available_records = record_list.filter(email__isnull=True)
        if not available_records:
            logger.warning(
                "Could not create email text - all records already " "have emails"
            )
            raise ValidationError("All records already have emails.")

        try:
            authors = record_list.values_list("author")
            # list(set()) removes duplicates.
            assert len(list(set(authors))) == 1
        except AssertionError:
            logger.exception(
                "Could not create email text - multiple authors " "in record set"
            )
            raise ValidationError("All records must have the same author.")

        author = record_list.first().author
        citations = cls._create_citations(available_records)

        logger.info("Returning original text of email")
        return render_to_string(
            "emails/author_email_template.html",
            context={
                "author": author,
                "liaison": author.dlc.liaison,
                "citations": citations,
            },
        )

    @staticmethod
    def _filter_records(records):
        # First, throw out all emails that have already been sent.
        records = records.filter(email__date_sent__isnull=True)

        if records.count() == 0:
            logger.info("No records - not creating email")
            return None

        return records

    @classmethod
    def _finalize_email(cls, email, records, author):
        if email:
            email = email[0]
            email.rebuild_citations()
        else:
            email = cls(original_text=cls.create_original_text(records), author=author)
            email.save()

        # Make sure to create the ForeignKey relation from those records to
        # the email! Otherwise this method will only ever create new emails
        # rather than finding existing ones.
        logger.info("Creating foreign key relationship to email for records")
        records.update(email=email)
        return email

    @staticmethod
    def _get_author_from_records(records):
        count = Author.objects.filter(record__in=records).distinct().count()
        # We don't have to worry about the count being zero because Record
        # requires Author. Don't call this with an empty record set!
        assert records
        if count > 1:
            logger.warning("Records have different authors - not creating " "email")
            raise ValidationError("Records do not all have the same author.")
        else:
            return Author.objects.filter(record__in=records)[0]

    @classmethod
    def _get_email_for_author(cls, author):
        emails = cls.objects.filter(author=author, date_sent__isnull=True).distinct()

        try:
            assert len(emails) in [0, 1]
        except AssertionError:
            logger.exception("Multiple unsent emails found for %s" % author)
            raise ValidationError("Multiple unsent emails found.")

        return emails if emails else None

    @classmethod
    def get_or_create_for_records(cls, records):
        """Given a queryset of records, finds or creates an *unsent* email to
        their author (there should not be more than one of these at a time).
        Records must all be by the same author."""

        logger.info("Creating unsent email for {records}".format(records=records))

        records = cls._filter_records(records)
        if not records:
            return None

        author = cls._get_author_from_records(records)
        if not author:
            return None

        email = cls._get_email_for_author(author)
        email = cls._finalize_email(email, records, author)

        logger.info("Retuning email")
        return email

    def _is_valid_for_sending(self):
        logger.info("Checking if email {pk} is valid for sending".format(pk=self.pk))
        try:
            assert not self.date_sent
        except AssertionError:
            logger.exception("Attempt to send invalid email")
            return False

        try:
            # Can't send the email if there isn't a liaison.
            assert self.liaison
        except AssertionError:
            logger.exception(
                "Attempt to send email {pk}, which is missing a "
                "liaison".format(pk=self.pk)
            )
            return False

        logger.info("Email {pk} is valid for sending".format(pk=self.pk))
        return True

    def _update_after_sending(self):
        """Set the metadata that should be set after sending an email."""
        logger.info("Updating date_sent for email {pk}".format(pk=self.pk))
        self.date_sent = date.today()
        self._liaison = self.liaison
        self.save()

    def _inner_send(self):
        """Actually perform the sending of an EmailMessage. Return True on
        success, False otherwise."""

        logger.info("Sending email {pk}".format(pk=self.pk))

        try:
            if settings.EMAIL_TESTING_MODE:
                recipients = [admin[1] for admin in settings.ADMINS]
            else:
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
            logger.exception("Could not send email; SMTP exception")
            return False
        except Exception:
            logger.exception("Could not send email; unanticipated exception")
            return False

        logger.info("Done sending email")
        return True

    def send(self, username):
        """
        Validates and sends an EmailMessage with the given pk. Upon send,
        updates sending-related metadata. Returns True if successful; False
        otherwise.
        """

        logger.info("Entering email.send() for {pk}".format(pk=self.pk))
        # First, validate.
        if not self._is_valid_for_sending():
            return False

        # Then, send.
        if not self._inner_send():
            return False

        self._update_after_sending()
        logger.info("Sending email_sent signal")

        email_sent.send(sender=self.__class__, instance=self, username=username)

        logger.info("Email {pk} sent".format(pk=self.pk))
        return True

    def rebuild_citations(self):
        """Find all unsent citations by this email's author. If it's the same
        as the current set of citations in this email, return False. If
        different, update the email to reflect all current unsent citations and
        return True."""
        # Get all unsent records associated with this email's author. This
        # will include the current email record_set and also unsent emails.
        # Use this rather than filtering Record directly to avoid circular
        # imports.
        records = self.author.record_set.exclude(email__date_sent__isnull=False)

        if records.count() == self.record_set.count():
            # Nothing to change here.
            return False

        soup = BeautifulSoup(self.latest_text, "html.parser")

        citations = EmailMessage._create_citations(records)
        new_soup = BeautifulSoup(citations, "html.parser")

        cite_block = soup.find("div", class_="control-citations")
        cite_block.clear()
        cite_block.insert(1, new_soup)
        self.latest_text = soup.prettify()
        self.new_citations = True
        self.save()

        return True

    def revert(self):
        """Ensure that the display text of the email is the original text.

        Right now we implement this by setting the latest text to the original,
        but we explicitly don't guarantee any particular implementation."""

        logger.info("Reverting changes for {pk}".format(pk=self.pk))
        self.latest_text = self.original_text
        self.save()

    @property
    def dlc(self):
        try:
            return self.author.dlc
        except Exception:
            return None

    @property
    def liaison(self):
        """For *sent* emails, returns the liaison to whom we actually sent the
        email (regardless of whether that is the current one).
        For *unsent* emails, returns the liaison to whom we expect to send the
        email. This can and should change if DLC/liaison pairings are updated.
        """
        if self._liaison and self.date_sent:
            # Don't just check for self._liaison, in case you foolishly set
            # that before sending the email.
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
        return soup.get_text()

    @property
    def subject(self):
        # This will throw an exception if there is no author for the email.
        # That's fine - we *shouldn't* be able to send emails with no author,
        # and we *should* notice if this problem happens - but we should log
        # it.
        try:
            return "OA outreach message to forward: {author}".format(
                author=self.author.last_name
            )
        except AttributeError:
            logger.exception("Could not find author for email #{pk}".format(pk=self.pk))
            raise
