# README.md

## Deploying to Heroku
The app deploys to mitlibraries-solenoid.herokuapp.com, with the libdev-cs credentials. It's connected to the MITLibraries github and has Heroku pipelines set up, so it will automatically:
* create review apps for all pull requests
* put the latest master on mitlibraries-solenoid-staging

If for some reason you wanted to set it up from scratch, you'd need to do the following:
* `heroku config:set DJANGO_SECRET_KEY=<a secret key>`
* `heroku config:set DJANGO_SETTINGS_MODULE=solenoid.settings.heroku`
* If you want `DEBUG=False` (e.g. on production):
  * `heroku config:unset DJANGO_DEBUG`
* Else `heroku config:set DJANGO_DEBUG=True`
  * Actually any non-null value for this setting will result in DEBUG being True.
* `git push heroku master`
* `heroku run python manage.py syncdb`
  * This is required on the first deploy only
  * On subsequent deploys, if and only if you have changed the database schema, you will need `heroku run python manage.py migrate`
