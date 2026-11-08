from django.contrib import admin
from .models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("title", "room_code", "host", "created_at", "is_active")
    search_fields = ("title", "room_code", "host__username")
    list_filter = ("is_active", "created_at")