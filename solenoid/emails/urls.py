from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^create/$', views.EmailCreate.as_view(), name='create'),
    url(r'^(?P<pk>\d+)/$', views.EmailEvaluate.as_view(), name='evaluate'),
    url(r'^send/$', views.EmailSend.as_view(), name='send'),
    url(r'^$', views.EmailListPending.as_view(), name='list_pending'),
]
