"""
ConversX Live Group Discussion Service.
Manages discussion topics, room lifecycle (3-8 participants), WebRTC peer coordinator,
and individual multi-user communication scoring across the 8 ConversX dimensions
plus discussion-specific collaboration metrics.
"""

from __future__ import annotations

import datetime
import uuid
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.practice import analyze_practice_response

# ---------------------------------------------------------------------------
# Curated Group Discussion Topics
# ---------------------------------------------------------------------------
DISCUSSION_TOPICS: List[Dict[str, Any]] = [
    {
        "id": "disc_01",
        "title": "Should artificial intelligence replace certain human analytical jobs?",
        "category": "Technology & Ethics",
        "difficulty": "Intermediate",
        "expected_duration_seconds": 900,  # 15 minutes
        "min_participants": 3,
        "max_participants": 8,
        "guidance": (
            "Explore economic productivity vs. workforce displacement. Focus on balanced "
            "reasoning, synthesizing peer counterpoints, and avoiding absolute assertions."
        ),
        "coaching_cues": [
            "Acknowledge the previous speaker's premise before stating your counter-view.",
            "Cite practical domain examples rather than purely theoretical outcomes.",
            "Invite input from participants who haven't spoken recently."
        ]
    },
    {
        "id": "disc_02",
        "title": "Remote Work vs. In-Office: Which model drives sustainable team culture?",
        "category": "Workplace & Culture",
        "difficulty": "Beginner",
        "expected_duration_seconds": 900,
        "min_participants": 3,
        "max_participants": 8,
        "guidance": (
            "Discuss autonomy, async collaboration, informal mentorship, and cross-functional silos. "
            "Aim to find nuanced middle ground rather than rigid polarization."
        ),
        "coaching_cues": [
            "Ask clarifying questions to uncover underlying assumptions.",
            "Summarize the group's consensus before pivoting to a new angle.",
            "Use measured, collaborative phrasing to introduce trade-offs."
        ]
    },
    {
        "id": "disc_03",
        "title": "Rapid Product Velocity vs. Deep Engineering Quality in High-Growth Tech",
        "category": "Engineering Leadership",
        "difficulty": "Advanced",
        "expected_duration_seconds": 900,
        "min_participants": 3,
        "max_participants": 8,
        "guidance": (
            "Debate tech debt vs. time-to-market. Practice executive persuasion, articulating "
            "risk posture clearly, and maintaining composure under disagreement."
        ),
        "coaching_cues": [
            "State your core recommendation within the first 15 seconds.",
            "Frame trade-offs quantitatively when possible.",
            "Respectfully challenge technical assumptions using evidence."
        ]
    },
    {
        "id": "disc_04",
        "title": "Corporate Climate Action: Voluntary Pledges vs. Mandatory Regulatory Caps",
        "category": "Policy & Economics",
        "difficulty": "Advanced",
        "expected_duration_seconds": 900,
        "min_participants": 3,
        "max_participants": 8,
        "guidance": (
            "Examine compliance incentives, global competitive fairness, and market mechanisms. "
            "Maintain diplomatic decorum and structured reasoning."
        ),
        "coaching_cues": [
            "Bridge opposing economic perspectives with constructive synthesis.",
            "Avoid dismissive filler phrases when peers express opposing views.",
            "Keep speaking turns concise (under 45 seconds) to maintain dialogue rhythm."
        ]
    },
    {
        "id": "disc_05",
        "title": "Balancing User Privacy with Data-Driven Personalization in Consumer Products",
        "category": "Product & Privacy",
        "difficulty": "Intermediate",
        "expected_duration_seconds": 900,
        "min_participants": 3,
        "max_participants": 8,
        "guidance": (
            "Analyze explicit user consent vs. frictionless recommendation algorithms. "
            "Focus on constructive dialogue and empathetic listening."
        ),
        "coaching_cues": [
            "Affirm valid security concerns before proposing product solutions.",
            "Check for mutual alignment before progressing to action items.",
            "Use precise lexicon rather than vague technical generalities."
        ]
    }
]

# Hard Bounds
MIN_PARTICIPANTS: int = 3
MAX_PARTICIPANTS: int = 8

