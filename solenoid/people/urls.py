from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^new$', views.LiaisonCreate.as_view(), name='liaison_create'),
    url(r'^$', views.LiaisonList.as_view(), name='liaison_list'),
    url(r'^update/(?P<pk>\d+)/$', views.LiaisonUpdate.as_view(),
        name='liaison_update'),
]
