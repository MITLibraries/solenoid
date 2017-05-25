from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.UnsentList.as_view(), name='unsent_list'),
    url(r'^import/$', views.Import.as_view(), name='import'),
]
