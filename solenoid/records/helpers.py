class Headers(object):
    EMAIL = 'Email'
    DOI = 'Doi'
    FIRST_NAME = 'First Name'
    LAST_NAME = 'Last Name'
    MIT_ID = 'MIT ID'
    CITATION = 'Citation'
    PUBLISHER_NAME = 'Publisher-name'
    ACQ_METHOD = 'Method-of-Acquisition-calculated'
    DLC = 'DLC'
    PAPER_ID = 'PaperID'
    MESSAGE = 'c-publisher-related-email-message'

    EXPECTED_HEADERS = [EMAIL, DOI, FIRST_NAME, LAST_NAME, MIT_ID, CITATION,
                        PUBLISHER_NAME, ACQ_METHOD, DLC, PAPER_ID, MESSAGE]

    # This is information we can get from the database if it happens to be
    # missing from a row in an Elements CSV file, if we already know about
    # this author. However, we need all of it if we don't already know about
    # the author.
    AUTHOR_DATA = [EMAIL, FIRST_NAME, LAST_NAME, DLC]

    # And this is the information from EXPECTED_HEADERS that we can't find if
    # it isn't in the CSV. DOI is optional because we only need it for FPV
    # manuscripts - the model is responsible for checking. MESSAGE is optional
    # because not all publishers have a special message.
    REQUIRED_DATA = list(set(EXPECTED_HEADERS) -
                         set(AUTHOR_DATA) - {DOI} - {MESSAGE})
