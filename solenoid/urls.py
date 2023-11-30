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
from django.contrib import admin
from django.urls import include, re_path
from django.views.defaults import server_error
from django.views.generic.base import RedirectView

from .views import HomeView

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(
        r"^accounts/",
        include("solenoid.accounts.urls", namespace="accounts"),
    ),
    re_path(r"^$", HomeView.as_view(), name="home"),
    re_path(
        r"^celery-progress/", include("celery_progress.urls", namespace="celery_progress")
    ),
    re_path(r"^records/", include("solenoid.records.urls", namespace="records")),
    re_path(r"^emails/", include("solenoid.emails.urls", namespace="emails")),
    re_path(r"^people/", include("solenoid.people.urls", namespace="people")),
    re_path(
        r"^logout/$",
        RedirectView.as_view(url="/accounts/logout"),
        name="logout",
    ),
    re_path(r"^500/$", server_error),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
