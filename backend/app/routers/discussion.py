"""
ConversX Live Group Discussion Router.
Phase 7 & Security Hardening Pass.

Coordinates real-time peer discussion rooms (3 to 8 participants),
WebRTC signaling relay, topic retrieval, contribution analysis, and privacy filtering.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# WebSocket Signaling Coordinator (WebRTC Mesh Support)
# ---------------------------------------------------------------------------
class DiscussionSignalingHub:
    """Coordinates WebRTC peer connections and real-time room events."""

    def __init__(self) -> None:
        self.rooms: Dict[str, Dict[str, Any]] = {}

    async def connect(self, room_id: str, participant_id: str, websocket: Any) -> bool:
        # Enforce maximum 8 participants on direct WebSocket connection
        if room_id in self.rooms and len(self.rooms[room_id]) >= 8 and participant_id not in self.rooms[room_id]:
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Room has reached the maximum limit of 8 participants."
            }))
            await websocket.close(code=4008)
            return False

        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][participant_id] = websocket

        # Notify peers
        await self.broadcast(room_id, {
            "type": "peer_connected",
            "participant_id": participant_id,
            "connected_peers": list(self.rooms[room_id].keys())
        }, exclude=participant_id)
        return True

    def disconnect(self, room_id: str, participant_id: str) -> None:
        if room_id in self.rooms and participant_id in self.rooms[room_id]:
            del self.rooms[room_id][participant_id]
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    async def broadcast(self, room_id: str, message: Dict[str, Any], exclude: Optional[str] = None) -> None:
        if room_id not in self.rooms:
            return
        msg_str = json.dumps(message)
        for pid, ws in list(self.rooms[room_id].items()):
            if pid != exclude:
                try:
                    await ws.send_text(msg_str)
                except Exception:
                    pass

    async def send_to_peer(self, room_id: str, target_id: str, message: Dict[str, Any]) -> None:
        if room_id in self.rooms and target_id in self.rooms[room_id]:
            try:
                await self.rooms[room_id][target_id].send_text(json.dumps(message))
            except Exception:
                pass


signaling_hub = DiscussionSignalingHub()


try:
    from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
    from pydantic import BaseModel, Field

    from app.core.auth import UserSession, get_optional_current_user
    from app.services.discussion import (
        analyze_group_discussion_contribution,
        complete_discussion_room,
        create_discussion_room,
        get_all_topics,
        get_discussion_room,
        get_topic_by_id,
        join_discussion_room,
        leave_discussion_room,
        sanitize_participant_for_client,
        sanitize_room_for_client,
        start_discussion_room,
        InsufficientParticipantsError,
        InvalidRoomStateError,
        RoomFullError,
        RoomNotFoundError,
    )

    router = APIRouter(prefix="/api/v1/discussion", tags=["discussion"])

    # -----------------------------------------------------------------------
    # Request & Response Schemas
    # -----------------------------------------------------------------------
    class CreateRoomRequest(BaseModel):
        topic_id: str = Field(..., description="Topic identifier (e.g. 'disc_01')")
        username: Optional[str] = Field("Host", description="Host display username (overridden by auth session if present)")
        user_id: Optional[str] = Field(None, description="Host user ID")
        custom_title: Optional[str] = Field(None, description="Optional custom room title")

    class JoinRoomRequest(BaseModel):
        username: Optional[str] = Field("Participant", description="Joining participant username (overridden by auth session if present)")
        user_id: Optional[str] = Field(None, description="Optional user ID")

    class RoomStatusActionRequest(BaseModel):
        user_id: Optional[str] = Field(None, description="Requesting user ID")

    class AnalyzeContributionRequest(BaseModel):
        user_transcript: str = Field(..., description="Spoken transcript of the participant")
        speaking_time_seconds: float = Field(..., description="Individual speaking duration in seconds")
        total_discussion_duration_seconds: float = Field(..., description="Total elapsed discussion duration")
        participant_count: int = Field(..., description="Number of participants in room")
        speaking_turns: int = Field(1, description="Number of distinct speaking turns")
        topic_id: Optional[str] = Field(None, description="Topic ID discussed")

    # -----------------------------------------------------------------------
    # API Routes
    # -----------------------------------------------------------------------
    @router.get("/topics")
    def list_discussion_topics() -> Dict[str, Any]:
        """Returns the full catalog of discussion topics across all categories."""
        return {"topics": get_all_topics()}

    @router.get("/topics/{topic_id}")
    def get_topic(topic_id: str) -> Dict[str, Any]:
        """Retrieves a single topic by ID."""
        topic = get_topic_by_id(topic_id)
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic '{topic_id}' not found."
            )
        return topic

    @router.post("/rooms")
    def create_room(
        req: CreateRoomRequest,
        current_user: Optional[UserSession] = Depends(get_optional_current_user)
    ) -> Dict[str, Any]:
        """Creates a new discussion room with 3 to 8 participant limit."""
        host_user_id = current_user.user_id if current_user else req.user_id
        host_name = (
            current_user.public_handle
            or current_user.display_name
            or req.username
            or "Host"
        ) if current_user else req.username or "Host"

        room = create_discussion_room(
            topic_id=req.topic_id,
            created_by_username=host_name,
            created_by_user_id=host_user_id,
            custom_title=req.custom_title
        )
        return sanitize_room_for_client(room)

    @router.get("/rooms/{room_id}")
    def get_room(room_id: str) -> Dict[str, Any]:
        """Retrieves room status and participant list."""
        try:
            room = get_discussion_room(room_id)
            return sanitize_room_for_client(room)
        except RoomNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discussion room '{room_id}' not found."
            )

    @router.post("/rooms/{room_id}/join")
    def join_room(
        room_id: str,
        req: JoinRoomRequest,
        current_user: Optional[UserSession] = Depends(get_optional_current_user)
    ) -> Dict[str, Any]:
        """Joins an existing discussion room (enforces 3-8 participant boundary)."""
        joiner_user_id = current_user.user_id if current_user else req.user_id
        joiner_name = (
            current_user.public_handle
            or current_user.display_name
            or req.username
            or "Participant"
        ) if current_user else req.username or "Participant"

        try:
            room, participant = join_discussion_room(
                room_id=room_id,
                username=joiner_name,
                user_id=joiner_user_id
            )
            return {
                "room": sanitize_room_for_client(room),
                "participant": sanitize_participant_for_client(participant)
            }
        except RoomNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Room '{room_id}' not found.")
        except RoomFullError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except InvalidRoomStateError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/rooms/{room_id}/leave/{participant_id}")
    def leave_room(room_id: str, participant_id: str) -> Dict[str, Any]:
        """Leaves a discussion room."""
        try:
            room = leave_discussion_room(room_id, participant_id)
            return sanitize_room_for_client(room)
        except RoomNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Room '{room_id}' not found.")

    @router.post("/rooms/{room_id}/start")
    def start_room(room_id: str, req: RoomStatusActionRequest) -> Dict[str, Any]:
        """Starts discussion (requires minimum 3 participants)."""
        try:
            room = start_discussion_room(room_id, req.user_id)
            return sanitize_room_for_client(room)
        except RoomNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Room '{room_id}' not found.")
        except InsufficientParticipantsError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except InvalidRoomStateError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/rooms/{room_id}/complete")
    def complete_room(room_id: str, req: RoomStatusActionRequest) -> Dict[str, Any]:
        """Concludes discussion and triggers comprehensive group metrics."""
        try:
            room = complete_discussion_room(room_id, req.user_id)
            return sanitize_room_for_client(room)
        except RoomNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Room '{room_id}' not found.")
        except InvalidRoomStateError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/analyze-contribution")
    def analyze_contribution(req: AnalyzeContributionRequest) -> Dict[str, Any]:
        """Analyzes an individual participant contribution in group discussion context."""
        analysis = analyze_group_discussion_contribution(
            user_transcript=req.user_transcript,
            speaking_time_seconds=req.speaking_time_seconds,
            total_discussion_duration_seconds=req.total_discussion_duration_seconds,
            participant_count=req.participant_count,
            speaking_turns=req.speaking_turns,
            topic_id=req.topic_id
        )
        return analysis

    @router.websocket("/ws/{room_id}/{participant_id}")
    async def websocket_signaling_endpoint(websocket: WebSocket, room_id: str, participant_id: str) -> None:
        connected = await signaling_hub.connect(room_id, participant_id, websocket)
        if not connected:
            return
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except Exception:
                    continue

                msg_type = msg.get("type")

                # WebRTC Signaling Messages: offer, answer, ice-candidate
                if msg_type in ("offer", "answer", "ice-candidate"):
                    target_id = msg.get("target_id")
                    if target_id:
                        msg["sender_id"] = participant_id
                        await signaling_hub.send_to_peer(room_id, target_id, msg)

                # Room events: speaking_indicator, mute_toggle, coaching_prompt
                elif msg_type in ("speaking", "mute", "ready", "coaching_prompt"):
                    msg["sender_id"] = participant_id
                    await signaling_hub.broadcast(room_id, msg, exclude=participant_id)

        except WebSocketDisconnect:
            signaling_hub.disconnect(room_id, participant_id)
            await signaling_hub.broadcast(room_id, {
                "type": "peer_disconnected",
                "participant_id": participant_id
            })

except ImportError:
    router = None
