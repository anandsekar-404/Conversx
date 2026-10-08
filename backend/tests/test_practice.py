"""
Comprehensive Test Suite for ConversX Communication Practice Engine.
Tests all 8 dimensions, scoring formula, filler detection, grammar, vocabulary,
structure, confidence, professionalism, scenarios, and Say It Better engine.
"""

import pytest
from app.services.scenarios import (
    PRACTICE_MODES,
    get_all_scenarios,
    get_scenario_by_id,
    get_today_challenge,
)
from app.services.practice import (
    analyze_practice_response,
    analyze_fillers,
    analyze_grammar,
    analyze_clarity_and_wordiness,
    analyze_vocabulary,
    analyze_confidence,
    analyze_professionalism,
    analyze_structure,
    generate_say_it_better,
    tokenize_words,
    normalize_text,
)

try:
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
except ImportError:
    TestClient = None
    app = None
    client = None


# =============================================================================
# 1. Scenarios & Challenge Tests
# =============================================================================

def test_practice_modes_defined():
    modes = [m["id"] for m in PRACTICE_MODES]
    assert "casual" in modes
    assert "interview" in modes
    assert "presentation" in modes
    assert "professional" in modes
    assert "challenge" in modes


def test_scenario_counts_and_modes():
    all_scenarios = get_all_scenarios()
    assert len(all_scenarios) >= 20

    casual = get_all_scenarios(mode="casual")
    assert len(casual) >= 6

    interview = get_all_scenarios(mode="interview")
    assert len(interview) >= 6

    presentation = get_all_scenarios(mode="presentation")
    assert len(presentation) >= 4

    professional = get_all_scenarios(mode="professional")
    assert len(professional) >= 5


def test_lookup_scenario_by_id():
    sc = get_scenario_by_id("int_01")
    assert sc is not None
    assert sc["title"] == "Tell Me About Yourself"
    assert "STAR" in sc["guidance"] or "Present-Past-Future" in sc["guidance"]


def test_today_challenge_deterministic():
    challenge = get_today_challenge()
    assert challenge is not None
    assert "id" in challenge
    assert "title" in challenge
    assert "prompt" in challenge
    assert challenge["mode"] == "challenge"


# =============================================================================
# 2. Filler Words Detection
# =============================================================================

def test_filler_words_detected():
    text = "I actually think this project is basically very useful and like it can help students."
    fillers, total = analyze_fillers(text)
    assert total >= 3
    filler_names = [f["filler"] for f in fillers]
    assert "actually" in filler_names
    assert "basically" in filler_names
    assert "like" in filler_names


def test_clean_speech_has_zero_fillers():
    text = "Good morning team. We have scheduled the project review for Thursday afternoon."
    fillers, total = analyze_fillers(text)
    assert total == 0
    assert len(fillers) == 0


# =============================================================================
# 3. Grammar Issues Detection
# =============================================================================

def test_grammar_article_usage():
    text = "She presented a apple to the teacher."
    issues = analyze_grammar(text)
    assert any(i["type"] == "article_usage" and i["matched"] == "a apple" for i in issues)


def test_grammar_duplicate_adjacent_word():
    text = "We will go to the the store tomorrow."
    issues = analyze_grammar(text)
    assert any(i["type"] == "duplicate_word" for i in issues)


def test_grammar_double_negative():
    text = "We don't have no time for delay."
    issues = analyze_grammar(text)
    assert any(i["type"] == "double_negative" for i in issues)


# =============================================================================
# 4. Clarity, Wordiness, and Sentence Length
# =============================================================================

def test_wordiness_detection():
    text = "Due to the fact that we are ready, in order to succeed we must launch."
    norm = normalize_text(text)
    tokens = tokenize_words(norm)
    score, wordy, long_s = analyze_clarity_and_wordiness(text, tokens)
    assert len(wordy) >= 2
    assert score < 100


