release: python manage.py migrate
web: newrelic-admin run-program gunicorn solenoid.wsgi --worker-class gevent --log-file -
