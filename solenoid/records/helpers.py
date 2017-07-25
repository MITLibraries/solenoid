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
    SOURCE = 'Data Source (Publication)'
    RECORD_ID = 'Data Source Proprietary ID (Publication)'
    # Note - this seems to be a string like '20050601' and not an actual year,
    # column title notwithstanding.
    PUBDATE = 'Year Published'
    TITLE = 'Title1'
    JOURNAL = 'Journal'
    VOLUME = 'Volume'
    ISSUE = 'Issue'

    EXPECTED_HEADERS = [EMAIL, DOI, FIRST_NAME, LAST_NAME, MIT_ID, CITATION,
                        PUBLISHER_NAME, ACQ_METHOD, DLC, PAPER_ID, MESSAGE,
                        SOURCE, RECORD_ID, TITLE, JOURNAL, VOLUME, ISSUE]

    # This is information we can get from the database if it happens to be
    # missing from a row in an Elements CSV file, if we already know about
    # this author. However, we need all of it if we don't already know about
    # the author.
    AUTHOR_DATA = [EMAIL, FIRST_NAME, LAST_NAME, DLC]

    # This is the data we need to construct a minimal citation, if the citation
    # field is blank.
    CITATION_DATA = [FIRST_NAME, LAST_NAME, TITLE, JOURNAL]

    # And this is the information from EXPECTED_HEADERS that we can't find if
    # it isn't in the CSV.
    # Some information is optional because...
    # * DOI: only needed for FPV manuscripts - the model is responsible for
    #   checking.
    # * MESSAGE: not all publishers have a special message.
    # * CITATION and citation-related data: We can construct a minimal citation
    #   from other data; alternately, we don't need the other data if we have a
    #   citation. The Record model will check for this.
    REQUIRED_DATA = list(set(EXPECTED_HEADERS) -
                         set(AUTHOR_DATA) - {DOI} - {MESSAGE} - {CITATION} -
                         {TITLE} - {JOURNAL} - {VOLUME} - {ISSUE})
