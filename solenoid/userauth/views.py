from django.contrib.auth.views import LogoutView
from social_django.utils import load_strategy


class SolenoidLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        backend = self._get_backend_instance(request)
        backend.revoke(request.user)
        return super(SolenoidLogoutView, self).dispatch(
            request, *args, **kwargs)

    def _get_backend_instance(self, request):
        strategy = load_strategy()
        backend = request.user.social_auth.get().get_backend(strategy)
        return backend(strategy=strategy)
