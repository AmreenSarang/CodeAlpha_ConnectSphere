
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from livekit import api

from .models import Meeting

logger = logging.getLogger(__name__)


@login_required
@require_GET
def livekit_token(request, room_code):
    try:
        # Find meeting
        meeting = get_object_or_404(
            Meeting,
            room_code=room_code
        )

        # Check permissions
        is_host = meeting.host_id == request.user.id

        is_participant = meeting.participants.filter(
            id=request.user.id
        ).exists()

        if not is_host and not is_participant:
            return JsonResponse({
                "success": False,
                "error": "You are not authorized to join this meeting."
            }, status=403)

        # Read credentials
        livekit_url = settings.LIVEKIT_URL.strip()
        api_key = settings.LIVEKIT_API_KEY.strip()
        api_secret = settings.LIVEKIT_API_SECRET.strip()

        if not all([livekit_url, api_key, api_secret]):
            return JsonResponse({
                "success": False,
                "error": "LiveKit credentials are missing."
            }, status=500)

        if not livekit_url.startswith("wss://"):
            return JsonResponse({
                "success": False,
                "error": "Invalid LiveKit server URL."
            }, status=500)

        # Create room name
        room_name = str(meeting.room_code)

        # Generate token
        token = api.AccessToken(
            api_key,
            api_secret
        )

        token.with_identity(str(request.user.id))
        token.with_name(request.user.username)

        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
        )

        jwt_token = token.to_jwt()

        # Safe diagnostic logging
        logger.info("LiveKit URL: %s", livekit_url)
        logger.info("LiveKit key ending: %s", api_key[-4:])

        return JsonResponse({
            "success": True,
            "url": livekit_url,
            "token": jwt_token,
            "room": room_name,
            "username": request.user.username
        })

    except Exception:
        logger.exception("LiveKit token generation failed")

        return JsonResponse({
            "success": False,
            "error": "Unable to generate LiveKit token."
        }, status=500)
