from django.apps import AppConfig


class EmailsConfig(AppConfig):
    name = "solenoid.emails"

    def ready(self) -> None:
        from .signals import email_sent
