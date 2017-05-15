from django.views.generic.base import TemplateView

from solenoid.userauth.mixins import LoginRequiredMixin


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'