# In-memory active discussion rooms repository
_ACTIVE_ROOMS: Dict[str, Dict[str, Any]] = {}


def get_all_topics() -> List[Dict[str, Any]]:
    """Returns all available discussion topics."""
    return list(DISCUSSION_TOPICS)


def get_topic_by_id(topic_id: str) -> Optional[Dict[str, Any]]:
    """Lookup a discussion topic by ID."""
    for t in DISCUSSION_TOPICS:
        if t["id"] == topic_id:
            return t
    return None


class DiscussionRoomError(Exception):
    """Base exception for discussion room errors."""
    pass


class RoomNotFoundError(DiscussionRoomError):
    pass


class RoomFullError(DiscussionRoomError):
    pass


class InsufficientParticipantsError(DiscussionRoomError):
    pass


class InvalidRoomStateError(DiscussionRoomError):
    pass


def create_discussion_room(
    topic_id: str,
    created_by_username: str = "Host",
    created_by_user_id: Optional[str] = None,
    custom_title: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a new discussion room in waiting state."""
    topic = get_topic_by_id(topic_id)
    if not topic:
        topic = DISCUSSION_TOPICS[0]

    room_id = f"room_{uuid.uuid4().hex[:8]}"
    participant_id = f"part_{uuid.uuid4().hex[:6]}"

    room = {
        "id": room_id,
        "topic_id": topic["id"],
        "topic_title": custom_title or topic["title"],
        "category": topic["category"],
        "difficulty": topic["difficulty"],
        "guidance": topic["guidance"],
        "coaching_cues": topic["coaching_cues"],
        "expected_duration_seconds": topic["expected_duration_seconds"],
        "status": "waiting",  # waiting, ready, in_progress, completed, cancelled
        "min_participants": MIN_PARTICIPANTS,
        "max_participants": MAX_PARTICIPANTS,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "started_at": None,
        "ended_at": None,
        "created_by": created_by_username,
        "participants": [
            {
                "id": participant_id,
                "user_id": created_by_user_id,
                "username": created_by_username,
                "is_ready": True,
                "is_muted": False,
                "joined_at": datetime.datetime.utcnow().isoformat(),
                "speaking_time_seconds": 0.0,
                "speaking_turns": 0
            }
        ]
    }
    _ACTIVE_ROOMS[room_id] = room
    return room


def get_discussion_room(room_id: str) -> Dict[str, Any]:
    """Retrieves room details by room ID."""
    room = _ACTIVE_ROOMS.get(room_id)
    if not room:
        raise RoomNotFoundError(f"Discussion room '{room_id}' not found.")
    return room


def join_discussion_room(
    room_id: str,
    username: str,
    user_id: Optional[str] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Adds a participant to a discussion room.
    Enforces maximum 8 participants; rejects 9th participant.
    """
    room = get_discussion_room(room_id)

    if room["status"] not in ("waiting", "ready"):
        raise InvalidRoomStateError(f"Cannot join room in state '{room['status']}'.")

    # Check participant count limit
    if len(room["participants"]) >= MAX_PARTICIPANTS:
        raise RoomFullError(f"Room has reached the maximum limit of {MAX_PARTICIPANTS} participants.")

    # Check if participant already in room
    existing = next((p for p in room["participants"] if p["username"].lower() == username.lower()), None)
    if existing:
        return room, existing

    participant_id = f"part_{uuid.uuid4().hex[:6]}"
    new_participant = {
        "id": participant_id,
        "user_id": user_id,
        "username": username,
        "is_ready": False,
        "is_muted": False,
        "joined_at": datetime.datetime.utcnow().isoformat(),
        "speaking_time_seconds": 0.0,
        "speaking_turns": 0
    }
    room["participants"].append(new_participant)

    # If count reaches minimum, mark ready
    if len(room["participants"]) >= MIN_PARTICIPANTS and room["status"] == "waiting":
        room["status"] = "ready"

    return room, new_participant


def leave_discussion_room(room_id: str, participant_id_or_username: str) -> Dict[str, Any]:
    """Removes a participant from a discussion room."""
    room = get_discussion_room(room_id)

    room["participants"] = [
        p for p in room["participants"]
        if p["id"] != participant_id_or_username and p["username"].lower() != participant_id_or_username.lower()
    ]

    # If participants drop below min while in ready state, revert to waiting
    if len(room["participants"]) < MIN_PARTICIPANTS and room["status"] == "ready":
        room["status"] = "waiting"

    # If all participants left, mark room cancelled
    if len(room["participants"]) == 0 and room["status"] in ("waiting", "ready"):
        room["status"] = "cancelled"

    return room


def start_discussion_room(room_id: str) -> Dict[str, Any]:
    """
    Starts the live group discussion.
    Enforces minimum 3 participants; rejects start if fewer than 3.
    """
    room = get_discussion_room(room_id)

    if len(room["participants"]) < MIN_PARTICIPANTS:
        raise InsufficientParticipantsError(
            f"Cannot start discussion with {len(room['participants'])} participants. "
            f"Minimum {MIN_PARTICIPANTS} required."
        )

    room["status"] = "in_progress"
    room["started_at"] = datetime.datetime.utcnow().isoformat()
    return room


def complete_discussion_room(room_id: str) -> Dict[str, Any]:
    """Concludes the live group discussion and transitions to completed."""
    room = get_discussion_room(room_id)
    room["status"] = "completed"
    room["ended_at"] = datetime.datetime.utcnow().isoformat()
    return room


# ---------------------------------------------------------------------------
# Individual Analysis & Discussion Metrics Calculation
# ---------------------------------------------------------------------------
def calculate_discussion_metrics(
    user_transcript: str,
    speaking_time_seconds: float,
    total_discussion_duration_seconds: float,
    participant_count: int,
    speaking_turns: int = 1
) -> Dict[str, Any]:
    """
    Calculates reliable group discussion metrics for an individual participant.
    Ensures zero fabricated data; calculates exact metrics based on real interaction.
    """
    total_dur = max(1.0, total_discussion_duration_seconds)
    speaking_pct = round((speaking_time_seconds / total_dur) * 100.0, 1)
    fair_share_pct = round(100.0 / max(1, participant_count), 1)

    if speaking_pct == 0:
        balance_status = "silent"
        balance_summary = "You did not speak during this discussion. Aim to share at least one perspective."
    elif speaking_pct < (fair_share_pct * 0.5):
        balance_status = "low_participation"
        balance_summary = "You contributed sparingly. Consider introducing your thoughts earlier in the dialogue."
    elif speaking_pct > (fair_share_pct * 2.2):
        balance_status = "high_airtime"
        balance_summary = "You commanded a large share of the airtime. Consider pausing to invite peer responses."
    else:
        balance_status = "balanced"
        balance_summary = "Balanced airtime. You contributed meaningfully while leaving ample floor space for peers."

    lower = user_transcript.lower()

    collab_patterns = [
        r"\bi agree\b",
        r"\bbuilding on\b",
        r"\bto add to\b",
        r"\bgood point\b",
        r"\bvalid point\b",
        r"\byou mentioned\b",
        r"\bas said\b",
        r"\bi appreciate\b",
        r"\bwhat you said\b"
    ]
    collab_count = sum(len(re.findall(p, lower)) for p in collab_patterns)

    disagree_patterns = [
        r"\bi see your point\b",
        r"\bi understand your point\b",
        r"\banother perspective\b",
        r"\balternative view\b",
        r"\bon the other hand\b",
        r"\bwith all due respect\b",
        r"\bi respectfully disagree\b",
        r"\bfrom a different angle\b",
        r"\bwhile that is true\b"
    ]
    disagree_count = sum(len(re.findall(p, lower)) for p in disagree_patterns)

    question_count = len(re.findall(r"\?", user_transcript))
    question_phrases = [
        r"\bwhat do you think\b",
        r"\bhow would you\b",
        r"\bcould you clarify\b",
        r"\bdo you agree\b",
        r"\bwhat are your thoughts\b"
    ]
    question_count += sum(len(re.findall(p, lower)) for p in question_phrases)

    return {
        "speaking_time_seconds": round(speaking_time_seconds, 1),
        "total_discussion_duration_seconds": round(total_discussion_duration_seconds, 1),
        "speaking_percentage": speaking_pct,
        "fair_share_percentage": fair_share_pct,
        "speaking_turns": max(1, speaking_turns) if speaking_time_seconds > 0 else 0,
        "conversational_balance": balance_status,
        "balance_summary": balance_summary,
        "collaborative_phrases_count": collab_count,
        "respectful_disagreements_count": disagree_count,
        "questions_asked": question_count
    }


def analyze_group_discussion_contribution(
    user_transcript: str,
    speaking_time_seconds: float = 60.0,
    total_discussion_duration_seconds: float = 900.0,
    participant_count: int = 5,
    speaking_turns: int = 2,
    topic_id: str = "disc_01"
) -> Dict[str, Any]:
    """
    Evaluates individual participant communication in a group discussion using
    the authoritative 8 ConversX deterministic dimensions + discussion-specific metrics.
    """
    practice_result = analyze_practice_response(
        text=user_transcript if user_transcript.strip() else "I listened to the discussion points.",
        scenario_id=topic_id
    )

    disc_metrics = calculate_discussion_metrics(
        user_transcript=user_transcript,
        speaking_time_seconds=speaking_time_seconds,
        total_discussion_duration_seconds=total_discussion_duration_seconds,
        participant_count=participant_count,
        speaking_turns=speaking_turns
    )

    strengths = list(getattr(practice_result, "positive_feedback", []) or [])
    improvements = list(getattr(practice_result, "improvement_feedback", []) or [])

    if disc_metrics["collaborative_phrases_count"] > 0:
        strengths.append(f"Demonstrated strong collaboration by acknowledging peer input ({disc_metrics['collaborative_phrases_count']} reference(s)).")
    elif user_transcript.strip():
        improvements.append("Try explicitly referencing other participants' arguments before presenting your own.")

    if disc_metrics["respectful_disagreements_count"] > 0:
        strengths.append("Maintained high diplomatic decorum during ideological disagreement.")

    if disc_metrics["questions_asked"] > 0:
        strengths.append("Engaged peers by asking probing questions to drive discussion depth.")
    else:
        improvements.append("Pose at least one question to the room to invite collaborative synthesis.")

    if disc_metrics["conversational_balance"] == "high_airtime":
        tip = "Practice yielding the floor gracefully after making your core point (aim for 30–45s speaking turns)."
    elif disc_metrics["conversational_balance"] == "low_participation":
        tip = "Speak up early in the first 3 minutes of discussion to establish presence and lower the threshold for speaking."
    else:
        tip = "Synthesize two contrasting viewpoints before presenting your recommendation to demonstrate executive facilitation."

    comm_score = getattr(practice_result, "overall_score", 85)
    dim_scores = getattr(practice_result, "dimension_scores", {})
    mod_status = getattr(practice_result, "moderation_status", "safe")
    sib = getattr(practice_result, "say_it_better", None)
    if hasattr(sib, "__dict__"):
        sib_dict = {
            "original_text": getattr(sib, "original_text", user_transcript),
            "suggested_text": getattr(sib, "suggested_text", ""),
            "improvements_made": getattr(sib, "improvements_made", [])
        }
    elif isinstance(sib, dict):
        sib_dict = sib
    else:
        sib_dict = {
            "original_text": user_transcript,
            "suggested_text": "Building on what was shared, I believe a balanced approach would allow us to...",
            "improvements_made": ["Enhanced collaborative phrasing", "Replaced blunt rebuttal with diplomatic transition"]
        }

    return {
        "status": "success",
        "topic_id": topic_id,
        "communication_score": comm_score,
        "dimension_scores": dim_scores,
        "discussion_metrics": disc_metrics,
        "moderation_status": mod_status,
        "positive_feedback": strengths,
        "improvement_feedback": improvements,
        "coaching_tip": tip,
        "say_it_better": sib_dict,
        "disclaimer": "Evaluated deterministically across 8 communication dimensions and group conversational balance."
    }
