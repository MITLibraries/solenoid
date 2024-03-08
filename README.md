![Test Status](https://github.com/MITLibraries/solenoid/workflows/Tests/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/MITLibraries/solenoid/badge.svg?branch=master)](https://coveralls.io/github/MITLibraries/solenoid?branch=master)
[![Code Climate](https://codeclimate.com/github/MITLibraries/solenoid/badges/gpa.svg)](https://codeclimate.com/github/MITLibraries/solenoid)

# solenoid

Solenoid is a web application for sending email requests for publications to students and faculty. The application supports the work of MIT Libraries' Scholarly Communications and Collections Strategy (SCCS) department in the implementation of the university's open access (OA) policies. Given an author's ID on [MIT's instance of Symplectic Elements](https://pubdata.mit.edu/), Solenoid retrieves citations for publications that either (a) have not been deposited (to DSpace) or (b) have not been requested. Users can build emails using Solenoid, which provides a standard template for publication requests that can be revised through the application. Users have the option of either (a) sending the email to the Liaison or (b) copying the contents of the generated email and sending the email to the author directly.

**Note:** Instructions for setting the system up for local development are in `docs/README.md`. The `system_architecture.xml` file is designed to be read by draw.io. There is a full maintenance plan on file with the PMO; `docs/maintenance.md` records developer-specific maintenance requirements in more detail. Some of this information may be outdated.

## Development

* To preview a list of available Makefile commands: `make help`
* To install with dev dependencies: `make install`
* To update dependencies: `make update`
* To run unit tests: `make test`
* To lint the repo: `make lint`
* To run the app: `pipenv run solenoid`

For local development and testing, the following environment variables are recommended:

```
   DJANGO_SECRET_KEY=<random-key>
   DJANGO_DEBUG=True
   DJANGO_LOGIN_REQUIRED=True # if testing login
```

The following sections provide a high-level overview for accessing Solenoid on a local machine and on Heroku. For more detailed walkthroughs and examples, please refer to our [internal documentation on Confluence (WIP)](https://mitlibraries.atlassian.net/l/cp/1hkcgkfG).

**Note:** Any tests that require a connection to Symplectic Elements must be performed through the `staging` app on Heroku. This can be done by manually deploying the `mitlibraries-solenoid-staging` app with the branch pointed to the Github branch under development.

### Running Solenoid on a local machine

1. Create a `.env` file at the root directory of the Solenoid repo, and set the environment variables recommended for local development and testing. 
   
2. If running the app locally for the first time, [create a user account](https://docs.djangoproject.com/en/5.0/topics/auth/default/#user-objects). For testing, it is recommended to create a 'superuser' account. This will be the username and password required to sign in to the locally hosted instance of Solenoid and needs to be entered if `DJANGO_LOGIN_REQUIRED=True.
   * If migration-related errors come up, run `python manage.py migrate`

3. Run the app: `pipenv run solenoid`.

4. View Solenoid by visiting the url: http://127.0.0.1:8000/. 

### Running Solenoid on Heroku

When running Solenoid on Heroku, only review and perform tests in **review apps**, applications that are automatically created when PRs are created in this repo, or in **`staging` apps (i.e., `mitlibraries-solenoid-staging`)**, applications that are automatically created when PRs are merged to `main` in this repo.

1. [OPTIONAL] Prior to launching a **review app**, you will need to create a user account for the application. 
   * Run this command in your terminal to create a 'superuser' account:
      ```
      heroku run --app=<heroku-app-name> python manage.py createsuperuser --username=<username> --email=<email>
      ```
2. Navigate to the `mitlibraries-solenoid` app on [Heroku Dashboard](https://dashboard.heroku.com/apps).
3. From the 'Pipeline' page, select the app linked to the Github PR under the 'Review Apps' column.
4. From the app's page, select `Settings`. 
5. Scroll down to 'Config Vars' and select `Reveal Config Vars`. Set the environment variables recommended for review and testing.
6. From the app's page, select `Open app`, which will launch Solenoid in a new tab.

## Environment variables

Environment variables are configured in Django settings files in `solenoid.settings`. For Solenoid, there are two settings files: 

* `base.py`: Base Django settings for Solenoid. In `manage.py`,a Python module that serves as a command-line utility for Django projects, the `DJANGO_SETTINGS_MODULE` env var is set to `solenoid.settings.base`. These are the settings used when running the app locally `pipenv run solenoid`.
* `heroku.py`: Base Django settings with additional configs specific to Heroku deployments. In `app.json`, an application manifest for Heroku, the `DJANGO_SETTINGS_MODULE` env var is set to `solenoid.settings.heroku`. These are the settings used when running the app on Heroku (i.e, via review apps or deployed Heroku applications in `staging` and `production`).

The Django settings files are modeled from the [sample `settings.py` file from Heroku](https://github.com/heroku/python-getting-started/blob/main/gettingstarted/settings.py), however, for organization purposes, the settings have been organized into two individual modules. It is recommended to take a closer look at how certain environment variables change when running the app on Heroku vs. locally, especially when debugging.

### Required

```
# Django refuses to start without a SECRET_KEY, derived from this env var. Set to any string value in 'dev'. In 'production', a 50-character random string is sufficient.
DJANGO_SECRET_KEY=
```

### Optional

```
# Runs the application in debug mode. It is recommended to set value to True for 'dev' and testing. In 'production', this value should be set to False. Default is False.
DJANGO_DEBUG=

# Requires users to log in to access the application. All requests by non-authenticated users will be redirected to the login page. For Heroku deployments, this value should be set to True. Default is False.
DJANGO_LOGIN_REQUIRED=

# The email address for the app's admins, used for the ADMINS Django setting. It is only used in 'dev', where the default is None. For Heroku deployments, the ADMINS Django setting is directly set to the 'solenoid-admins' Moira list.
SOLENOID_ADMIN=

# Password associated with the SMTP host and port specified in the EMAIL_HOST and EMAIL_PORT Django settings (i.e., for 'libsys@outgoing.mit.edu'). Default is None, which will write the emails that would be sent to standard output. For 'dev' and testing, only set the password if DJANGO_EMAIL_TESTING_MODE is True, which will send emails to the address indicated in the SOLENOID_ADMIN env var. For 'production', the password must be set.
DJANGO_SMTP_PASSWORD=

# Database connection string. In 'dev', the default is "sqlite:///db.sqlite3"; for Heroku deployments, this variable is set to a PostgreSQL connection string (configured by Heroku when the app is created).
DATABASE_URL=

# Heroku application name and indicates the host/domain name that the Django site can serve (i.e., used in the ALLOWED_HOSTS Django setting). In 'dev', this variable does not need to be set and defaults to an empty string; for Heroku deployments, this variable does not need to be explicitly set and defaults to 'mitlibraries-solenoid'. 
HEROKU_APP_NAME=

# Runs the application in test mode. Default is False, which will send emails to actual liasons and MIT's SCCS Full Text Acquisition (FTA) Moira list. For 'dev' and testing, set to True, which will send emails to the address indicated in the SOLENOID_ADMIN env var. For 'production', set to False.
DJANGO_EMAIL_TESTING_MODE=

# Send API requests to Symplectic Elements for citation imports. Default is False.
DJANGO_USE_ELEMENTS=

# Username associated with an API account for Symplectic Elements. Default is 'solenoid'. A value is required if DJANGO_USE_ELEMENTS is set to True.
DJANGO_ELEMENTS_USER=

# Password associated with an API account for Symplectic Elements. Default is None. A value is required if DJANGO_USE_ELEMENTS is set to True.
DJANGO_ELEMENTS_PASSWORD=

# API endpoint for Symplectic Elements. Defaults to the 'dev' instance of Elements. The 'prod' instance should never be used for testing unless it is absolutely necessary.
DJANGO_ELEMENTS_ENDPOINT=

# A salt (random data used as an additional input for a hash function) used to create a hash for the 'dspace_id' attribute of an 'Author' object. In 'dev', this can be set to any string value and the default is 'salty'; for Heroku deployments, defaults to the DJANGO_SECRET_KEY env var.
DSPACE_AUTHOR_ID_SALT=

# URL for Redis data store. In 'dev', the default is 'redis://localhost:6379/0'; for Heroku deployments, the corresponding config var (named similarly) is set to the URL for the newly provisioned Heroku Data for Redis instance upon creation.
REDIS_URL=
```
