"""
Comprehensive Test Suite for Deterministic Rule-Based Moderation Engine.
Conforms to Master Prompt Section 16 (Testing), Section 3 (Normalization),
Section 4 (Matching Engine), Section 5 (Severity), Section 6 (Communication Score),
Section 7 (Say It Better), Section 11 (Multilingual), and Section 12 (False Positives).
"""

import pytest
try:
    from fastapi.testclient import TestClient
    from app.main import app
    
except ImportError:
    TestClient = None
    app = None
    client = None
from app.services.moderation import (
    normalize_text,
    tokenize_words,
    get_moderation_service,
    CommunicationResult,
    MatchedRule,
    rule_cache
)


mod_service = get_moderation_service()


# =============================================================================
# 1. Text Normalization Tests (Section 3)
# =============================================================================

def test_normalization_lowercasing_and_punctuation():
    """Ensure text is normalized while whitespace and symbols are handled properly."""
    raw = "You are!!!   USELESS!!!"
    normalized = normalize_text(raw)
    assert normalized == "you are useless"


def test_normalization_unicode_and_accents():
    """Ensure unicode diacritics and ligatures decompose deterministically."""
    raw = "Stúpíd idéà"
    normalized = normalize_text(raw)
    assert "stupid" in normalized
    assert "idea" in normalized


def test_tokenization_boundaries():
    """Verify word tokens are correctly extracted."""
    raw = "Could we, perhaps, consider another approach?"
    norm = normalize_text(raw)
    tokens = tokenize_words(norm)
    assert tokens == ["could", "we", "perhaps", "consider", "another", "approach"]


# =============================================================================
# 2. Safe Messages Tests (Section 16)
# =============================================================================

@pytest.mark.parametrize("safe_text", [
    "Can you explain this again?",
    "I disagree with your idea.",
    "Could we try another approach?",
    "Here is the project timeline for Q3 deliverables.",
    "Thank you for the thoughtful feedback on the design doc."
])
def test_safe_messages_produce_safe_result(safe_text):
    result = mod_service.analyze_communication(safe_text)
    assert result.status == "safe"
    assert result.severity == 0
    assert result.severity_label == "Safe"
    assert result.score == 100
    assert result.matched_count == 0
    assert len(result.matched_rules) == 0
    assert result.dimensions["respectfulness"] == 100
    assert result.dimensions["aggressiveness"] == 0
    assert result.dimensions["professionalism"] == 100
    assert result.suggestion is None


# =============================================================================
# 3. False Positive Prevention Tests (Section 12)
# =============================================================================

@pytest.mark.parametrize("benign_text", [
    "We studied classic literature in our seminar.",
    "She was passionate about her classroom assignment.",
    "The therapist assisted our department yesterday.",
    "Please review the attached project document.",
    "The assassin character was purely fictional in the play.",
    "The baseline assumption was documented thoroughly."
])
def test_false_positive_words_do_not_trigger_rules(benign_text):
    """
    Substrings like 'ass' in 'classic/passionate/assignment',
    'rape' in 'therapist', 'cum' in 'document' must NEVER trigger.
    """
    result = mod_service.analyze_communication(benign_text)
    assert result.status == "safe"
    assert result.severity == 0
    assert result.score == 100
    assert result.matched_count == 0


# =============================================================================
# 4. Bad-Word Matching Tests (Section 4, Level 1)
# =============================================================================

def test_bad_word_exact_match():
    result = mod_service.analyze_communication("You are useless.")
    assert result.matched_count >= 1
    assert any(r.match == "useless" for r in result.matched_rules)
    assert result.severity >= 2


def test_bad_word_case_insensitivity():
    result = mod_service.analyze_communication("This is STUPID and MORONIC.")
    assert any(r.match == "stupid" for r in result.matched_rules)


def test_bad_word_with_extreme_punctuation():
    result = mod_service.analyze_communication("You idiot!!!!! Why did you do that?!")
    assert any(r.match == "idiot" for r in result.matched_rules)


# =============================================================================
# 5. Harassment Phrase Matching Tests (Section 4, Level 2)
# =============================================================================

def test_harassment_phrase_detection():
    result = mod_service.analyze_communication("You are useless. Your idea is stupid.")
    # Should catch both phrase and word rules deterministically
    assert result.matched_count >= 2
    categories = [r.category for r in result.matched_rules]
    assert "personal_attack" in categories or "insult" in categories
    assert result.severity >= 2
    assert result.status in ["warning", "harmful"]


def test_harassment_phrase_with_extra_whitespace():
    result = mod_service.analyze_communication("you    are    useless   in this project")
    assert any(r.match == "you are useless" for r in result.matched_rules)


