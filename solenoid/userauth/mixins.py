from django.conf import settings
from django.contrib.auth.decorators import login_required


class LoginRequiredMixin(object):
    """
    Requires users to log in if (and only if) settings.LOGIN_REQUIRED is True.
    This makes it easy to require login on production but not test.
    Use as a mixin for a class-based view; e.g.

    class ProtectedView(LoginRequiredMixin, ...):
    """
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        if settings.LOGIN_REQUIRED:
            return login_required(view)
        else:
            return view
