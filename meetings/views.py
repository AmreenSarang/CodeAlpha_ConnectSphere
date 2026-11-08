
import os
from datetime import datetime
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .models import Meeting, MeetingRecording


def user_is_member(meeting, user):
    """Only the host and authorized participants can access a meeting."""
    return (
        meeting.host_id == user.id
        or meeting.participants.filter(pk=user.pk).exists()
    )


def parse_local_datetime(value):
    """Parse a datetime-local input using Django's current timezone."""
    if not value:
        raise ValueError("Both meeting start and end times are required.")

    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except (ValueError, TypeError) as exc:
        raise ValueError("Enter valid meeting start and end times.") from exc

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(
            parsed,
            timezone.get_current_timezone(),
        )

    return parsed


def meeting_has_ended(meeting):
    """A meeting ends when it is inactive or its end time has passed."""
    if not meeting.is_active:
        return True

    return (
        meeting.scheduled_end is not None
        and timezone.now() >= meeting.scheduled_end
    )


@login_required
def meeting_list(request):
    hosted_meetings = (
        Meeting.objects.filter(host=request.user)
        .order_by("-created_at")
    )

    joined_meetings = (
        request.user.joined_meetings
        .exclude(host=request.user)
        .distinct()
        .order_by("-created_at")
    )

    return render(
        request,
        "meetings/meeting_list.html",
        {
            "meetings": hosted_meetings,
            "hosted_meetings": hosted_meetings,
            "joined_meetings": joined_meetings,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_meeting(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()

        if not title:
            messages.error(request, "Please enter a meeting title.")
            return render(request, "meetings/create_meeting.html")

        if len(title) > 150:
            messages.error(
                request,
                "Meeting title cannot exceed 150 characters.",
            )
            return render(request, "meetings/create_meeting.html")

        try:
            start = parse_local_datetime(
                request.POST.get("scheduled_start", "")
            )
            end = parse_local_datetime(
                request.POST.get("scheduled_end", "")
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, "meetings/create_meeting.html")

        now = timezone.now()

        if start <= now:
            messages.error(
                request,
                "The meeting start time must be in the future.",
            )
            return render(request, "meetings/create_meeting.html")

        if end <= start:
            messages.error(
                request,
                "The meeting end time must be later than its start time.",
            )
            return render(request, "meetings/create_meeting.html")

        meeting = Meeting.objects.create(
            title=title,
            host=request.user,
            scheduled_start=start,
            scheduled_end=end,
        )
        meeting.participants.add(request.user)

        messages.success(
            request,
            "Meeting scheduled successfully. You can enter the room early.",
        )

        return redirect(
            "meetings:meeting_room",
            room_code=meeting.room_code,
        )

    return render(request, "meetings/create_meeting.html")


@login_required
@require_POST
def join_meeting(request):
    room_code = request.POST.get("room_code", "").strip()

    try:
        parsed_room_code = UUID(room_code)
    except (ValueError, TypeError, AttributeError):
        messages.error(
            request,
            "Please enter a valid meeting room code.",
        )
        return redirect("meetings:meeting_list")

    meeting = get_object_or_404(
        Meeting,
        room_code=parsed_room_code,
    )

    if meeting_has_ended(meeting):
        messages.error(
            request,
            "This meeting has ended or is no longer active.",
        )
        return redirect("meetings:meeting_list")

    # Participants can join before the scheduled start time.
    meeting.participants.add(request.user)

    messages.success(
        request,
        f"You joined '{meeting.title}' successfully.",
    )

    return redirect(
        "meetings:meeting_room",
        room_code=meeting.room_code,
    )


@login_required
def meeting_room(request, room_code):
    meeting = get_object_or_404(
        Meeting,
        room_code=room_code,
    )

    if not user_is_member(meeting, request.user):
        messages.error(
            request,
            "You are not authorized to access this meeting.",
        )
        return redirect("meetings:meeting_list")

    if meeting_has_ended(meeting):
        recording = meeting.recordings.order_by("-uploaded_at").first()

        if recording:
            return redirect(
                "meetings:recording_detail",
                recording_id=recording.pk,
            )

        return render(
            request,
            "meetings/meeting_waiting.html",
            {
                "meeting": meeting,
                "meeting_ended": True,
                "recording_available": False,
            },
        )

    # IMPORTANT:
    # Do not block access because scheduled_start is in the future.
    # Authorized participants may open the live meeting room early.
    return render(
        request,
        "meetings/meeting_room.html",
        {
            "meeting": meeting,
            "room_code": meeting.room_code,
        },
    )


@login_required
@require_POST
def upload_recording(request, room_code):
    meeting = get_object_or_404(
        Meeting,
        room_code=room_code,
    )

    if meeting.host_id != request.user.id:
        raise Http404("Recording not found.")

    if not meeting_has_ended(meeting):
        messages.error(
            request,
            "Upload the recording after the meeting ends.",
        )
        return redirect(
            "meetings:meeting_room",
            room_code=meeting.room_code,
        )

    uploaded_file = request.FILES.get("recording")

    if not uploaded_file:
        messages.error(request, "Please select a recording file.")
        return redirect("meetings:meeting_list")

    extension = os.path.splitext(uploaded_file.name)[1].lower()

    if extension not in {".webm", ".mp4"}:
        messages.error(
            request,
            "Only WebM and MP4 recordings are supported.",
        )
        return redirect("meetings:meeting_list")

    if uploaded_file.size > 500 * 1024 * 1024:
        messages.error(
            request,
            "The recording must not exceed 500 MB.",
        )
        return redirect("meetings:meeting_list")

    recording = MeetingRecording.objects.create(
        meeting=meeting,
        file=uploaded_file,
        original_name=os.path.basename(uploaded_file.name),
        uploaded_by=request.user,
    )

    messages.success(request, "Meeting recording uploaded successfully.")

    return redirect(
        "meetings:recording_detail",
        recording_id=recording.pk,
    )


@login_required
def recording_detail(request, recording_id):
    recording = get_object_or_404(
        MeetingRecording.objects.select_related("meeting"),
        pk=recording_id,
    )

    meeting = recording.meeting

    if not user_is_member(meeting, request.user):
        raise Http404("Recording not found.")

    if not meeting_has_ended(meeting):
        messages.error(
            request,
            "The recording is available after the meeting ends.",
        )
        return redirect("meetings:meeting_list")

    return render(
        request,
        "meetings/recording_detail.html",
        {
            "recording": recording,
            "meeting": meeting,
        },
    )


@login_required
def play_recording(request, recording_id):
    recording = get_object_or_404(
        MeetingRecording.objects.select_related("meeting"),
        pk=recording_id,
    )

    meeting = recording.meeting

    if not user_is_member(meeting, request.user):
        raise Http404("Recording not found.")

    if not meeting_has_ended(meeting):
        raise Http404("Recording is not available yet.")

    try:
        file_handle = recording.file.open("rb")
    except (OSError, ValueError, SuspiciousFileOperation):
        raise Http404("Recording file is unavailable.")

    extension = os.path.splitext(recording.original_name)[1].lower()
    content_type = (
        "video/mp4" if extension == ".mp4" else "video/webm"
    )

    response = FileResponse(
        file_handle,
        content_type=content_type,
    )
    response["Content-Disposition"] = "inline"
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"

    return response


@login_required
def websocket_test(request):
    return render(request, "meetings/websocket_test.html")
