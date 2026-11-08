
from django.urls import path

from .consumers import MeetingConsumer


websocket_urlpatterns = [
    path(
        "ws/meetings/<str:room_code>/",
        MeetingConsumer.as_asgi(),
        name="meeting_websocket",
    ),
]
