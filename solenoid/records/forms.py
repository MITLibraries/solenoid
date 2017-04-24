import chardet
import csv
import logging

from django import forms
from django.core.exceptions import ValidationError

from .helpers import Headers

logger = logging.getLogger(__name__)


def _validate_encoding(csv_file):
    csv_file.seek(0)
    encoding_info = chardet.detect(csv_file.read())
    encoding = encoding_info['encoding']
    if (not encoding or
            encoding.lower() not in ['utf-8', 'utf-16', 'windows-1252', 'ascii']): # noqa
        raise ValidationError("File encoding not recognized. Please "
            "make sure you have exported from Excel to CSV with UTF-8 "
            "encoding.")

    return encoding


def _validate_filetype(csv_file, encoding):
    csv_file.seek(0)
    try:
        csv.Sniffer().sniff(csv_file.read().decode(encoding))
    except csv.Error:
        logger.warning('Invalid CSV file uploaded')
        raise ValidationError("This file doesn't appear to be CSV format.")


def _validate_headers_existence(csv_file, encoding):
    csv_file.seek(0)
    if not csv.Sniffer().has_header(csv_file.read().decode(encoding)):
        logger.warning('Uploaded CSV has no header row')
        raise ValidationError("This file doesn't seem to have a header row.")


def _validate_headers_content(csv_file, encoding):
    csv_file.seek(0)
    headers = csv_file.readline().decode(encoding).strip().split(',')
    if not all([x in headers for x in Headers.EXPECTED_HEADERS]):
        logger.warning("CSV file is missing one or more required columns")
        raise ValidationError("The CSV file must contain all of the following "
            "columns: {cols}".format(cols=Headers.EXPECTED_HEADERS))


def _validate_csv(csv_file):
    encoding = _validate_encoding(csv_file)
    _validate_filetype(csv_file, encoding)
    _validate_headers_existence(csv_file, encoding)
    _validate_headers_content(csv_file, encoding)


class ImportForm(forms.Form):
    csv_file = forms.FileField(validators=[_validate_csv])
