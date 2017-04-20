from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.EmailCreate.as_view(), name='create'),
]
