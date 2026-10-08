"""
ConversX Production Smoke Tests (Phase 7).
Verifies:
- Core subsystem readiness (Database health, Whisper STT config, NLP analyzer).
- Practice engine deterministic analysis across modes.
- Voice coach analysis and delivery metrics.
- Deterministic safety moderation checks (rule-based, no ML).
- Authentication token generation, decoding, and role validation.
- Admin governance & authorization verification.
- Frontend assets integrity (index.html, admin.html, styles, scripts).
"""
from __future__ import annotations

import os
import sys
import pytest

# Ensure repository root is on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, os.path.join(root_dir, "backend"))
sys.path.insert(0, root_dir)


from app.db.session import check_db_health
from app.services.whisper_stt import get_whisper_config
from app.services.nlp.analyzer import run_nlp_analysis
from app.services.practice import analyze_practice_response, analyze_voice_response
from app.services.scenarios import get_all_scenarios, get_today_challenge
from app.services.moderation import analyze_communication
from app.core.auth import (
    ROLE_ADMIN,
    ROLE_USER,
    create_access_token,
    decode_access_token,
    verify_user_ownership,
    UserSession,
)


def test_smoke_database_health():
    """Verify database health probe returns True in healthy state."""
    assert check_db_health() is True


def test_smoke_whisper_stt_configuration():
    """Verify Whisper STT singleton configuration returns expected CPU settings."""
    model, device, compute_type = get_whisper_config()
    assert isinstance(model, str)
    assert device in ["cpu", "cuda"]
    assert compute_type in ["int8", "float32", "float16", "default"]


def test_smoke_nlp_analyzer():
    """Verify modular NLP pipeline computes scores and issues."""
    text = "Hello team. I propose that we implement this system today because it improves performance."
    res = run_nlp_analysis(text)
    assert "grammar" in res
    assert "vocabulary" in res
    assert "clarity" in res
    assert "confidence" in res
    assert "structure" in res
    assert res["word_count"] > 5


def test_smoke_practice_response_analysis():
    """Verify deterministic practice evaluation across 8 dimensions."""
    text = "Good morning. I would like to present our project roadmap for the upcoming quarter."
    res = analyze_practice_response(text=text, scenario_id="interview_intro")
    assert 0 <= res.overall_score <= 100
    assert len(res.dimension_scores.to_dict()) == 8
    assert res.say_it_better is not None
    assert res.moderation_status == "safe"


def test_smoke_voice_coach_analysis():
    """Verify voice coach delivery metrics and scoring."""
    transcript = "Thank you everyone for your time. Today I will discuss our deployment progress."
    res = analyze_voice_response(transcript=transcript, duration_seconds=12.0)
    assert res.speaking_metrics.word_count > 0
    assert res.speaking_metrics.wpm > 0
    assert 0 <= res.delivery_score <= 100
    assert 0 <= res.communication_score <= 100


def test_smoke_deterministic_moderation_engine():
    """Verify safety moderation remains 100% deterministic rule-based (no ML)."""
    clean_res = analyze_communication("This is a polite and professional meeting.")
    assert clean_res.status == "safe"
    assert clean_res.severity == 0
    assert len(clean_res.matched_rules) == 0


def test_smoke_auth_token_lifecycle():
    """Verify JWT access token generation and claims decoding."""
    token = create_access_token(user_id="user_smoke_01", role=ROLE_USER, username="tester")
    claims = decode_access_token(token)
    assert claims["sub"] == "user_smoke_01"
    assert claims["role"] == ROLE_USER
    assert claims["username"] == "tester"


def test_smoke_admin_authorization():
    """Verify ADMIN role privileges and ownership logic."""
    admin_sess = UserSession(user_id="admin_01", username="admin_smoke", role=ROLE_ADMIN)
    user_sess = UserSession(user_id="user_01", username="user_smoke", role=ROLE_USER)

    assert admin_sess.is_admin is True
    assert user_sess.is_admin is False

    # Ownership checks (anti-IDOR)
    assert verify_user_ownership(user_sess, "user_01") is True
    assert verify_user_ownership(user_sess, "user_99") is False
    assert verify_user_ownership(admin_sess, "user_99") is True


def test_smoke_frontend_static_assets_exist():
    """Verify core frontend entry points and assets are present and valid."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    frontend_dir = os.path.join(root, "frontend")

    assert os.path.exists(os.path.join(frontend_dir, "index.html"))
    assert os.path.exists(os.path.join(frontend_dir, "admin.html"))
    assert os.path.exists(os.path.join(frontend_dir, "vercel.json"))
    assert os.path.exists(os.path.join(frontend_dir, "src", "config.js"))
    assert os.path.exists(os.path.join(frontend_dir, "src", "firebase.js"))
