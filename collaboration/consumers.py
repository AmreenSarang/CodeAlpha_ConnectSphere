
import asyncio
import json
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from django.utils import timezone

from meetings.models import Meeting


@database_sync_to_async
def get_meeting_access(room_code, user):
    """
    Verify that the user is the host or an authorized participant.
    Allow early entry, but reject ended or inactive meetings.
    """

    meeting = (
        Meeting.objects.filter(room_code=room_code)
        .filter(
            Q(host=user) | Q(participants=user)
        )
        .first()
    )

    if meeting is None:
        return False

    if not meeting.is_active:
        return False

    if (
        meeting.scheduled_end
        and timezone.now() >= meeting.scheduled_end
    ):
        return False

    # scheduled_start is deliberately not checked.
    # Authorized participants can enter early.

    return True


@database_sync_to_async
def meeting_can_continue(room_code):
    """Check whether the meeting is still active."""

    meeting = Meeting.objects.filter(
        room_code=room_code
    ).first()

    if meeting is None:
        return False

    if not meeting.is_active:
        return False

    if (
        meeting.scheduled_end
        and timezone.now() >= meeting.scheduled_end
    ):
        return False

    return True


class MeetingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        """Connect an authorized user to the meeting chat."""

        user = self.scope["user"]

        # Authentication check
        if not user.is_authenticated:
            await self.close(code=4401)
            return

        raw_room_code = self.scope["url_route"]["kwargs"].get(
            "room_code"
        )

        # Validate room code
        try:
            self.room_code = uuid.UUID(raw_room_code)

        except (ValueError, TypeError, AttributeError):
            await self.close(code=4404)
            return

        # Verify meeting membership
        allowed = await get_meeting_access(
            self.room_code,
            user,
        )

        if not allowed:
            await self.close(code=4403)
            return

        self.username = user.get_username()
        self.peer_id = str(uuid.uuid4())

        self.room_group_name = (
            f"meeting_{self.room_code}"
        )

        self.end_monitor_task = None

        # Join meeting chat group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        # Notify connected client
        await self.send(
            text_data=json.dumps({
                "type": "connected",
                "peer_id": self.peer_id,
                "username": self.username,
                "message": "Connected to ConnectSphere chat.",
            })
        )

        # Notify other chat clients
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "participant_joined",
                "peer_id": self.peer_id,
                "username": self.username,
                "sender_channel": self.channel_name,
            },
        )

        # Monitor scheduled meeting end
        self.end_monitor_task = asyncio.create_task(
            self.monitor_meeting_end()
        )

    async def monitor_meeting_end(self):
        """Disconnect chat when the meeting ends."""

        try:
            while True:

                await asyncio.sleep(3)

                allowed = await meeting_can_continue(
                    self.room_code
                )

                if not allowed:

                    try:
                        await self.send(
                            text_data=json.dumps({
                                "type": "meeting-ended",
                                "message": "The meeting has ended.",
                            })
                        )

                    except Exception:
                        pass

                    await self.close(code=4408)
                    return

        except asyncio.CancelledError:
            pass

    async def disconnect(self, close_code):
        """Remove disconnected users from the chat group."""

        task = getattr(
            self,
            "end_monitor_task",
            None,
        )

        if task and task is not asyncio.current_task():
            task.cancel()

        if hasattr(self, "room_group_name"):

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "participant_left",
                    "peer_id": getattr(
                        self,
                        "peer_id",
                        "",
                    ),
                    "username": getattr(
                        self,
                        "username",
                        "",
                    ),
                    "sender_channel": self.channel_name,
                },
            )

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(self, text_data=None, bytes_data=None):
        """Receive and relay meeting chat messages."""

        if not text_data:
            return

        # Check meeting status before processing messages
        allowed = await meeting_can_continue(
            self.room_code
        )

        if not allowed:
            await self.close(code=4408)
            return

        try:
            data = json.loads(text_data)

        except (json.JSONDecodeError, TypeError):
            return

        message_type = data.get("type")

        # LiveKit handles audio/video signaling.
        # Django Channels handles meeting chat only.
        if message_type != "chat":
            return

        payload = data.get("payload")

        if not isinstance(payload, str):
            return

        payload = payload.strip()

        if not payload:
            return

        if len(payload) > 1000:
            return

        # Send chat to everyone in the meeting except sender
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "relay_chat",
                "username": self.username,
                "peer_id": self.peer_id,
                "payload": payload,
                "sender_channel": self.channel_name,
            },
        )

    async def relay_chat(self, event):
        """Deliver a chat message to another participant."""

        if event["sender_channel"] == self.channel_name:
            return

        await self.send(
            text_data=json.dumps({
                "type": "chat",
                "username": event["username"],
                "peer_id": event["peer_id"],
                "payload": event["payload"],
            })
        )

    async def participant_joined(self, event):
        """Notify chat clients that someone joined."""

        if event["sender_channel"] == self.channel_name:
            return

        await self.send(
            text_data=json.dumps({
                "type": "participant-joined",
                "peer_id": event["peer_id"],
                "username": event["username"],
            })
        )

    async def participant_left(self, event):
        """Notify chat clients that someone left."""

        if event["sender_channel"] == self.channel_name:
            return

        await self.send(
            text_data=json.dumps({
                "type": "participant-left",
                "peer_id": event["peer_id"],
                "username": event["username"],
            })
        )
