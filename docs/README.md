# README.md

## Deploying to Heroku
The app deploys to mitlibraries-solenoid.herokuapp.com, with the libdev-cs credentials.

* `heroku config:set DJANGO_SECRET_KEY=<a secret key>`
* `heroku config:set DJANGO_SETTINGS_MODULE=solenoid.settings.heroku`
* If you want `DEBUG=False` (e.g. on production):
  * `heroku config:unset DJANGO_DEBUG`
* Else `heroku config:set DJANGO_DEBUG=True`
  * Actually any non-null value for this setting will result in DEBUG being True.
* `git push heroku master`
