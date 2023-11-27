import logging
from typing import Generator
import xml.etree.ElementTree as ET

import backoff
import requests

from django.conf import settings

from .errors import RetryError
from .xml_handlers import NS

logger = logging.getLogger(__name__)

AUTH = (settings.ELEMENTS_USER, settings.ELEMENTS_PASSWORD)

PROXIES = {
    "http": settings.QUOTAGUARD_URL,
    "https": settings.QUOTAGUARD_URL,
}


@backoff.on_exception(backoff.expo, RetryError, max_tries=5)
def get_from_elements(url: str) -> str:
    """Issue a get request to the Elements API for a given URL. Return the
    response text. Retries up to 5 times for known Elements API retry status
    codes.
    """
    response = requests.get(url, proxies=PROXIES, auth=AUTH, timeout=10)  # type: ignore
    if response.status_code in [409, 500, 504]:
        raise RetryError(
            f"Elements response status {response.status_code} " "requires retry"
        )
    response.raise_for_status()
    return response.text


def get_paged(url: str) -> Generator:
    page = get_from_elements(url)
    yield (page)
    next = ET.fromstring(page).find(".//*[@position='next']", NS)
    if next is not None:
        next_url = next.get("href")
        if next_url is not None:
            yield from get_paged(next_url)


@backoff.on_exception(backoff.expo, RetryError, max_tries=5)
def patch_elements_record(url: str, xml_data: str) -> str:
    """Issue a patch to the Elements API for a given item record URL, with the
    given update data. Return the response. Retries up to 5 times for known Elements
    API retry status codes."""
    response = requests.patch(
        url,
        data=xml_data,
        headers={"Content-Type": "text/xml"},
        proxies=PROXIES,  # type: ignore
        auth=AUTH,  # type: ignore
        timeout=10,
    )
    if response.status_code in [409, 500, 504]:
        raise RetryError(
            f"Elements response status {response.status_code} " "requires retry"
        )
    response.raise_for_status()
    return response.text
