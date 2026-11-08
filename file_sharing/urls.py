
from django.urls import path

from . import views

app_name = "file_sharing"

urlpatterns = [
    path(
        "meeting/<int:meeting_id>/",
        views.file_list,
        name="file_list",
    ),
    path(
        "meeting/<int:meeting_id>/upload/",
        views.upload_file,
        name="upload_file",
    ),
    path(
        "meeting/<int:meeting_id>/download/<int:file_id>/",
        views.download_file,
        name="download_file",
    ),
]
