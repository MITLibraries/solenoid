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
  * Currently the app is pre-alpha and has a number of intentionally failing tests
  * This will become unacceptable later
* Static assets
  * To run the stylesheet compiler/compressor, you need to:
    * Install npm
    * `npm install`
    * `./node_modules/grunt-cli/bin/grunt django_compressor`
    * `gem install sass`
    * `python manage.py collectstatic`
    * `python manage.py compress`
    * Note that it will only run if DEBUG=False

## Deploying to Heroku
The app deploys to mitlibraries-solenoid.herokuapp.com, with the libdev-cs credentials. It's connected to the MITLibraries github and has Heroku pipelines set up, so it will automatically:
* create review apps for all pull requests
* put the latest master on mitlibraries-solenoid-staging

If for some reason you wanted to set it up from scratch, you'd need to do the following:
* Set up a Heroku instance associated with your repository (https://devcenter.heroku.com/articles/deploying-python)
* `heroku buildpacks:set heroku/python`
* `heroku buildpacks:add --index 1 heroku/nodejs`
  * This is needed to run the grunt task that compiles and compresses assets.
* `heroku config:set DJANGO_SECRET_KEY=<a secret key>`
  * Can be anything; a 50-character random string is reasonable.
* `heroku config:set DJANGO_SETTINGS_MODULE=solenoid.settings.heroku`
* `heroku config:set DJANGO_SMTP_PASSWORD=<the MIT libsys password>`
  * This is in the Lastpass DLAD shared notes folder.
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
  * See below for more on Elements; you'll need to have configured it on the Symplectic side.
* If you want `DEBUG=False` (e.g. on production):
  * `heroku config:unset DJANGO_DEBUG`
  * Else `heroku config:set DJANGO_DEBUG=True`
* `git push heroku master`
* Required on the first deploy only: `heroku run python manage.py syncdb`
* `heroku run python manage.py migrate`
  * Technically this is only needed if you have changed the database schema, but it won't hurt to run it regardless, so you may as well do it every time

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
  * If the endpoint is the dev instance https://pubdata-dev.mit.edu:8091/secure-api/v5.5, you can skip this step.
* Set an environment variable, `DJANGO_ELEMENTS_PASSWORD`, with the API user password you noted earlier.
* Set an environment variable `DJANGO_ELEMENTS_USER` with the username of your API user.
  * If the username is 'solenoid', you can skip this step.