def test_overly_long_sentences_penalized():
    long_sentence = "We must immediately evaluate every single potential risk associated with this new software architecture before we can even begin to consider presenting it to our stakeholders who are expecting complete certainty."
    norm = normalize_text(long_sentence)
    tokens = tokenize_words(norm)
    score, wordy, long_s = analyze_clarity_and_wordiness(long_sentence, tokens)
    assert len(long_s) >= 1
    assert score <= 88


# =============================================================================
# 5. Vocabulary & Lexical Diversity (TTR)
# =============================================================================

def test_vocabulary_overused_basic_words():
    text = "This is a good thing and that good thing is very very nice stuff."
    norm = normalize_text(text)
    tokens = tokenize_words(norm)
    score, basic_counts, ttr = analyze_vocabulary(tokens)
    assert "good" in basic_counts
    assert "thing" in basic_counts
    assert score < 85


# =============================================================================
# 6. Confidence & Hedging Markers
# =============================================================================

def test_hedging_phrases_penalize_confidence():
    text = "I think maybe I'm not sure but I guess this might work."
    score, hedges, assertive = analyze_confidence(text)
    assert len(hedges) >= 2
    assert score <= 60


def test_assertive_phrases_boost_confidence():
    text = "I recommend this architecture because our goal is high throughput and I delivered the prototype."
    score, hedges, assertive = analyze_confidence(text)
    assert len(assertive) >= 2
    assert score >= 90


# =============================================================================
# 7. Professionalism & Contractions
# =============================================================================

def test_informal_contractions_penalize_professionalism():
    text = "I gonna do this cuz u told me to."
    norm = normalize_text(text)
    tokens = tokenize_words(norm)
    score, informal = analyze_professionalism(text, tokens)
    assert len(informal) >= 2
    assert score < 85


def test_excessive_capitalization_detected():
    text = "WE MUST STOP THIS RIGHT NOW."
    norm = normalize_text(text)
    tokens = tokenize_words(norm)
    score, informal = analyze_professionalism(text, tokens)
    assert any("Excessive capitalization" in item for item in informal)


# =============================================================================
# 8. Structure Analysis
# =============================================================================

def test_complete_structure():
    text = "Good morning. I want to discuss the new roadmap. Because client demand has increased, I recommend adding search. In conclusion, thank you for your support."
    score, components = analyze_structure(text, sentence_count=4)
    assert components["opening"] is True
    assert components["main_point"] is True
    assert components["supporting_detail"] is True
    assert components["conclusion"] is True
    assert score == 100


# =============================================================================
# 9. Respectfulness & Moderation Reusability
# =============================================================================

def test_respectfulness_reuses_moderation():
    harmful_text = "You are useless and your idea is stupid."
    res = analyze_practice_response(harmful_text)
    assert res.dimension_scores.respectfulness < 50
    assert res.moderation_status in ["warning", "harmful"]


# =============================================================================
# 10. Scoring Formula Verification
# =============================================================================

def test_scoring_formula_weights():
    text = "Good morning. I am writing to propose a revised timeline for our project launch. Because our core deliverables need thorough verification, I recommend we schedule the deployment for next Tuesday. In summary, this guarantees stability for our clients."
    res = analyze_practice_response(text)
    dims = res.dimension_scores

    # Formula:
    # 0.20*clarity + 0.15*grammar + 0.10*vocabulary + 0.15*confidence +
    # 0.15*prof + 0.10*respect + 0.10*filler + 0.05*struct
    expected_score = round(
        0.20 * dims.clarity
        + 0.15 * dims.grammar
        + 0.10 * dims.vocabulary
        + 0.15 * dims.confidence
        + 0.15 * dims.professionalism
        + 0.10 * dims.respectfulness
        + 0.10 * dims.filler_control
        + 0.05 * dims.structure
    )
    assert res.overall_score == expected_score


# =============================================================================
# 11. Deterministic "Say It Better" Engine
# =============================================================================

