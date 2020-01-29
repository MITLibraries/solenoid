release: python manage.py migrate
web: newrelic-admin run-program gunicorn solenoid.wsgi --log-file -
worker: celery -A solenoid worker -B --loglevel=info