"""
ConversX Production Architecture Tests.
Verifies Health endpoints, Appeals workflow, Admin governance & authentication,
Modular NLP services, and Whisper STT service singleton.
"""
from __future__ import annotations

import os
import pytest

# 1. Modular NLP Tests
from app.services.nlp.grammar import analyze_grammar
from app.services.nlp.vocabulary import analyze_vocabulary
from app.services.nlp.clarity import analyze_clarity
from app.services.nlp.confidence import analyze_confidence
from app.services.nlp.structure import analyze_structure
from app.services.nlp.analyzer import run_nlp_analysis

def test_nlp_grammar_module():
    clean_res = analyze_grammar("This is a clean and grammatically sound sentence.")
    assert clean_res["score"] == 100
    assert len(clean_res["issues"]) == 0

    bad_res = analyze_grammar("We went to the the store and don't know nothing about a apple.")
    assert bad_res["score"] < 80
    assert len(bad_res["issues"]) >= 2
    rule_ids = [i["rule_id"] for i in bad_res["issues"]]
    assert "duplicate_adjacent_word" in rule_ids
    assert "double_negative" in rule_ids or "article_a_before_vowel" in rule_ids

def test_nlp_vocabulary_module():
    words_rich = ["robust", "scalable", "architecture", "optimized", "throughput", "latency", "pipeline"]
    rich_res = analyze_vocabulary(words_rich)
    assert rich_res["score"] >= 80
    assert rich_res["ttr"] == 1.0

    words_repetitive = ["good", "thing", "good", "thing", "very", "very", "stuff", "stuff"]
    rep_res = analyze_vocabulary(words_repetitive)
    assert rep_res["score"] < 70
    assert len(rep_res["overused_words"]) >= 2

def test_nlp_clarity_module():
    wordy_text = "Due to the fact that we need to hurry, in order to finish, we worked late."
    clarity_res = analyze_clarity(wordy_text, sentences=["Due to the fact that we need to hurry, in order to finish, we worked late."])
    assert clarity_res["score"] <= 80
    assert len(clarity_res["wordy_phrases"]) >= 2

def test_nlp_confidence_module():
    hedged_text = "I guess maybe kinda we should look at this, sorry but just my opinion."
    conf_res = analyze_confidence(hedged_text)
    assert conf_res["score"] <= 60
    assert len(conf_res["hedges_detected"]) >= 2

    assertive_text = "I recommend our team implement this solution. Our analysis shows clear gains."
    assert_res = analyze_confidence(assertive_text)
    assert assert_res["score"] >= 85
    assert len(assert_res["assertive_detected"]) >= 2

def test_nlp_structure_module():
    text_full = "Good morning everyone. Our main proposal is to migrate to PostgreSQL. In particular, this reduces costs. In conclusion, thank you for your time."
    struct_res = analyze_structure(text_full, sentence_count=4)
    assert struct_res["score"] >= 85
    assert struct_res["has_opening"] is True
    assert struct_res["has_support"] is True
    assert struct_res["has_conclusion"] is True

def test_nlp_unified_analyzer_facade():
    sample = "Hello team. I recommend we deploy the new microservice architecture because our latency dropped significantly. In conclusion, thank you."
    res = run_nlp_analysis(sample)
    assert res["word_count"] > 10
    assert res["sentence_count"] >= 2
    assert "grammar" in res
    assert "vocabulary" in res
    assert "clarity" in res
    assert "confidence" in res
    assert "structure" in res

# 2. Whisper STT Service Tests
from app.services.whisper_stt import get_whisper_config, transcribe_audio_file

def test_whisper_config_defaults():
    model, device, compute_type = get_whisper_config()
    assert isinstance(model, str)
    assert device in ["cpu", "cuda"]
    assert isinstance(compute_type, str)

def test_whisper_transcribe_fallback():
    result = transcribe_audio_file("nonexistent_test_audio.webm")
    assert "transcript" in result
    assert "duration_seconds" in result
    assert "segments" in result
    assert len(result["transcript"]) > 0

# 3. Database Health Check Test
from app.db.session import check_db_health

def test_db_health_check_operational():
    is_healthy = check_db_health()
    assert is_healthy is True

# 4. Appeal System & Admin Governance Tests (Protected for FastAPI environment)
try:
    from app.routers.appeals import submit_appeal, get_appeal_status, SubmitAppealRequest, _IN_MEMORY_APPEALS
    from app.routers.admin import verify_admin_key, decide_appeal, AppealDecisionRequest, ADMIN_SECRET_KEY
    from fastapi import HTTPException
    HAS_FASTAPI = True
except Exception:
    HAS_FASTAPI = False

@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed in host environment")
def test_admin_auth_verification():
    valid = verify_admin_key(ADMIN_SECRET_KEY)
    assert valid == ADMIN_SECRET_KEY

    with pytest.raises(HTTPException) as exc_info_none:
        verify_admin_key(None)
    assert exc_info_none.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info_bad:
        verify_admin_key("wrong-secret-key")
    assert exc_info_bad.value.status_code == 403

@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed in host environment")
@pytest.mark.anyio
async def test_appeal_submission_and_decision_lifecycle():
    req = SubmitAppealRequest(
        user_id="user_test_99",
        violation_id="viol_456",
        reason="My statement was a direct quote from a textbook and not harassment."
    )
    appeal_res = await submit_appeal(req)
    appeal_id = appeal_res.appeal_id
    assert appeal_res.status == "pending"
    assert appeal_res.user_id == "user_test_99"

    status_res = await get_appeal_status(appeal_id)
    assert status_res.appeal_id == appeal_id
    assert status_res.status == "pending"

    decision_req = AppealDecisionRequest(decision="overturned", admin_notes="Valid context verified.")
    decide_res = await decide_appeal(appeal_id, decision_req)
    assert decide_res["status"] == "success"
    assert decide_res["appeal"]["status"] == "approved"
    assert decide_res["appeal"]["admin_decision"] == "overturned"

    updated_status = await get_appeal_status(appeal_id)
    assert updated_status.status == "approved"
    assert updated_status.admin_decision == "overturned"
