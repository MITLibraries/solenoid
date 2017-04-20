from django.http import HttpResponse
from django.views.generic.base import View


def email_bulk_create(pk_list):
    pass


class EmailCreate(View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk_list = request.POST.getlist('records')
        email_bulk_create(pk_list)
        return HttpResponse('yo')

