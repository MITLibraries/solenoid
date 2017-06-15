# README.md

## Development
* Consult DLAD development guidelines at http://mitlibraries.github.io/ .
* The github repo is https://github.com/MITLibraries/solenoid .
* Set up a virtualenv for your project
* `pip install -r requirements/base.txt`
  * The requirements.txt file is there only for Heroku and installs `requirements/heroku.txt`
  * `requirements/base.txt` should contain dependencies that are required for all environemtns
  * `requirements/heroku.txt` is for things required only on Heroku
  * At minimum, the `certifi` dependency should be regularly updated.
* `python manage.py test` to run the tests
  * If you `pip install coverage`, you can `coverage run manage.py test` to get a coverage report along with running your test
  * There is a `.coveragerc` file which provides sensible defaults
  * `coverage html` will generate a nicely HTML-formatted report at `htmlcov/index.html`
* Static assets
  * If you have DEBUG=True:
    * `python manage.py collectstatic`
    * `python manage.py compress`
    * The order of these commands is important.
    * Restart runserver to see changes.
  * If you have DEBUG=False you're going to have to figure out how to serve static on localhost.

## Deploying to Heroku
The app deploys to mitlibraries-solenoid.herokuapp.com, with the libdev-cs credentials. It's connected to the MITLibraries github and has Heroku pipelines set up, so it will automatically:
* create review apps for all pull requests
* put the latest master on mitlibraries-solenoid-staging
  * You can (and should) set it to only deploy if tests pass

