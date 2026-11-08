
from django.urls import path

from . import views



app_name = "meetings"


urlpatterns = [

    # ==========================================
    # MEETING LIST
    # ==========================================

    path(
        "",
        views.meeting_list,
        name="meeting_list"
    ),

    # ==========================================
    # CREATE MEETING
    # ==========================================

    path(
        "create/",
        views.create_meeting,
        name="create_meeting"
    ),

    # ==========================================
    # JOIN MEETING
    # ==========================================

    path(
        "join/",
        views.join_meeting,
        name="join_meeting"
    ),

    # ==========================================
    # MEETING ROOM
    # ==========================================

    path(
        "room/<uuid:room_code>/",
        views.meeting_room,
        name="meeting_room"
    ),

    # ==========================================
    # LIVEKIT TOKEN GENERATION
    # ==========================================


    # ==========================================
    # RECORDING UPLOAD
    # ==========================================

    path(
        "room/<uuid:room_code>/recording/upload/",
        views.upload_recording,
        name="upload_recording"
    ),

    # ==========================================
    # RECORDING DETAILS
    # ==========================================

    path(
        "recordings/<int:recording_id>/",
        views.recording_detail,
        name="recording_detail"
    ),

    # ==========================================
    # PLAY RECORDING
    # ==========================================

    path(
        "recordings/<int:recording_id>/play/",
        views.play_recording,
        name="play_recording"
    ),

    # ==========================================
    # WEBSOCKET TEST
    # ==========================================

    path(
        "websocket-test/",
        views.websocket_test,
        name="websocket_test"
    ),

]
