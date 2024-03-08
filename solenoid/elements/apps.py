from django.apps import AppConfig


class ElementsConfig(AppConfig):
    name = "solenoid.elements"

    def ready(self):
        from .views import wrap_elements_api_call
