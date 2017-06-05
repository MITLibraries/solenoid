from bs4 import UnicodeDammit
import chardet
import csv
import logging

from django import forms
from django.core.exceptions import ValidationError

from .helpers import Headers

logger = logging.getLogger(__name__)

# These are the types of CSV uploaded file encoding we will test and support.
# While other encodings may work, since we aren't testing them, we won't
# accept them. This should cover anything users are reasonably likely to end up
# with after exporting from Excel, though.
ENCODING_OPTS = ['utf-8', 'utf-16', 'windows-1252', 'ascii', 'utf-8-sig']


def _validate_encoding(csv_file):
    csv_file.seek(0)
    encoding_info = chardet.detect(csv_file.read())
    encoding = encoding_info['encoding']
    if (not encoding or
            encoding.lower() not in ENCODING_OPTS):
        logger.warning('Unsupported encoding {enc} for CSV file {name}'.format(
            enc=encoding, name=csv_file.name))
        raise ValidationError("File encoding not recognized. Please "
            "make sure you have exported from Excel to CSV with UTF-8 "
            "encoding.")


def _validate_filetype(csv_file):
    try:
        csv.Sniffer().sniff(csv_file)
    except csv.Error:
        logger.warning('Invalid CSV file {name} uploaded'.format(
            name=csv_file.name))
        raise ValidationError("This file doesn't appear to be CSV format.")


def _validate_headers_existence(csv_file):
    try:
        has_headers = csv.Sniffer().has_header(csv_file)
    except TypeError:
        logger.exception('CSV file header detection failed')
        raise ValidationError("Can't read CSV header row")
    if not has_headers:
        logger.warning('Uploaded CSV has no header row')
        raise ValidationError("This file doesn't seem to have a header row.")


def _validate_headers_content(csv_file):
    headers = csv_file.splitlines()[0].strip().split(',')
    if not all([x in headers for x in Headers.EXPECTED_HEADERS]):
        logger.warning("CSV file is missing one or more required columns")
        raise ValidationError("The CSV file must contain all of the following "
            "columns: {cols}".format(cols=Headers.EXPECTED_HEADERS))


def _validate_csv(csv_file):
    _validate_filetype(csv_file)
    _validate_headers_existence(csv_file)
    _validate_headers_content(csv_file)


class ImportForm(forms.Form):
    csv_file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)
        self.fields['csv_file'].widget.attrs['class'] = 'field field-upload'

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        logger.info('Cleaning CSV file %s...' % csv_file.name)

        # Check encodings before proceeding. Will raise exception for
        # unsupported encodings.
        _validate_encoding(csv_file)
        logger.info('CSV file %s encoding is valid' % csv_file.name)

        # Reset file pointer so we get actual data on read.
        csv_file.seek(0)

        # Yeah, let's ensure we're working with a known good encoding from
        # here on out. Thank you, Leonard Richardson!
        dammit = UnicodeDammit(csv_file.read(), ENCODING_OPTS)

        # Let's also make sure that we're not getting tripped up on differences
        # among Mac, Windows, and Unix-style newlines. (Without this line,
        # Excel saved as CSV on a Mac will break the upload.)
        csv_utf_8 = dammit.unicode_markup.replace(
            '\r\n', '\n').replace('\r', '\n')
        logger.info('CSV file %s converted to unicode' % csv_file.name)

        _validate_csv(csv_utf_8)
        logger.info('CSV file %s is valid' % csv_file.name)
        return csv_utf_8
