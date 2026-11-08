
from django.contrib import admin
from .models import SharedFile


@admin.register(SharedFile)
class SharedFileAdmin(admin.ModelAdmin):
    list_display = (
        "original_name",
        "uploaded_by",
        "file_size",
        "uploaded_at",
    )

    search_fields = (
        "original_name",
        "uploaded_by__username",
    )

    list_filter = ("uploaded_at",)
    readonly_fields = ("uploaded_at", "file_size")
