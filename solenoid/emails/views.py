from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.list import ListView

from .models import Email

def email_bulk_create(pk_list):
    pass


class EmailCreate(View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk_list = request.POST.getlist('records')
        email_bulk_create(pk_list)
        return HttpResponseRedirect(reverse('emails:evaluate'))

class EmailEvaluate(ListView):
    queryset = Email.objects.filter(date_sent__isnull=True)
