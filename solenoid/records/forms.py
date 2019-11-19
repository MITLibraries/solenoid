import csv
import logging

import chardet

from bs4 import UnicodeDammit
from django import forms
from django.core.exceptions import ValidationError

from .helpers import Fields

logger = logging.getLogger(__name__)

# These are the types of CSV uploaded file encoding we will test and support.
# While other encodings may work, since we aren't testing them, we won't
# accept them. This should cover anything users are reasonably likely to end up
# with after exporting from Excel, though.
# (windows-1254, oddly, is what Numbers on Mac will produce if you export
# something containing emoji.)
# If you change this, update the corresponding test!
# (solenoid.records.tests.tests.ImportViewTest.test_encodings_handled_properly)
ENCODING_OPTS = ['utf-8', 'windows-1252', 'windows-1254', 'ascii', 'utf-8-sig',
                 'iso-8859-1', 'utf-16']


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
            "encoding (Windows) or used Numbers (Mac); see instructions "
            "above.")

    return encoding


def _unicode_dammit(csv_file, encoding):
    # Let's ensure we're working with a known good encoding from here on
    # out. Thank you, Leonard Richardson!
    try:
        dammit = UnicodeDammit(csv_file.read(), ENCODING_OPTS)
    except UnicodeDecodeError as e:
        if encoding == 'utf-16':
            logger.info('Could not read file; assuming it is utf-16 with BOM')
            csv_file = csv_file.file
            csv_file.close()
            with open(csv_file, 'rb', encoding='utf-16le') as f:
                dammit = UnicodeDammit(f.read(), ['utf-16le'])
        else:
            logger.exception('Could not handle utf-16 file')
            raise e

    return dammit


def _validate_filetype(csv_utf_8):
    try:
        csv.Sniffer().sniff(csv_utf_8)
    except (csv.Error, TypeError):
        logger.exception('Invalid CSV file uploaded')
        raise ValidationError("This file doesn't appear to be CSV format.")


def _validate_headers_existence(csv_utf_8):
    try:
        has_headers = csv.Sniffer().has_header(csv_utf_8)
    except TypeError:
        logger.exception('CSV file header detection failed')
        raise ValidationError("Can't read CSV header row")
    if not has_headers:
        logger.warning('Uploaded CSV has no header row')
        raise ValidationError("This file doesn't seem to have a header row.")


def _validate_headers_content(csv_utf_8):
    dialect = csv.Sniffer().sniff(csv_utf_8)
    headers = csv_utf_8.splitlines()[0].strip().split(dialect.delimiter)
    if not all([x in headers for x in Fields.EXPECTED_FIELDS]):
        logger.warning("CSV file is missing one or more required columns")
        raise ValidationError("The CSV file must contain all of the following "
            "columns: {cols}".format(cols=Fields.EXPECTED_FIELDS))


def _validate_csv(csv_utf_8):
    delimiter = _validate_filetype(csv_utf_8)
    _validate_headers_existence(csv_utf_8)
    _validate_headers_content(csv_utf_8)
    return delimiter


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
        encoding = _validate_encoding(csv_file)
        logger.info('CSV file %s encoding is valid' % csv_file.name)

        # Reset file pointer so we get actual data on read.
        csv_file.seek(0)

        dammit = _unicode_dammit(csv_file, encoding)

        # Let's also make sure that we're not getting tripped up on differences
        # among Mac, Windows, and Unix-style newlines. (Without this line,
        # Excel saved as CSV on a Mac will break the upload.) We also need to
        # strip null bytes, which may be present after Tableau exports.
        csv_utf_8 = dammit.unicode_markup.replace(
            '\r\n', '\n').replace('\r', '\n').replace('\0', '')
        logger.info('CSV file %s converted to unicode' % csv_file.name)

        _validate_csv(csv_utf_8)
        logger.info('CSV file %s is valid' % csv_file.name)
        csv_file.close()
        return csv_utf_8
