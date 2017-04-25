from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^new$', views.LiaisonCreate.as_view(), name='liaison_create'),
]
