from django.urls import re_path

from . import views

app_name = 'emails'

urlpatterns = [
    re_path(r'^create/$', views.EmailCreate.as_view(), name='create'),
    re_path(r'^(?P<pk>\d+)/$', views.EmailEvaluate.as_view(), name='evaluate'),
    re_path(r'^send/$', views.EmailSend.as_view(), name='send'),
    re_path(r'^$', views.EmailListPending.as_view(), name='list_pending'),
    re_path(r'^liaison/(?P<pk>\d+)/$', views.EmailLiaison.as_view(),
            name='get_liaison'),
    re_path(r'^rebuild/(?P<pk>\d+)/$', views.EmailRebuild.as_view(),
            name='rebuild'),
    ]