def test_say_it_better_removes_fillers_and_wordiness():
    raw = "I actually think this project is basically very useful in order to help students."
    fillers, _ = analyze_fillers(raw)
    _, wordy, _ = analyze_clarity_and_wordiness(raw, tokenize_words(normalize_text(raw)))
    grammar = analyze_grammar(raw)
    _, informal = analyze_professionalism(raw, tokenize_words(normalize_text(raw)))

    sib = generate_say_it_better(raw, fillers, wordy, grammar, informal)
    assert "actually" not in sib.suggested_text.lower()
    assert "basically" not in sib.suggested_text.lower()
    assert "in order to" not in sib.suggested_text.lower()
    assert len(sib.improvements_made) >= 2


# =============================================================================
# 12. Strict Determinism
# =============================================================================

def test_practice_analysis_strict_determinism():
    input_text = "I want to share my perspective on the database migration plan."
    run1 = analyze_practice_response(input_text, "pro_03")
    run2 = analyze_practice_response(input_text, "pro_03")
    assert run1.overall_score == run2.overall_score
    assert run1.dimension_scores.to_dict() == run2.dimension_scores.to_dict()
    assert run1.say_it_better.suggested_text == run2.say_it_better.suggested_text


# =============================================================================
# 13. API Endpoint Tests (FastAPI Client)
# =============================================================================

