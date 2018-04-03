# README.md

## Development
* Consult DLAD development guidelines at http://mitlibraries.github.io/ .
* The github repo is https://github.com/MITLibraries/solenoid .
* Make sure you have pipenv installed
* `pipenv install`
  * You only really need to install dev-packages.
  * The `certifi` dependency should be regularly updated (and will be auto-updated whenever you `pipenv install`).
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
* `DEBUG` defaults to False, as it should on production
  * If you want it to be True, `heroku config:set DJANGO_DEBUG=True`
* `git push heroku master`
* Required on the first deploy only: `heroku run python manage.py syncdb`
  * `heroku run python manage.py migrate` is run every time via a post-compile hook and a `bin/` script, so you don't need to do this, even if you have made database schema changes.
  * Pipeline apps don't need this - they run it via a postdeploy script in app.json.

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

The credentials for the production and staging OAuth providers are stored in a Solenoid note in DLE Lastpass.

## Integrating with Sympletic Elements

Solenoid issues calls to the Sympletic Elements API when it sends emails in order to mark items as requested. This requires some configuration on both the Elements system administration end and the solenoid end.

Sympletic Elements API documentation is visible to authorized users only.

### In Heroku (part 1)

Provision the following:
* Quotaguard Static
  * Note your IP addresses.
* Heroku Scheduler
  * Optional on staging

### In Elements

Following https://support.symplectic.co.uk/support/solutions/articles/6000049962-manage-the-elements-api :

* Ensure that the Standard 5.5 API is turned on.
  * _This should be https_ because we are sending password data
  * If it isn't marked as https, edit it to use https
  * Note its URL - you'll need this later.
* Authorize the static IP(s) of your server(s).
* Create an API account
  * Store the username and password in the Shared DLAD keys Lastpass folder - you'll need them later
  * 'solenoid' is the default username for the solenoid app, so you should probably use that unless you have a good reason not to
  * Make sure 'can modify data' is checked
  * The account does not need the other rights, so leave those unchecked

### In Heroku (part 2)

Set the following environment variables:
* `heroku config:set DJANGO_ELEMENTS_ENDPOINT=<your API endpoint>`
  * If the endpoint is the dev instance https://pubdata-dev.mit.edu:8091/secure-api/v5.5/, you can skip this step.
  * The trailing slash is important.
* `heroku config:set DJANGO_ELEMENTS_PASSWORD=<your API user password>`
* `heroku config:set DJANGO_ELEMENTS_USER=<your API user name>`
  * If you used 'solenoid' as your username you can skip this step.
* `heroku config:set DJANGO_USE_ELEMENTS_USER=True`

If you want to get emails with API monitoring information:
* `heroku addons:create scheduler:standard`
* `heroku addons:open scheduler`
* Add `python manage.py issue_unsent_calls` at your desired frequency
* Add `python manage.py notify_about_api` at your desired frequency (the management command assumes this will run daily)

### With Sympletic customer service

Notwithstanding the fact that you are using basic auth and you have whitelisted your IP(s), have customer service make a hole in the server's firewall for your IP(s) - you'll need all 3 to authenticate.

#### Sympletic API versions & other troubleshooting info

Solenoid requires API version >= 5.8 to function. (The library status field wasn't exposed until 5.8, per the release notes at https://support.symplectic.co.uk/support/solutions/articles/6000183912.)

However, this is listed in the API Endpoint dropdown as 5.5. Per discussions with Sympletic support, the 5.8 behavior has been added to the 5.5 release. So you should configure as if using 5.5, even though solenoid relies on 5.8.

__If you find that the API integration is behaving unexpectedly__, first check to see that the version exposed by the endpoint is the version you expect, keeping in mind that the version number of the endpoint need not correspond to the version number actually in use. You may have to contact customer service to verify.

__If you get 502 (Bad Gateway) errors__, check with Symplectic customer service to be sure your IPs are whitelisted in their firewall.

__If every call times out__, check the URLs to which they are issued; if it's missing the last part of the endpoint, make sure your env variable includes the trailing slash.