You can then one-click promote staging to production through the Dashboard, if desired.
* This does _not_ run post-compile hooks, but it _does_ run [release tasks defined in the Procfile](https://devcenter.heroku.com/articles/release-phase)
* Therefore database migrations are called in the Procfile, not in a post-compile hook
* Release tasks run as part of both app build and pipeline promotion, so we get this on both staging and production
* We don't need to set a collectstatic release task because Heroku does that automatically during app build (and this is then copied over from staging during promotion)

If for some reason you wanted to set it up from scratch, you'd need to do the following:
* Set up a Heroku instance associated with your repository (https://devcenter.heroku.com/articles/deploying-python)
* Add its URL to `ALLOWED_HOSTS` in `settings/heroku.py`
* Provision the following apps (the free tier is fine):
  * Postgres
  * Quotaguard Static
  * Heroku Scheduler
    * Optional on staging
  * Newrelic
    * This is optional - you can live on the edge if you don't like logging - but if you don't have it, you need to edit the Procfile to take out the newrelic run-program parts
  * Papertrail
  * Rollbar
    * Papertrail and Rollbar are also optional if you are from the YOLO school of devops
* `heroku config:set DJANGO_SECRET_KEY=<a secret key>`
  * Can be anything; a 50-character random string is reasonable.
* `heroku config:set DJANGO_SETTINGS_MODULE=solenoid.settings.heroku`
* `heroku config:set DJANGO_SMTP_PASSWORD=<the MIT libsys password>`
  * This is in the Lastpass DLAD shared notes folder.
  * Make sure to read the part about escaping special characters.
* `heroku config:set WEB_CONCURRENCY=3`
* `heroku config:set DJANGO_EMAIL_TESTING_MODE=False`
  * If you want to send email to real liaisons and the scholcomm moira list, set this
  * If it is anything else, or unset, emails will be sent to settings.ADMINS only
  * This allows for testing email in a production-like environment without spamming people
* `heroku pg:backups:schedule DATABASE_URL --at "02:00" --app mitlibraries-solenoid`
  * Or whatever time/app/database color name is relevant to you
  * The Heroku docs say `--at "{time} {timezone}"` but that doesn't seem to work
* For OAuth2:
  * `heroku config:set DJANGO_MITOAUTH2_KEY=<your MIT OAuth key>`
  * `heroku config:set DJANGO_MITOAUTH2_SECRET=<your MIT OAuth secret>`
  * You can turn OAuth off with `heroku config:unset DJANGO_LOGIN_REQUIRED`, but you probably shouldn't.
  * See below for more on OAuth; you'll need to have configured it on the MIT side.
* For Elements:
  * `heroku config:set DJANGO_ELEMENTS_ENDPOINT=<your API endpoint>`
  * `heroku config:set DJANGO_ELEMENTS_PASSWORD=<your API user password>`
  * `heroku config:set DJANGO_ELEMENTS_USER=<your API user name>`
    * If you used 'solenoid' as your username you can skip this step.
  * If you want to get emails with API monitoring information:
    * `heroku addons:create scheduler:standard`
    * `heroku addons:open scheduler`
    * Add `python manage.py notify_about_api` at your desired frequency (the management command assumes this will run daily)
  * See below for more on Elements; you'll need to have configured it on the Symplectic side.
* `DEBUG` defaults to False, as it should on production
  * If you want it to be True, `heroku config:set DJANGO_DEBUG=True`
* `git push heroku master`
* Required on the first deploy only: `heroku run python manage.py syncdb`
  * `heroku run python manage.py migrate` is run every time via a post-compile hook and a `bin/` script, so you don't need to do this, even if you have made database schema changes.

You don't need to set up S3 - Heroku suffices for serving static on an app this low-traffic.

### OAuth and sensitive data

The project specification requires that the final product be limited to
authorized users. Therefore production must use OAuth, and all Heroku servers use it by default.

ITDD's Heroku + OpenID policy requires that sensitive data not be stored
on Heroku. (See https://infoprotect.mit.edu/what-needs-protecting for more details on sensitive data.)

The data files exported from Sympletic contain MIT IDs, which are explicitly sensitive data under MIT policy. However, we do not store this information on Heroku. We store *hashes* of MIT IDs, which allow us to verify that two authors are indeed distinct, but do not compromise their data. The rest of the data that we store is explicitly public information (for instance, metadata of published papers, or email addresses available through the public MIT directory).

Because we don't store sensitive data offsite, it is okay to turn OAuth off on test servers. However, think carefully whether those test servers are configured to send email before doing so; it isn't okay for our Heroku review apps to turn into gateways for spamming liaison librarians.

### Who can log in

The python-social-auth pipeline (see `solenoid.userauth.backends`) first confirms with the MIT OAuth server that the user has a kerb; it then checks their MIT email against a whitelist defined in `settings.SOCIAL_AUTH_WHITELISTED_EMAILS`.

__Only people on this whitelist will be allowed to log in.__ If the desired access list changes, edit this settings variable.

Change `settings.WHITELIST` if you'd like to alter the set of people allowed to
log in.

### Configuring your MIT OAuth provider
Register an OAuth client at https://oidc.mit.edu with the following parameters:
* Main:
  * Redirect URI: `<your base URL>/oauth2/complete/mitoauth2/`
* Access:
  * grant types: authorization code
  * response types: code
  * scope: email, openid

Defaults are fine for everything else.

## Integrating with Sympletic Elements

Solenoid issues calls to the Sympletic Elements API when it sends emails in order to mark items as requested. This requires some configuration on both the Elements system administration end and the solenoid end.

Sympletic Elements API documentation is visible to authorized users only.

### In Heroku

You'll need to set up a static IP. https://devcenter.heroku.com/articles/quotaguardstatic#using-with-python-django is free for up to 250 requests/month.

### In Elements

Following https://support.symplectic.co.uk/support/solutions/articles/6000049962-manage-the-elements-api :

* Ensure that the Standard 5.5 API is turned on.
  * _This should be https_ because we are sending password data
  * If it isn't marked as https, edit it to use https
  * Note its URL - you'll need this later.
* Authorize the static IP of your server(s).
* Create an API account
  * Store the username and password in the Shared DLAD keys Lastpass folder - you'll need them later
  * 'solenoid' is the default username for the solenoid app, so you should probably use that unless you have a good reason not to
  * Make sure 'can modify data' is checked
  * The account does not need the other rights, so leave those unchecked

### In solenoid

* Set an environment variable, `DJANGO_ELEMENTS_ENDPOINT`, matching the API URL you noted earlier.
  * If the endpoint is the dev instance https://pubdata-dev.mit.edu:8091/secure-api/v5.5/, you can skip this step.
* Set an environment variable, `DJANGO_ELEMENTS_PASSWORD`, with the API user password you noted earlier.
* Set an environment variable `DJANGO_ELEMENTS_USER` with the username of your API user.
  * If the username is 'solenoid', you can skip this step.

### With Sympletic customer service

Notwithstanding the fact that you are using basic auth and you have whitelisted your IP(s), have customer service make a hole in the server's firewall for your IP(s) - you'll need all 3 to authenticate.