@pytest.mark.skipif(client is None, reason="FastAPI not installed in host environment")
def test_api_practice_analyze_endpoint():
    resp = client.post(
        "/api/v1/practice/analyze",
        json={"text": "Good morning. I propose we launch on Thursday.", "scenario_id": "pro_01"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "dimension_scores" in data
    assert "say_it_better" in data
    assert data["overall_score"] >= 80


@pytest.mark.skipif(client is None, reason="FastAPI not installed in host environment")
def test_api_practice_scenarios_endpoint():
    resp = client.get("/api/v1/practice/scenarios?mode=interview")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 6
    assert all(item["mode"] == "interview" for item in data)


@pytest.mark.skipif(client is None, reason="FastAPI not installed in host environment")
def test_api_practice_daily_challenge_endpoint():
    resp = client.get("/api/v1/practice/challenges/today")
    assert resp.status_code == 200
    data = resp.json()
    assert "title" in data
    assert data["mode"] == "challenge"


@pytest.mark.skipif(client is None, reason="FastAPI not installed in host environment")
def test_api_record_session_and_progress_endpoint():
    rec_resp = client.post(
        "/api/v1/practice/session",
        json={
            "user_id": "test_user_42",
            "scenario_id": "int_01",
            "practice_type": "interview",
            "attempt_number": 1,
            "score": 85,
            "dimension_scores": {"clarity": 85, "grammar": 90},
            "detected_issues_count": 1
        }
    )
    assert rec_resp.status_code == 200

    prog_resp = client.get("/api/v1/progress?user_id=test_user_42")
    assert prog_resp.status_code == 200
    prog_data = prog_resp.json()
    assert prog_data["practice_sessions_count"] >= 1



# ---------------------------------------------------------------------------
# Phase 5: Voice Communication Coach Unit Tests
# ---------------------------------------------------------------------------
from app.services.practice import (
    calculate_speaking_metrics,
    calculate_delivery_score,
    analyze_voice_response,
    classify_pace_tempo,
    VOICE_DELIVERY_DISCLAIMER
)


def test_speaking_metrics_calculation():
    # 65 words over 30 seconds = 130.0 WPM (optimal range)
    words_13 = "This is a clean speech sample designed to test speaking metrics calculation accurately. "
    transcript = (words_13 * 5).strip()
    metrics = calculate_speaking_metrics(transcript, duration_seconds=30.0)

    assert metrics.word_count == 65
    assert metrics.duration_seconds == 30.0
    assert metrics.wpm == 130.0
    assert metrics.pace_category == "optimal"
    assert metrics.filler_count == 0
    assert metrics.filler_rate == 0.0


def test_speaking_metrics_with_fillers():
    # 19 words with 3 fillers ("um", "uh", "actually") over 10 seconds = 114.0 WPM
    text = "Hello um my name is Sarah and uh I am actually applying for the data science role here today."
    metrics = calculate_speaking_metrics(text, duration_seconds=10.0)

    assert metrics.word_count == 19
    assert metrics.duration_seconds == 10.0
    assert metrics.wpm == 114.0
    assert metrics.pace_category == "slow"
    assert metrics.filler_count == 3
    assert metrics.filler_rate > 15.0
    assert any(f["filler"] == "um" for f in metrics.detected_fillers)
    assert any(f["filler"] == "actually" for f in metrics.detected_fillers)


def test_speaking_metrics_zero_words_empty_transcript():
    metrics = calculate_speaking_metrics("", duration_seconds=15.0)
    assert metrics.word_count == 0
    assert metrics.wpm == 0.0
    assert metrics.pace_category == "none"
    assert metrics.filler_count == 0


def test_speaking_pace_classification_ranges():
    cat1, _ = classify_pace_tempo(85.0)
    assert cat1 == "very_slow"

    cat2, _ = classify_pace_tempo(110.0)
    assert cat2 == "slow"

    cat3, _ = classify_pace_tempo(138.0)
    assert cat3 == "optimal"

    cat4, _ = classify_pace_tempo(172.0)
    assert cat4 == "fast"

    cat5, _ = classify_pace_tempo(205.0)
    assert cat5 == "very_fast"


def test_delivery_score_optimal_vs_rushed():
    # Clean optimal response: 70 words, 30s = 140 WPM, 0 fillers
    sentence_14_words = "Today we present our new system that speeds up processing and simplifies data flow. "
    clean_text = (sentence_14_words * 5).strip()  # exactly 70 words
    metrics_optimal = calculate_speaking_metrics(clean_text, duration_seconds=30.0)
    score_opt, dims_opt, feedback_opt = calculate_delivery_score(metrics_optimal)

    assert metrics_optimal.word_count == 70
    assert metrics_optimal.wpm == 140.0
    assert dims_opt.pace == 100
    assert dims_opt.filler_control == 100
    assert score_opt >= 90
    assert len(feedback_opt["strengths"]) >= 1

    # Rushed, filler-laden response: 100 words in 30s = 200 WPM, high fillers
    filler_sentence = "Um basically like actually I think sort of like you know we really need help. "
    messy_text = (filler_sentence * 7).strip()
    metrics_messy = calculate_speaking_metrics(messy_text, duration_seconds=30.0)
    score_messy, dims_messy, feedback_messy = calculate_delivery_score(metrics_messy)

    assert metrics_messy.wpm >= 180.0
    assert dims_messy.pace <= 60
    assert dims_messy.filler_control <= 50
    assert score_messy <= 65
    assert len(feedback_messy["improvements"]) >= 1


def test_voice_response_analysis_complete():
    transcript = "Good afternoon. I am excited to share my experience building real-time data pipelines. In my last project, I reduced memory consumption by forty percent."
    res = analyze_voice_response(transcript, duration_seconds=20.0, scenario_id="int_01")

    assert res.transcript == transcript
    assert res.speaking_metrics.word_count > 0
    assert res.speaking_metrics.wpm > 0
    assert 0 <= res.delivery_score <= 100
    assert 0 <= res.communication_score <= 100
    assert res.moderation_status == "safe"
    assert "ConversX does not claim" in res.disclaimer


def test_voice_analysis_strict_determinism():
    transcript = "Hello everyone. Today I will demonstrate our communication platform designed for students and professionals."
    res1 = analyze_voice_response(transcript, duration_seconds=15.0)
    res2 = analyze_voice_response(transcript, duration_seconds=15.0)

    assert res1.delivery_score == res2.delivery_score
    assert res1.communication_score == res2.communication_score
    assert res1.speaking_metrics.wpm == res2.speaking_metrics.wpm
    assert res1.speaking_metrics.filler_rate == res2.speaking_metrics.filler_rate
    assert res1.delivery_dimensions == res2.delivery_dimensions
