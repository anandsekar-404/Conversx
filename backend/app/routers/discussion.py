"""
ConversX Live Group Discussion Router.
Phase 7 & Security Hardening Pass.

Coordinates real-time peer discussion rooms (3 to 8 participants),
WebRTC signaling relay, topic retrieval, contribution analysis, and privacy filtering.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

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

    class LeaveRoomRequest(BaseModel):
        participant_id_or_username: str = Field(..., description="Participant ID or username to remove")

    class AnalyzeContributionRequest(BaseModel):
        user_transcript: str = Field(..., min_length=1, description="Transcribed spoken contribution")
        speaking_time_seconds: float = Field(..., ge=0.0, description="Total speaking time in seconds")
        total_discussion_duration_seconds: float = Field(..., gt=0.0, description="Full session duration in seconds")
        participant_count: int = Field(..., ge=1, le=8, description="Number of participants in room")
        speaking_turns: int = Field(1, ge=0, description="Number of times user took the floor")
        topic_id: Optional[str] = Field(None, description="Discussion topic identifier")


    @router.get("/topics")
    async def list_topics() -> Dict[str, Any]:
        """List all available curated discussion topics."""
        return {
            "status": "success",
            "topics": get_all_topics()
        }

    @router.get("/topics/{topic_id}")
    async def get_topic(topic_id: str) -> Dict[str, Any]:
        """Get details for a specific discussion topic."""
        topic = get_topic_by_id(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        return {"status": "success", "topic": topic}

    @router.post("/rooms")
    async def create_room_endpoint(
        req: CreateRoomRequest,
        current_user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """
        Create a new discussion room in waiting state.
        If authenticated, requires completed ConversX onboarding and enforces @handle identity.
        """
        host_username = req.username or "Host"
        host_user_id = req.user_id

        if current_user:
            if not current_user.onboarding_completed or not current_user.conversx_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="ConversX User ID onboarding required. Please complete onboarding first.",
                    headers={"X-Onboarding-Required": "true"}
                )
            host_username = f"@{current_user.conversx_user_id}"
            host_user_id = current_user.user_id

        room = create_discussion_room(
            topic_id=req.topic_id,
            created_by_username=host_username,
            created_by_user_id=host_user_id,
            custom_title=req.custom_title
        )
        return {"status": "success", "room": sanitize_room_for_client(room)}

    @router.get("/rooms/{room_id}")
    async def get_room_endpoint(room_id: str) -> Dict[str, Any]:
        """Get live status and participant list for a room. Strips private user IDs."""
        try:
            room = get_discussion_room(room_id)
            return {"status": "success", "room": sanitize_room_for_client(room)}
        except RoomNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/rooms/{room_id}/join")
    async def join_room_endpoint(
        room_id: str,
        req: JoinRoomRequest,
        current_user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """
        Join a discussion room.
        Enforces 3-8 participants bounds. Rejects 9th participant with 409 Conflict.
        If authenticated, requires completed onboarding and forces @handle identity (anti-impersonation).
        """
        join_username = req.username or "Participant"
        join_user_id = req.user_id

        if current_user:
            if not current_user.onboarding_completed or not current_user.conversx_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="ConversX User ID onboarding required. Please complete onboarding first.",
                    headers={"X-Onboarding-Required": "true"}
                )
            join_username = f"@{current_user.conversx_user_id}"
            join_user_id = current_user.user_id

        try:
            room, participant = join_discussion_room(
                room_id=room_id,
                username=join_username,
                user_id=join_user_id
            )
            return {
                "status": "success",
                "room": sanitize_room_for_client(room),
                "participant": sanitize_participant_for_client(participant)
            }
        except RoomNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RoomFullError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except InvalidRoomStateError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/rooms/{room_id}/leave")
    async def leave_room_endpoint(room_id: str, req: LeaveRoomRequest) -> Dict[str, Any]:
        """Leave a discussion room."""
        try:
            room = leave_discussion_room(
                room_id=room_id,
                participant_id_or_username=req.participant_id_or_username
            )
            return {"status": "success", "room": sanitize_room_for_client(room)}
        except RoomNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/rooms/{room_id}/start")
    async def start_room_endpoint(room_id: str) -> Dict[str, Any]:
        """
        Start live discussion.
        Enforces minimum 3 participants; rejects with 400 if fewer than 3.
        """
        try:
            room = start_discussion_room(room_id)
            return {"status": "success", "room": sanitize_room_for_client(room)}
        except RoomNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except InsufficientParticipantsError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/rooms/{room_id}/complete")
    async def complete_room_endpoint(room_id: str) -> Dict[str, Any]:
        """Conclude the discussion session."""
        try:
            room = complete_discussion_room(room_id)
            return {"status": "success", "room": sanitize_room_for_client(room)}
        except RoomNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/analyze")
    async def analyze_contribution_endpoint(
        req: AnalyzeContributionRequest,
        current_user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """
        Evaluate individual participant contribution across the 8 ConversX dimensions
        and discussion-specific collaboration metrics.
        """
        if current_user and not current_user.onboarding_completed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ConversX User ID onboarding required. Please complete onboarding first.",
                headers={"X-Onboarding-Required": "true"}
            )

        analysis = analyze_group_discussion_contribution(
            user_transcript=req.user_transcript,
            speaking_time_seconds=req.speaking_time_seconds,
            total_discussion_duration_seconds=req.total_discussion_duration_seconds,
            participant_count=req.participant_count,
            speaking_turns=req.speaking_turns,
            topic_id=req.topic_id
        )
        return analysis


# ---------------------------------------------------------------------------
# WebSocket Signaling Coordinator (WebRTC Mesh Support)
# ---------------------------------------------------------------------------
class DiscussionSignalingHub:
    """Coordinates WebRTC peer connections and real-time room events."""

    def __init__(self) -> None:
        self.rooms: Dict[str, Dict[str, Any]] = {}

    async def connect(self, room_id: str, participant_id: str, websocket: Any) -> None:
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

if router is not None and WebSocket is not None:
    @router.websocket("/ws/{room_id}/{participant_id}")
    async def websocket_signaling_endpoint(websocket: WebSocket, room_id: str, participant_id: str) -> None:
        await signaling_hub.connect(room_id, participant_id, websocket)
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
    signaling_hub = None
