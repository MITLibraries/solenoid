from django.conf import settings
from django.contrib.auth.mixins import AccessMixin


class ConditionalLoginRequiredMixin(AccessMixin):
    """
    Requires users to log in if (and only if) settings.LOGIN_REQUIRED is True.
    This makes it easy to require login on production but not test.

    It is written by analogy with django.contrib.auth.mixins.LoginRequiredMixin
    but includes the conditional settings check.
    """
    def dispatch(self, request, *args, **kwargs):
        if (settings.LOGIN_REQUIRED and
                not getattr(request.user, 'is_authenticated')):
            return self.handle_no_permission()
        return super(ConditionalLoginRequiredMixin, self
                     ).dispatch(request, *args, **kwargs)
