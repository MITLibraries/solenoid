from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.UnsentList.as_view(), name='unsent_list')
]
