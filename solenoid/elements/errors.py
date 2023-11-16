class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class RetryError(Error):
    """Exception raised for HTTP status codes that indicate a Symplectic
    Elements API call should be retried (409, 500, 504).
    """

    pass
