from django.conf.urls import url

from . import views

app_name = 'people'

urlpatterns = [
    url(r'^new$', views.LiaisonCreate.as_view(), name='liaison_create'),
    url(r'^$', views.LiaisonList.as_view(), name='liaison_list'),
    url(r'^(?P<pk>\d+)/$', views.LiaisonUpdate.as_view(),
        name='liaison_update'),
    url(r'^delete/(?P<pk>\d+)/$', views.LiaisonDelete.as_view(),
        name='liaison_delete'),
]
