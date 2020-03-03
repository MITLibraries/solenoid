import pytest
from requests.exceptions import HTTPError

from solenoid.elements.elements import (get_from_elements, get_paged,
                                        patch_elements_record)
from solenoid.elements.errors import RetryError


def test_get_from_elements_success(mock_elements):
    response = get_from_elements('mock://api.com')
    assert response == 'Success'


def test_get_from_elements_retries_and_raises_exception(mock_elements):
    assert 0 == mock_elements.call_count
    with pytest.raises(RetryError):
        get_from_elements('mock://api.com/409')
    assert 3 == mock_elements.call_count
    with pytest.raises(RetryError):
        get_from_elements('mock://api.com/500')
    assert 6 == mock_elements.call_count
    with pytest.raises(RetryError):
        get_from_elements('mock://api.com/504')
    assert 9 == mock_elements.call_count


def test_get_from_elements_failure_raises_exception(mock_elements):
    with pytest.raises(HTTPError):
        get_from_elements('mock://api.com/400')


def test_get_paged_success(mock_elements):
    response = get_paged('mock://api.com/page1')
    for item in response:
        assert '<xml page=' in item


def test_patch_elements_record_success(mock_elements, patch_xml):
    response = patch_elements_record('mock://api.com', patch_xml)
    assert 200 == response.status_code


def test_patch_elements_record_raises_retry(mock_elements, patch_xml):
    with pytest.raises(RetryError):
        patch_elements_record('mock://api.com/409', patch_xml)
    with pytest.raises(RetryError):
        patch_elements_record('mock://api.com/500', patch_xml)
    with pytest.raises(RetryError):
        patch_elements_record('mock://api.com/504', patch_xml)


def test_patch_elements_record_failure_raises_exception(mock_elements,
                                                        patch_xml):
    with pytest.raises(HTTPError):
        patch_elements_record('mock://api.com/400', patch_xml)
