from django.views.generic.base import TemplateView

from solenoid.people.models import Liaison, DLC
from solenoid.userauth.mixins import LoginRequiredMixin


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['dlcs_exist'] = bool(DLC.objects.count())
        context['liaisons_exist'] = bool(Liaison.objects.count())
        return context
