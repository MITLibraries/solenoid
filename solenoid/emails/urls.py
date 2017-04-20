from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^create$', views.EmailCreate.as_view(), name='create'),
    url(r'^$', views.EmailEvaluate.as_view(), name='evaluate'),
]
