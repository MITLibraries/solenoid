from django.conf.urls import url
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    url(r'^$', views.UnsentList.as_view(), name='unsent_list'),
    url(r'^import/$', views.Import.as_view(), name='import'),
    url(r'^instructions/$',
        TemplateView.as_view(template_name="records/instructions.html"),
        name='instructions'),
]
