
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import dashboard_view


urlpatterns = [
    # Homepage redirects to the dashboard
    path(
        "",
        RedirectView.as_view(
            url="/dashboard/",
            permanent=False,
        ),
        name="home",
    ),

    # Authentication and profile URLs
    path(
        "",
        include("accounts.urls"),
    ),

    # Django admin
    path(
        "admin/",
        admin.site.urls,
    ),

    # User dashboard
    path(
        "dashboard/",
        dashboard_view,
        name="dashboard",
    ),

    # Meeting and video conferencing
    path(
        "meetings/",
        include("meetings.urls"),
    ),

    # File sharing
    path(
        "files/",
        include("file_sharing.urls"),
    ),
]
