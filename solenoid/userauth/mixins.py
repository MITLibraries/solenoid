from django import db
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
        # We've seen an OperationalError ('too many connections for role')
        # thrown from this part of the code. Those connections likely aren't
        # being left open here - this is solidly within the request/response
        # cycle and the db connection it opened to check
        # user.is_authenticated() should be closed by the view - but as long
        # as we've errored out here due to too many connections, may as well
        # close.
        db.close_old_connections()
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        if settings.LOGIN_REQUIRED:
            return login_required(view)
        else:
            return view
