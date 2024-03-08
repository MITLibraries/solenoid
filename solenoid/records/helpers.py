class Fields(object):
    EMAIL = "Email"
    DOI = "Doi"
    FIRST_NAME = "First Name"
    LAST_NAME = "Last Name"
    MIT_ID = "MIT ID"
    CITATION = "Citation"
    PUBLISHER_NAME = "Publisher-name"
    ACQ_METHOD = "C-Method-Of-Acquisition"
    DLC = "DLC"
    PAPER_ID = "PaperID"
    MESSAGE = "C-Publisher-Related-Email-Message"
    PUBDATE = "Year Published"
    TITLE = "Title1"
    JOURNAL = "Journal-name"
    VOLUME = "Volume"
    ISSUE = "Issue"

    EXPECTED_FIELDS = [
        EMAIL,
        DOI,
        FIRST_NAME,
        LAST_NAME,
        MIT_ID,
        CITATION,
        PUBLISHER_NAME,
        ACQ_METHOD,
        DLC,
        PAPER_ID,
        MESSAGE,
        TITLE,
        JOURNAL,
        VOLUME,
        ISSUE,
    ]

    # This is information we can get from the database if it happens to be
    # missing from the Elements metadata, if we already know about
    # this author. However, we need all of it if we don't already know about
    # the author.
    AUTHOR_DATA = [EMAIL, FIRST_NAME, LAST_NAME, DLC]

    # This is the data we need to construct a minimal citation, if the citation
    # field is blank.
    CITATION_DATA = [FIRST_NAME, LAST_NAME, TITLE, JOURNAL]

    # And this is the information from EXPECTED_HEADERS that we can't find if
    # it isn't in the data.
    # Some information is optional because...
    # * DOI: only needed for FPV manuscripts - the model is responsible for
    #   checking.
    # * MESSAGE: not all publishers have a special message.
    # * CITATION and citation-related data: We can construct a minimal citation
    #   from other data; alternately, we don't need the other data if we have a
    #   citation. The Record model will check for this.
    REQUIRED_DATA = list(
        set(EXPECTED_FIELDS)
        - set(AUTHOR_DATA)
        - {DOI}
        - {MESSAGE}
        - {CITATION}
        - {TITLE}
        - {JOURNAL}
        - {VOLUME}
        - {ISSUE}
        -
        # Acq method is allowed to be blank.
        {ACQ_METHOD}
        -
        # We don't need publisher name unless the method of
        # acquisition is FPV (in which case the publisher name
        # is interpolated into the email text).
        {PUBLISHER_NAME}
    )
