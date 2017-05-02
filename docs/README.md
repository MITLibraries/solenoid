# README.md

## Deploying to Heroku
The app deploys to mitlibraries-solenoid.herokuapp.com, with the libdev-cs credentials. It's connected to the MITLibraries github and has Heroku pipelines set up, so it will automatically:
* create review apps for all pull requests
* put the latest master on mitlibraries-solenoid-staging

If for some reason you wanted to set it up from scratch, you'd need to do the following:
* Set up a Heroku instance associated with your repository (https://devcenter.heroku.com/articles/deploying-python)
* `heroku config:set DJANGO_SECRET_KEY=<a secret key>`
* `heroku config:set DJANGO_SETTINGS_MODULE=solenoid.settings.heroku`
* For OAuth2:
  * `heroku config:set DJANGO_MITOAUTH2_KEY=<your MIT OAuth key>`
  * `heroku config:set DJANGO_MITOAUTH2_SECRET=<your MIT OAuth secret>`
  * You can turn OAuth off with `heroku config:unset DJANGO_LOGIN_REQUIRED`, but you probably shouldn't.
  * See below for more on OAuth.
* If you want `DEBUG=False` (e.g. on production):
  * `heroku config:unset DJANGO_DEBUG`
* Else `heroku config:set DJANGO_DEBUG=True`
  * Actually any non-null value for this setting will result in DEBUG being True.
* `git push heroku master`
* `heroku run python manage.py syncdb`
  * This is required on the first deploy only
  * On subsequent deploys, if and only if you have changed the database schema, you will need `heroku run python manage.py migrate`

### OAuth and sensitive data

The project specification requires that the final product be limited to
authorized users. Therefore production must use OAuth, and all Heroku servers use it by default.

ITDD's Heroku + OpenID policy requires that sensitive data not be stored
on Heroku. (See https://infoprotect.mit.edu/what-needs-protecting for more details on sensitive data.)

The data files exported from Sympletic contain MIT IDs, which are explicitly sensitive data under MIT policy. However, we do not store this information on Heroku. We store *hashes* of MIT IDs, which allow us to verify that two authors are indeed distinct, but do not compromise their data. The rest of the data that we store is explicitly public information (for instance, metadata of published papers, or email addresses available through the public MIT directory).

Because we don't store sensitive data offsite, it is okay to turn OAuth off on test servers. However, think carefully whether those test servers are configured to send email before doing so; it isn't okay for our Heroku review apps to turn into gateways for spamming liaison librarians.

## Development
* Consult DLAD development guidelines at http://mitlibraries.github.io/ .
* The github repo is https://github.com/MITLibraries/solenoid .
* Set up a virtualenv for your project
* `pip install -r requirements/base.txt`
  * The requirements.txt file is there only for Heroku and installs `requirements/heroku.txt`
  * `requirements/base.txt` should contain dependencies that are required for all environemtns
  * `requirements/heroku.txt` is for things required only on Heroku
* `python manage.py test` to run the tests
  * Currently the app is pre-alpha and has a number of intentionally failing tests
  * This will become unacceptable later
