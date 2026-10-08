"""
Tests for ConversX Personal AI Coach & Secure Provider Integration.
Tests:
- Authenticated AES/PBKDF2 encryption at rest with per-record salts and nonces.
- Ciphertext tamper detection and integrity validation.
- Per-user secret isolation (User A cannot access User B's keys).
- Masked key formatting without leaking raw secrets.
- Deletion removes secret permanently.
- Sanitized connection testing states.
- 4-part AI coaching structure & drill extensions (STAR interview & presentation).
- Strict non-interference: ConversX 8-dimension deterministic score is authoritative.
"""
import pytest
from app.services.ai_coach import (
    encrypt_api_key,
    decrypt_api_key,
    mask_api_key,
    save_user_ai_connection,
    get_user_ai_connections,
    delete_user_ai_connection,
    set_user_preferred_provider,
    get_decrypted_user_key,
    verify_ai_connection,
    generate_ai_coaching,
    generate_deterministic_fallback_coaching,
    PROVIDER_OPENAI,
    PROVIDER_GEMINI,
)


def test_encryption_at_rest_and_decryption():
    master = "test-master-secret-12345"
    raw_key = "sk-proj-abc123xyz890secretkey"

    token1 = encrypt_api_key(raw_key, master)
    token2 = encrypt_api_key(raw_key, master)

    # Different salts and nonces ensure ciphertexts are distinct
    assert token1 != token2
    assert token1 != raw_key
    assert token2 != raw_key

    # Decrypts cleanly
    decrypted1 = decrypt_api_key(token1, master)
    decrypted2 = decrypt_api_key(token2, master)
    assert decrypted1 == raw_key
    assert decrypted2 == raw_key


def test_ciphertext_tamper_detection():
    master = "test-master-secret-12345"
    raw_key = "sk-proj-tampertest-12345678"
    token = encrypt_api_key(raw_key, master)

    # Flip a byte in the base64 token
    chars = list(token)
    chars[20] = "X" if chars[20] != "X" else "Y"
    tampered = "".join(chars)

    with pytest.raises(ValueError) as exc:
        decrypt_api_key(tampered, master)
    assert "integrity" in str(exc.value).lower() or "validation" in str(exc.value).lower() or "base64" in str(exc.value).lower()


def test_mask_api_key_security():
    openai_key = "sk-proj-1234567890abcdef"
    gemini_key = "AIzaSy1234567890abcdef"

    masked_o = mask_api_key(openai_key, "openai")
    masked_g = mask_api_key(gemini_key, "gemini")

    assert "sk-proj" in masked_o
    assert "cdef" in masked_o
    assert "1234567890" not in masked_o  # Raw body is redacted
    assert "••••" in masked_o

    assert "AIzaSy" in masked_g
    assert "cdef" in masked_g
    assert "1234567890" not in masked_g
    assert "••••" in masked_g


def test_per_user_isolation_and_credential_storage():
    user_a = "usr_alice_101"
    user_b = "usr_bob_202"

    key_a = "sk-proj-alice-secret-key-1111"
    key_b = "sk-proj-bob-secret-key-2222"

    # Save for both
    res_a = save_user_ai_connection(user_a, "openai", key_a)
    res_b = save_user_ai_connection(user_b, "openai", key_b)

    assert res_a["status"] == "connected"
    assert res_b["status"] == "connected"
    assert "sk-proj-alice-secret-key-1111" not in res_a["masked_key"]
    assert "sk-proj-bob-secret-key-2222" not in res_b["masked_key"]

    # Retrieve connection metadata
    conns_a = get_user_ai_connections(user_a)
    conns_b = get_user_ai_connections(user_b)

    assert conns_a["openai"]["connected"] is True
    assert conns_b["openai"]["connected"] is True
    assert conns_a["openai"]["masked_key"] != conns_b["openai"]["masked_key"]

    # Verify decrypted key strictly matches user
    dec_a = get_decrypted_user_key(user_a, "openai")
    dec_b = get_decrypted_user_key(user_b, "openai")
    assert dec_a == key_a
    assert dec_b == key_b
    assert dec_a != dec_b

    # Deleting User A does NOT affect User B
    delete_user_ai_connection(user_a, "openai")
    assert get_decrypted_user_key(user_a, "openai") is None
    assert get_decrypted_user_key(user_b, "openai") == key_b

    # Clean up User B
    delete_user_ai_connection(user_b, "openai")
    assert get_decrypted_user_key(user_b, "openai") is None


