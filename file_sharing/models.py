
import os

from django.conf import settings
from django.db import models


def shared_file_upload_path(instance, filename):
    safe_name = os.path.basename(filename)
    return (
        f"shared_files/{instance.meeting_id or 'unassigned'}/"
        f"{instance.uploaded_by_id}/{safe_name}"
    )


class SharedFile(models.Model):
    meeting = models.ForeignKey(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="shared_files",
        null=True,
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shared_files",
    )

    file = models.FileField(upload_to=shared_file_upload_path)
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size

        if self.file and not self.original_name:
            self.original_name = os.path.basename(self.file.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name or "Shared file"
