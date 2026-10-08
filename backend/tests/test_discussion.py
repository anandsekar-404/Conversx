"""
Comprehensive Test Suite for ConversX Live Group Discussion Service.
Tests room lifecycle, participant boundaries (3-8 participants),
rejection of 9th participant, speaking metrics calculation,
conversational balance, collaborative indicators, and deterministic scoring.
"""

import pytest
from app.services.discussion import (
    MIN_PARTICIPANTS,
    MAX_PARTICIPANTS,
    DISCUSSION_TOPICS,
    get_all_topics,
    get_topic_by_id,
    create_discussion_room,
    get_discussion_room,
    join_discussion_room,
    leave_discussion_room,
    start_discussion_room,
    complete_discussion_room,
    calculate_discussion_metrics,
    analyze_group_discussion_contribution,
    RoomNotFoundError,
    RoomFullError,
    InsufficientParticipantsError,
    InvalidRoomStateError,
)


# =============================================================================
# 1. Topic Catalog Tests
# =============================================================================
def test_discussion_topics_catalog():
    topics = get_all_topics()
    assert len(topics) >= 5
    for t in topics:
        assert t["min_participants"] == 3
        assert t["max_participants"] == 8
        assert t["expected_duration_seconds"] == 900
        assert "guidance" in t
        assert len(t["coaching_cues"]) >= 3


def test_get_topic_by_id():
    topic = get_topic_by_id("disc_01")
    assert topic is not None
    assert "artificial intelligence" in topic["title"].lower()

    non_existent = get_topic_by_id("invalid_id")
    assert non_existent is None


# =============================================================================
# 2. Participant Limits & Boundary Tests (Min 3, Max 8, 9th Rejected)
# =============================================================================
def test_room_hard_limits_constants():
    assert MIN_PARTICIPANTS == 3
    assert MAX_PARTICIPANTS == 8


def test_cannot_start_with_fewer_than_3_participants():
    room = create_discussion_room("disc_01", created_by_username="User1")
    # Only 1 participant
    with pytest.raises(InsufficientParticipantsError):
        start_discussion_room(room["id"])

    # Add 2nd participant (still < 3)
    join_discussion_room(room["id"], username="User2")
    with pytest.raises(InsufficientParticipantsError):
        start_discussion_room(room["id"])


def test_discussion_ready_at_3_participants_and_starts_successfully():
    room = create_discussion_room("disc_01", created_by_username="User1")
    join_discussion_room(room["id"], username="User2")
    room, _ = join_discussion_room(room["id"], username="User3")

    assert len(room["participants"]) == 3
    assert room["status"] == "ready"

    # Now starting succeeds
    started_room = start_discussion_room(room["id"])
    assert started_room["status"] == "in_progress"
    assert started_room["started_at"] is not None


def test_reject_ninth_participant_when_room_full():
    room = create_discussion_room("disc_01", created_by_username="User1")
    for i in range(2, 9):  # Adds User2, User3, User4, User5, User6, User7, User8
        join_discussion_room(room["id"], username=f"User{i}")

    assert len(room["participants"]) == 8

    # 9th participant must be rejected
    with pytest.raises(RoomFullError):
        join_discussion_room(room["id"], username="User9")


# =============================================================================
# 3. Room Lifecycle (Join, Leave, Complete)
# =============================================================================
def test_participant_leave_and_revert_to_waiting_if_below_min():
    room = create_discussion_room("disc_01", created_by_username="User1")
    join_discussion_room(room["id"], username="User2")
    join_discussion_room(room["id"], username="User3")
    assert room["status"] == "ready"

    # User3 leaves
    updated_room = leave_discussion_room(room["id"], "User3")
    assert len(updated_room["participants"]) == 2
    assert updated_room["status"] == "waiting"


def test_discussion_room_complete():
    room = create_discussion_room("disc_01", created_by_username="User1")
    join_discussion_room(room["id"], username="User2")
    join_discussion_room(room["id"], username="User3")
    start_discussion_room(room["id"])

    completed = complete_discussion_room(room["id"])
    assert completed["status"] == "completed"
    assert completed["ended_at"] is not None


def test_invalid_room_not_found():
    with pytest.raises(RoomNotFoundError):
        get_discussion_room("non_existent_room_999")


# =============================================================================
# 4. Discussion Metrics & Balance Calculations
# =============================================================================
def test_calculate_discussion_metrics_balanced():
    # 5 participants, 15 min (900s), user spoke for 180s (20% airtime, fair share is 20%)
    metrics = calculate_discussion_metrics(
        user_transcript="I agree with your point, but another perspective is that automation drives efficiency. What do you think?",
        speaking_time_seconds=180.0,
        total_discussion_duration_seconds=900.0,
        participant_count=5,
        speaking_turns=4
    )
    assert metrics["speaking_percentage"] == 20.0
    assert metrics["fair_share_percentage"] == 20.0
    assert metrics["conversational_balance"] == "balanced"
    assert metrics["collaborative_phrases_count"] >= 1  # "I agree with"
    assert metrics["respectful_disagreements_count"] >= 1  # "another perspective"
    assert metrics["questions_asked"] >= 1  # "?" and "what do you think"


def test_calculate_discussion_metrics_high_airtime():
    metrics = calculate_discussion_metrics(
        user_transcript="I spoke constantly throughout the call without stopping.",
        speaking_time_seconds=600.0,  # 66% of 900s for 5 people
        total_discussion_duration_seconds=900.0,
        participant_count=5,
        speaking_turns=8
    )
    assert metrics["conversational_balance"] == "high_airtime"
    assert "commanded a large share" in metrics["balance_summary"]


def test_calculate_discussion_metrics_silent_participant():
    metrics = calculate_discussion_metrics(
        user_transcript="",
        speaking_time_seconds=0.0,
        total_discussion_duration_seconds=900.0,
        participant_count=5,
        speaking_turns=0
    )
    assert metrics["conversational_balance"] == "silent"
    assert metrics["speaking_turns"] == 0


# =============================================================================
# 5. Full Individual Analysis & Determinism
# =============================================================================
def test_analyze_group_discussion_contribution_deterministic():
    text = (
        "Building on what Elena noted, we should consider risk factors carefully. "
        "I agree that product velocity is essential, but while that is true, "
        "we cannot compromise system reliability. How would the team manage outages?"
    )
    res1 = analyze_group_discussion_contribution(
        user_transcript=text,
        speaking_time_seconds=90.0,
        total_discussion_duration_seconds=900.0,
        participant_count=6,
        speaking_turns=3,
        topic_id="disc_03"
    )
    res2 = analyze_group_discussion_contribution(
        user_transcript=text,
        speaking_time_seconds=90.0,
        total_discussion_duration_seconds=900.0,
        participant_count=6,
        speaking_turns=3,
        topic_id="disc_03"
    )

    assert res1["communication_score"] >= 80
    assert res1["discussion_metrics"]["collaborative_phrases_count"] >= 2
    assert res1["discussion_metrics"]["respectful_disagreements_count"] >= 1
    assert res1["discussion_metrics"]["questions_asked"] >= 1
    assert "say_it_better" in res1
    assert len(res1["positive_feedback"]) >= 1

    # 100% Deterministic match
    assert res1 == res2
