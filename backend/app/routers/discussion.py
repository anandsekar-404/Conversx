"""
FastAPI Router for Live Group Discussion.
Provides REST management for rooms, topics, participant lifecycle,
and WebSocket-based WebRTC signaling coordinator.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
    from pydantic import BaseModel, Field
except ImportError:
    APIRouter = None
    HTTPException = None
    WebSocket = None
    WebSocketDisconnect = None
    BaseModel = None
    Field = None

from app.services.discussion import (
    MIN_PARTICIPANTS,
    MAX_PARTICIPANTS,
    get_all_topics,
    get_topic_by_id,
    create_discussion_room,
    get_discussion_room,
    join_discussion_room,
    leave_discussion_room,
    start_discussion_room,
    complete_discussion_room,
    analyze_group_discussion_contribution,
    RoomNotFoundError,
    RoomFullError,
    InsufficientParticipantsError,
    InvalidRoomStateError,
)

if APIRouter is not None:
    router = APIRouter(prefix="/api/v1/discussion", tags=["discussion"])
else:
    router = None


# ---------------------------------------------------------------------------
# Pydantic Request Models
# ---------------------------------------------------------------------------
if BaseModel is not None:
    class CreateRoomRequest(BaseModel):
        topic_id: str = "disc_01"
        username: str = "Host"
        user_id: Optional[str] = None
        custom_title: Optional[str] = None

    class JoinRoomRequest(BaseModel):
        username: str
        user_id: Optional[str] = None

    class LeaveRoomRequest(BaseModel):
        participant_id_or_username: str

    class AnalyzeContributionRequest(BaseModel):
        user_transcript: str
        speaking_time_seconds: float = 60.0
        total_discussion_duration_seconds: float = 900.0
        participant_count: int = 5
        speaking_turns: int = 2
        topic_id: str = "disc_01"


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------
if router is not None:
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
    async def create_room_endpoint(req: CreateRoomRequest) -> Dict[str, Any]:
        """Create a new discussion room in waiting state."""
        room = create_discussion_room(
            topic_id=req.topic_id,
            created_by_username=req.username,
            created_by_user_id=req.user_id,
            custom_title=req.custom_title
        )
        return {"status": "success", "room": room}

    @router.get("/rooms/{room_id}")
    async def get_room_endpoint(room_id: str) -> Dict[str, Any]:
        """Get live status and participant list for a room."""
        try:
            room = get_discussion_room(room_id)
            return {"status": "success", "room": room}
        except RoomNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/rooms/{room_id}/join")
    async def join_room_endpoint(room_id: str, req: JoinRoomRequest) -> Dict[str, Any]:
        """
        Join a discussion room.
        Enforces 3-8 participants bounds. Rejects 9th participant with 409 Conflict.
        """
        try:
            room, participant = join_discussion_room(
                room_id=room_id,
                username=req.username,
                user_id=req.user_id
            )
            return {
                "status": "success",
                "room": room,
                "participant": participant
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
            return {"status": "success", "room": room}
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
            return {"status": "success", "room": room}
        except RoomNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except InsufficientParticipantsError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/rooms/{room_id}/complete")
    async def complete_room_endpoint(room_id: str) -> Dict[str, Any]:
        """Conclude the discussion session."""
        try:
            room = complete_discussion_room(room_id)
            return {"status": "success", "room": room}
        except RoomNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/analyze")
    async def analyze_contribution_endpoint(req: AnalyzeContributionRequest) -> Dict[str, Any]:
        """
        Evaluate individual participant contribution across the 8 ConversX dimensions
        and discussion-specific collaboration metrics.
        """
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
        # room_id -> { participant_id: WebSocket }
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
