import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "solenoid.settings.base")

app = Celery("solenoid")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self) -> None:  # type: ignore
    print("Request: {0!r}".format(self.request))
