from django.urls import re_path

from . import views

app_name = "people"

urlpatterns = [
    re_path(r"^new$", views.LiaisonCreate.as_view(), name="liaison_create"),
    re_path(r"^$", views.LiaisonList.as_view(), name="liaison_list"),
    re_path(r"^(?P<pk>\d+)/$", views.LiaisonUpdate.as_view(), name="liaison_update"),
    re_path(
        r"^delete/(?P<pk>\d+)/$", views.LiaisonDelete.as_view(), name="liaison_delete"
    ),
]