def test_dual_provider_connection_and_preference():
    user_id = "usr_charlie_303"
    save_user_ai_connection(user_id, "openai", "sk-proj-charlie-openai-8888")
    save_user_ai_connection(user_id, "gemini", "AIzaSyCharlieGeminiKey9999")

    conns = get_user_ai_connections(user_id)
    assert conns["openai"]["connected"] is True
    assert conns["gemini"]["connected"] is True

    # Preferred provider toggle
    set_user_preferred_provider(user_id, "gemini")
    conns_after = get_user_ai_connections(user_id)
    assert conns_after["preferred_provider"] == "gemini"

    # Cleanup
    delete_user_ai_connection(user_id, "openai")
    delete_user_ai_connection(user_id, "gemini")


def test_sanitized_connection_testing():
    user_id = "usr_tester_404"
    # Testing non-existent connection returns not_connected
    res = verify_ai_connection(user_id, "openai")
    assert res["status"] in ("not_connected", "invalid", "unavailable")

    # Testing with bogus key returns invalid or unavailable without throwing
    res2 = verify_ai_connection(user_id, "openai", raw_api_key="sk-invalid-bogus-key-12345")
    assert res2["status"] in ("invalid", "unavailable", "rate_limited")
    assert "error" not in res2 or isinstance(res2.get("message"), str)


def test_ai_coaching_graceful_not_connected_fallback():
    user_id = "usr_unconnected_505"
    scenario = {
        "title": "Weekend Highlights",
        "prompt": "Share a 30s update with a colleague.",
        "mode": "casual"
    }
    metrics = {
        "clarity": 88,
        "filler_control": 92,
        "confidence": 85,
        "overall_score": 88
    }

    res = generate_ai_coaching(
        user_id=user_id,
        transcript="I had a productive weekend working on our core project deliverables.",
        scenario_data=scenario,
        communication_metrics=metrics
    )

    assert res["status"] == "not_connected"
    assert "coaching" in res
    assert len(res["coaching"]["strengths"]) >= 2
    assert len(res["coaching"]["improvements"]) >= 1
    assert "why_it_matters" in res["coaching"]
    assert "next_time_actions" in res["coaching"]
    assert "stronger_phrasing" in res["coaching"]


def test_interview_drill_star_breakdown():
    scenario = {
        "title": "Tell Me About a Time You Disagreed With a Decision",
        "prompt": "Describe a professional disagreement and the resolution.",
        "mode": "interview"
    }
    metrics = {
        "clarity": 84,
        "filler_control": 78,
        "confidence": 82,
        "overall_score": 83
    }

    coaching = generate_deterministic_fallback_coaching(
        transcript="In my previous team we faced an aggressive delivery schedule...",
        scenario_data=scenario,
        communication_metrics=metrics
    )

    assert coaching["interview_star"] is not None
    star = coaching["interview_star"]
    assert "situation" in star
    assert "task" in star
    assert "action" in star
    assert "result" in star
    assert "likely_followup" in star


def test_presentation_drill_structure_critique():
    scenario = {
        "title": "Q3 Capex Justification",
        "prompt": "Present the rationale for technology investment.",
        "mode": "presentation"
    }
    metrics = {
        "clarity": 90,
        "filler_control": 88,
        "confidence": 92,
        "overall_score": 90
    }

    coaching = generate_deterministic_fallback_coaching(
        transcript="Good morning leadership team. Today I present our Q3 capital allocation proposal...",
        scenario_data=scenario,
        communication_metrics=metrics
    )

    assert coaching["presentation_structure"] is not None
    pres = coaching["presentation_structure"]
    assert "opening" in pres
    assert "organization" in pres
    assert "transitions" in pres
    assert "conclusion" in pres


def test_authoritative_score_preservation():
    """Verify that ConversX core communication score is NEVER modified by AI coaching."""
    original_score = 87
    metrics = {
        "clarity": 85,
        "grammar": 90,
        "vocabulary": 80,
        "confidence": 85,
        "professionalism": 90,
        "respectfulness": 95,
        "filler_control": 80,
        "structure": 85,
        "overall_score": original_score
    }
    scenario = {"title": "Drill", "mode": "casual"}

    coaching = generate_deterministic_fallback_coaching(
        transcript="I had an interesting conversation today.",
        scenario_data=scenario,
        communication_metrics=metrics
    )

    # Coaching provides feedback without touching or modifying the original score
    assert metrics["overall_score"] == 87
    assert "score" not in coaching or coaching.get("score") is None