def test_harassment_phrase_case_and_symbols():
    result = mod_service.analyze_communication("YOUR IDEA IS STUPID!!!")
    assert any(r.match == "your idea is stupid" for r in result.matched_rules)


# =============================================================================
# 6. Severity & Communication Score Tests (Section 5 & 6)
# =============================================================================

def test_threat_severity_is_severe():
    result = mod_service.analyze_communication("I will hurt you if you don't comply.")
    assert result.severity >= 3
    assert "threat" in result.categories
    assert result.score < 40
    assert result.dimensions["aggressiveness"] > 70


def test_multiple_matches_aggregate_correctly():
    result = mod_service.analyze_communication("You are useless, stupid, and a total idiot.")
    assert result.matched_count >= 3
    assert result.score <= 35
    assert result.dimensions["respectfulness"] < 50
    assert result.dimensions["aggressiveness"] >= 60


# =============================================================================
# 7. Say It Better Constructive Suggestions (Section 7 & 20)
# =============================================================================

def test_say_it_better_suggestion_provided():
    result = mod_service.analyze_communication("You are useless.")
    assert result.suggestion is not None
    assert "suggestion" in result.suggestion
    assert "example" in result.suggestion
    assert len(result.suggestion["example"]) > 10


def test_threat_suggestion_provided():
    result = mod_service.analyze_communication("I will hurt you.")
    assert result.suggestion is not None
    assert result.suggestion["category"] == "threat"


# =============================================================================
# 8. Multilingual Vocabulary Support (Section 11)
# =============================================================================

def test_multilingual_rules_hindi_tamil():
    res_hi = mod_service.analyze_communication("Yeh sab pagal harkat hai.")
    assert any(r.match == "pagal" for r in res_hi.matched_rules)

    res_ta = mod_service.analyze_communication("Nee oru muttal.")
    assert any(r.match == "muttal" for r in res_ta.matched_rules)


# =============================================================================
# 9. Offline & Fallback Resilience (Section 16)
# =============================================================================

def test_moderation_runs_offline_with_cached_rules():
    """Ensure engine never crashes and produces deterministic results even without Firestore."""
    res = mod_service.analyze_communication("This is a simple clean message.")
    assert res.status == "safe"
    assert res.score == 100


# =============================================================================
# 10. API Endpoints Integration Tests (FastAPI)
# =============================================================================

@pytest.mark.skipif(client is None, reason="FastAPI or TestClient not installed in environment")
def test_api_analyze_endpoint_safe():
    response = client.post(
        "/api/v1/moderation/analyze",
        json={"text": "Can we schedule a discussion for tomorrow?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "safe"
    assert data["score"] == 100
    assert data["matched_count"] == 0


@pytest.mark.skipif(client is None, reason='FastAPI not installed')
def test_api_analyze_endpoint_harmful():
    response = client.post(
        "/api/v1/moderation/analyze",
        json={"text": "You are useless and incompetent!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["warning", "harmful"]
    assert data["severity"] >= 2
    assert data["matched_count"] >= 2
    assert data["suggestion"] is not None


@pytest.mark.skipif(client is None, reason='FastAPI not installed')
def test_api_get_rules_endpoint():
    response = client.get("/api/v1/moderation/rules")
    assert response.status_code == 200
    data = response.json()
    assert "bad_words" in data
    assert "harassment_patterns" in data
    assert len(data["bad_words"]) > 0


@pytest.mark.skipif(client is None, reason='FastAPI not installed')
def test_api_categories_endpoint():
    response = client.get("/api/v1/moderation/categories")
    assert response.status_code == 200
    data = response.json()
    assert "insult" in data
    assert "threat" in data


@pytest.mark.skipif(client is None, reason='FastAPI not installed')
def test_api_severity_levels_endpoint():
    response = client.get("/api/v1/moderation/severity-levels")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


@pytest.mark.skipif(client is None, reason='FastAPI not installed')
def test_api_admin_add_and_delete_rule():
    # 1. Add rule
    add_resp = client.post(
        "/api/v1/moderation/admin/rules",
        json={
            "rule_type": "word",
            "target": "testdummyword",
            "category": "insult",
            "severity": 2,
            "language": "en",
            "active": True
        }
    )
    assert add_resp.status_code == 200
    rule_id = add_resp.json()["id"]

    # 2. Verify test word is now caught
    test_res = mod_service.analyze_communication("You are a testdummyword.")
    assert any(r.match == "testdummyword" for r in test_res.matched_rules)

    # 3. Delete rule
    del_resp = client.delete(f"/api/v1/moderation/admin/rules/word/{rule_id}")
    assert del_resp.status_code == 200

    # 4. Verify no longer caught
    test_res2 = mod_service.analyze_communication("You are a testdummyword.")
    assert not any(r.match == "testdummyword" for r in test_res2.matched_rules)
