"""solenoid URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.views.defaults import server_error

from .views import HomeView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^records/', include('solenoid.records.urls', namespace='records')),
    url(r'^emails/', include('solenoid.emails.urls', namespace='emails')),
    url(r'^people/', include('solenoid.people.urls', namespace='people')),
    url(r'^oauth2/', include('social_django.urls', namespace='social')),
    url(r'^logout/$', LogoutView.as_view(template_name='userauth/logout.html'),
        name='logout'),
    url(r'^500/$', server_error),
]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
