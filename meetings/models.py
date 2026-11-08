
import os
import uuid

from django.conf import settings
from django.db import models


def recording_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    return f"meeting_recordings/{instance.meeting_id}/{uuid.uuid4().hex}{extension}"


class Meeting(models.Model):
    title = models.CharField(max_length=150)

    room_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_meetings",
    )

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="joined_meetings",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Nullable so existing database rows can be migrated safely.
    # Newly created meetings will require both values in the form.
    scheduled_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    scheduled_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title

    def has_started(self):
        from django.utils import timezone

        return (
            self.scheduled_start is None
            or timezone.now() >= self.scheduled_start
        )

    def has_ended(self):
        from django.utils import timezone

        return (
            not self.is_active
            or (
                self.scheduled_end is not None
                and timezone.now() >= self.scheduled_end
            )
        )

    def can_be_joined(self):
        return (
            self.is_active
            and self.has_started()
            and not self.has_ended()
        )


class MeetingRecording(models.Model):
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="recordings",
    )

    file = models.FileField(
        upload_to=recording_upload_path,
    )

    original_name = models.CharField(
        max_length=255,
        default="meeting-recording.webm",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_meeting_recordings",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recording: {self.meeting.title}"
