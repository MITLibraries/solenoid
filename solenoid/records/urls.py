from django.urls import re_path
from django.views.generic import TemplateView

from . import views

app_name = 'records'

urlpatterns = [
    re_path(r'^$', views.UnsentList.as_view(), name='unsent_list'),
    re_path(r'^import/$', views.Import.as_view(), name='import'),
    re_path(r'^import/status/(?P<task_id>[^/]+)/$', views.status,
            name="status"),
    re_path(r'^instructions/$',
            TemplateView.as_view(template_name="records/instructions.html"),
            name='instructions'),
    ]
