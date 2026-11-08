
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from meetings.models import Meeting

from .forms import SharedFileForm
from .models import SharedFile


def get_accessible_meeting(meeting_id, user):
    meeting = get_object_or_404(
        Meeting,
        pk=meeting_id,
        is_active=True,
    )

    is_member = (
        meeting.host_id == user.id
        or meeting.participants.filter(pk=user.pk).exists()
    )

    if not is_member:
        # Return 404 rather than revealing meeting details.
        raise Http404("Meeting not found.")

    return meeting


@login_required
def file_list(request, meeting_id):
    meeting = get_accessible_meeting(meeting_id, request.user)

    files = (
        SharedFile.objects
        .filter(meeting=meeting)
        .select_related("uploaded_by")
    )

    return render(
        request,
        "file_sharing/file_list.html",
        {
            "meeting": meeting,
            "files": files,
            "form": SharedFileForm(),
        },
    )


@login_required
@require_POST
def upload_file(request, meeting_id):
    meeting = get_accessible_meeting(meeting_id, request.user)

    form = SharedFileForm(request.POST, request.FILES)

    if form.is_valid():
        uploaded_file = form.cleaned_data["file"]

        shared_file = form.save(commit=False)
        shared_file.meeting = meeting
        shared_file.uploaded_by = request.user
        shared_file.original_name = os.path.basename(
            uploaded_file.name
        )
        shared_file.file_size = uploaded_file.size
        shared_file.save()

        messages.success(request, "File uploaded successfully.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect(
        "file_sharing:file_list",
        meeting_id=meeting.pk,
    )


@login_required
def download_file(request, meeting_id, file_id):
    meeting = get_accessible_meeting(meeting_id, request.user)

    shared_file = get_object_or_404(
        SharedFile,
        pk=file_id,
        meeting=meeting,
    )

    try:
        file_handle = shared_file.file.open("rb")
    except (OSError, ValueError, SuspiciousFileOperation):
        raise Http404("File is unavailable.")

    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=os.path.basename(shared_file.original_name),
    )
