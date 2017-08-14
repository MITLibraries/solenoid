release: python manage.py migrate ; python manage.py compress
web: newrelic-admin run-program gunicorn solenoid.wsgi --worker-class gevent --log-file -
