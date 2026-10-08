"""
ConversX SQLAlchemy Database Entities for PostgreSQL.
Privacy-First Design: stores scores, metrics, timestamps, and moderation audits.
Never stores raw audio or private user communication text by default.
"""
from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        JSON,
        String,
        Text,
    )
    from sqlalchemy.orm import declarative_base, relationship

    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        username = Column(String(64), unique=True, index=True, nullable=False)
        email = Column(String(255), unique=True, index=True, nullable=False)
        hashed_password = Column(String(255), nullable=True)
        role = Column(String(20), default="user", nullable=False)
        is_active = Column(Boolean, default=True, nullable=False)
        is_banned = Column(Boolean, default=False, nullable=False)
        created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

        practice_sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")
        appeals = relationship("Appeal", back_populates="user", cascade="all, delete-orphan")

    class PracticeSession(Base):
        __tablename__ = "practice_sessions"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
        scenario_id = Column(String(64), index=True, nullable=False)
        practice_type = Column(String(32), default="casual", nullable=False)
        attempt_number = Column(Integer, default=1, nullable=False)
        score = Column(Integer, nullable=False)
        delivery_score = Column(Integer, nullable=True)
        wpm = Column(Float, nullable=True)
        filler_rate = Column(Float, nullable=True)
        speaking_duration = Column(Float, nullable=True)
        is_voice = Column(Boolean, default=False, nullable=False)
        dimension_scores = Column(JSON, nullable=True)
        detected_issues_count = Column(Integer, default=0, nullable=False)
        created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

        user = relationship("User", back_populates="practice_sessions")

    class ModerationEvent(Base):
        __tablename__ = "moderation_events"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String(36), index=True, nullable=True)
        content_hash = Column(String(64), index=True, nullable=False)
        severity = Column(Integer, default=0, nullable=False)
        status = Column(String(32), default="safe", nullable=False)
        matched_rules = Column(JSON, nullable=True)
        action_taken = Column(String(32), default="none", nullable=False)
        created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    class Appeal(Base):
        __tablename__ = "appeals"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
        violation_id = Column(String(64), index=True, nullable=False)
        reason = Column(Text, nullable=False)
        status = Column(String(32), default="pending", nullable=False)
        admin_decision = Column(String(32), nullable=True)
        admin_notes = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
        reviewed_at = Column(DateTime, nullable=True)

        user = relationship("User", back_populates="appeals")

    class AdminAuditLog(Base):
        __tablename__ = "admin_audit_logs"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        admin_id = Column(String(64), index=True, nullable=False)
        action = Column(String(64), nullable=False)
        target_id = Column(String(64), nullable=False)
        details = Column(JSON, nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


    class DiscussionRoom(Base):
        __tablename__ = "discussion_rooms"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        topic_id = Column(String(64), index=True, nullable=False)
        topic_title = Column(String(255), nullable=False)
        status = Column(String(32), default="waiting", nullable=False)  # waiting, in_progress, completed, cancelled
        min_participants = Column(Integer, default=3, nullable=False)
        max_participants = Column(Integer, default=8, nullable=False)
        duration_seconds = Column(Integer, default=900, nullable=False)  # 15 minutes default
        created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
        started_at = Column(DateTime, nullable=True)
        ended_at = Column(DateTime, nullable=True)

        participants = relationship("DiscussionParticipant", back_populates="room", cascade="all, delete-orphan")
        sessions = relationship("DiscussionSession", back_populates="room", cascade="all, delete-orphan")

    class DiscussionParticipant(Base):
        __tablename__ = "discussion_participants"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        room_id = Column(String(36), ForeignKey("discussion_rooms.id"), index=True, nullable=False)
        user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
        username = Column(String(64), nullable=False)
        is_ready = Column(Boolean, default=False, nullable=False)
        is_muted = Column(Boolean, default=False, nullable=False)
        speaking_time_seconds = Column(Float, default=0.0, nullable=False)
        speaking_turns = Column(Integer, default=0, nullable=False)
        joined_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
        left_at = Column(DateTime, nullable=True)

        room = relationship("DiscussionRoom", back_populates="participants")

    class DiscussionSession(Base):
        __tablename__ = "discussion_sessions"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        room_id = Column(String(36), ForeignKey("discussion_rooms.id"), index=True, nullable=False)
        user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
        username = Column(String(64), nullable=False)
        score = Column(Integer, nullable=False)
        dimension_scores = Column(JSON, nullable=True)
        discussion_metrics = Column(JSON, nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

        room = relationship("DiscussionRoom", back_populates="sessions")


    class UserAIConnection(Base):
        __tablename__ = "user_ai_connections"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
        provider = Column(String(32), nullable=False)  # 'openai' or 'gemini'
        encrypted_key = Column(Text, nullable=False)
        masked_key = Column(String(64), nullable=False)
        status = Column(String(32), default="connected", nullable=False)  # 'connected', 'error', 'not_connected'
        is_preferred = Column(Boolean, default=False, nullable=False)
        last_tested_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

except ImportError:
    Base = None
    User = None
    PracticeSession = None
    ModerationEvent = None
    Appeal = None
    AdminAuditLog = None
    DiscussionRoom = None
    DiscussionParticipant = None
    DiscussionSession = None
    UserAIConnection = None

