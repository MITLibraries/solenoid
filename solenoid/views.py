from django.urls import reverse
from django.views.generic.base import TemplateView

from solenoid.people.models import Liaison
from solenoid.mixins import ConditionalLoginRequiredMixin


class HomeView(ConditionalLoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):  # type: ignore
        context = super(HomeView, self).get_context_data(**kwargs)
        if Liaison.objects.count():
            context["liaison_url"] = reverse("people:liaison_list")
            context["liaison_text"] = "manage"
        else:
            context["liaison_url"] = reverse("people:liaison_create")
            context["liaison_text"] = "create"

        return context
