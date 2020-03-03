# Maintenance requirements
When CKEditor must be updated, be aware that solenoid needs to do careful surgery on the contents of the file that users update via CKeditor in order to update saved emails with new citation data when additional citations are uploaded. This surgery depends on CKEditor configuration in the settings file, to prevent CKeditor from stripping the invisible HTML and CSS used to demarcate the updateable region. Verify that this feature still works by doing the following:
* upload some citations
* create a new email
* edit and save (but do not send) it
* upload additional citations _by the same author_
* reopen the saved email
* confirm that the new citations have been appended to the citation region and previous edits are retained

Solenoid integrates with the Symplectic Elements API. This API may change at any time without warning, with changes deployed to the same endpoint. The endpoint URL may also change without warning due to Elements system configuration.

`settings.WHITELIST` contains the list of MIT kerbs which are authorized to log in to Solenoid. This includes the list of users you are supporting, and should contain the project manager with the maintenance plan and the staff responsible for the relationship with Symplectic. It may need to be updated from time to time according to staff turnover or roles changes.

There is a Moira list of solenoid users which you can use to communicate about downtime, etc.: https://groups.mit.edu/webmoira/list/solenoid-users

There is also a Moira list of solenoid admins which is listed as a contact email in the 500 error page and to email API notifications as noted above. This should be updated as needed with members of the tech support team responsible for maintaining the application: https://groups.mit.edu/webmoira/list/solenoid-admins
