import pytest
from requests.exceptions import HTTPError, Timeout

from solenoid.elements.elements import (get_from_elements, get_paged,
                                        patch_elements_record)
from solenoid.elements.errors import RetryError


def test_get_from_elements_success(mock_elements):
    response = get_from_elements('mock://api.com')
    assert response == 'Success'


def test_get_from_elements_retries_and_raises_exception(mock_elements, error):
    with pytest.raises(RetryError):
        get_from_elements(error)
    assert mock_elements.call_count == 3


def test_get_from_elements_failure_raises_exception(mock_elements):
    with pytest.raises(HTTPError):
        get_from_elements('mock://api.com/400')


def test_get_from_elements_timeout(mock_elements):
    with pytest.raises(Timeout):
        get_from_elements('mock://api.com/timeout')


def test_get_paged_success(mock_elements):
    response = get_paged('mock://api.com/page1')
    for item in response:
        assert '<xml page=' in item


def test_patch_elements_record_success(mock_elements, patch_xml):
    response_text = patch_elements_record('mock://api.com', patch_xml)
    assert 'Success' == response_text


def test_patch_elements_record_raises_retry(mock_elements, error, patch_xml):
    with pytest.raises(RetryError):
        patch_elements_record(error, patch_xml)


def test_patch_elements_record_failure_raises_exception(
    mock_elements, patch_xml
):
    with pytest.raises(HTTPError):
        patch_elements_record('mock://api.com/400', patch_xml)


def test_patch_elements_record_timeout(
    mock_elements, patch_xml
):
    with pytest.raises(Timeout):
        patch_elements_record('mock://api.com/timeout', patch_xml)
