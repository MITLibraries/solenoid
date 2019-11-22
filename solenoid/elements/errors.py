class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class RetryError(Error):
    """Exception raised for HTTP status codes that indicate a Symplectic
    Elements API call should be retried (409, 504).
    """

    def __init__(self, status_code):
        Error.__init__(self, f'Elements response status {status_code} '
                       'requires retry')
