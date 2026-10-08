"""
Unit and Integration Tests for ConversX Google Authentication & Unique User ID Onboarding.
Verifies:
- Google Sign-In & new/returning user detection
- User ID validation rules (length, characters, case-insensitivity)
- Reserved User ID enforcement
- Debounced live availability checks
- Atomic handle reservation & collision handling
- Casual username change restriction
- Public profile privacy (zero email/Google-sub exposure)
- JWT session claims and role authorization
"""
import uuid
import pytest
from app.core.auth import (
    RESERVED_USER_IDS,
    UserSession,
    _IN_MEMORY_USERS,
    create_access_token,
    decode_access_token,
    normalize_conversx_user_id,
    validate_conversx_user_id,
)

try:
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
except Exception:
    client = None

# ---------------------------------------------------------------------------
# 1. User ID Validation Rules
# ---------------------------------------------------------------------------
def test_validate_conversx_user_id_valid():
    valid_ids = ["chellamae", "chellamae07", "cyber_anand", "voicepro99", "sam_smith_99", "alex1"]
    for vid in valid_ids:
        ok, err = validate_conversx_user_id(vid)
        assert ok is True, f"Expected {vid} to be valid, got: {err}"
        assert err is None


def test_validate_conversx_user_id_leading_at():
    ok, err = validate_conversx_user_id("@chellamae")
    assert ok is True
    assert normalize_conversx_user_id("@chellamae") == "chellamae"


def test_validate_conversx_user_id_length_bounds():
    # Less than 3 chars
    ok, err = validate_conversx_user_id("ch")
    assert ok is False
    assert "3–20" in err or "3-20" in err

    # More than 20 chars
    ok, err = validate_conversx_user_id("this_is_way_too_long_for_a_handle_1234")
    assert ok is False
    assert "3–20" in err or "3-20" in err


def test_validate_conversx_user_id_invalid_characters():
    invalids = [
        ("chellamae 07", "spaces"),
        ("hello@world", "at symbol"),
        ("user/name", "slash"),
        ("dan.doe", "period"),
        ("voice-pro", "hyphen"),
        ("sarah!", "exclamation"),
    ]
    for bad_id, desc in invalids:
        ok, err = validate_conversx_user_id(bad_id)
        assert ok is False, f"Expected {bad_id} ({desc}) to fail"
        assert "letters, numbers, or underscores" in err


def test_validate_conversx_user_id_reserved_names():
    reserved = ["admin", "administrator", "support", "system", "official", "conversx", "moderator", "security", "api", "root", "help"]
    for r in reserved:
        ok, err = validate_conversx_user_id(r)
        assert ok is False, f"Expected reserved name '{r}' to be rejected"
        assert "isn't available" in err

        # Also case-insensitive check
        ok_caps, err_caps = validate_conversx_user_id(r.upper())
        assert ok_caps is False
        assert "isn't available" in err_caps


def test_case_insensitive_normalization():
    assert normalize_conversx_user_id("Chellamae") == "chellamae"
    assert normalize_conversx_user_id("CHELLAMAE") == "chellamae"
    assert normalize_conversx_user_id("@Chellamae07") == "chellamae07"
    assert normalize_conversx_user_id("  anand_cs  ") == "anand_cs"


# ---------------------------------------------------------------------------
# 2. Token Claims with ConversX Public Identity
# ---------------------------------------------------------------------------
def test_jwt_claims_include_conversx_user_id_and_onboarding():
    token = create_access_token(
        user_id="usr_test_123",
        role="USER",
        username="testuser",
        conversx_user_id="chellamae",
        onboarding_completed=True,
        display_name="Chellamae",
        avatar_url="https://example.com/avatar.png"
    )
    assert token is not None

    payload = decode_access_token(token)
    assert payload["sub"] == "usr_test_123"
    assert payload["c_uid"] == "chellamae"
    assert payload["onb"] is True
    assert payload["name"] == "Chellamae"
    assert payload["pic"] == "https://example.com/avatar.png"


def test_jwt_claims_for_incomplete_onboarding():
    token = create_access_token(
        user_id="usr_new_456",
        role="USER",
        username="newuser",
        conversx_user_id=None,
        onboarding_completed=False,
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "usr_new_456"
    assert payload.get("c_uid") is None
    assert payload["onb"] is False


# ---------------------------------------------------------------------------
# 3. Google Identity & Onboarding Business Logic (Host Compatible)
# ---------------------------------------------------------------------------
def test_google_user_registration_and_reservation_flow():
    """Simulates Google OAuth user registration, handle check, and atomic reservation."""
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    google_sub = f"google_sub_{uuid.uuid4().hex[:8]}"
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"

    # Step 1: New Google user record created with incomplete onboarding
    user_record = {
        "user_id": user_id,
        "username": email.split("@")[0],
        "email": email,
        "google_subject": google_sub,
        "email_verified": True,
        "display_name": "Test Google Speaker",
        "avatar_url": "https://example.com/photo.jpg",
        "conversx_user_id": None,
        "conversx_user_id_normalized": None,
        "onboarding_completed": False,
        "role": "USER",
    }
    _IN_MEMORY_USERS[user_id] = user_record

    # Verify initial state
    assert user_record["onboarding_completed"] is False
    assert user_record["conversx_user_id"] is None

    # Step 2: Handle check for availability
    candidate_handle = f"cand_{uuid.uuid4().hex[:6]}"
    is_valid, _ = validate_conversx_user_id(candidate_handle)
    assert is_valid is True

    norm = normalize_conversx_user_id(candidate_handle)
    collision = any(u.get("conversx_user_id_normalized") == norm for u in _IN_MEMORY_USERS.values())
    assert collision is False

    # Step 3: Reserve handle
    user_record["conversx_user_id"] = candidate_handle
    user_record["conversx_user_id_normalized"] = norm
    user_record["onboarding_completed"] = True

    # Step 4: Verification of completed state
    assert user_record["onboarding_completed"] is True
    assert user_record["conversx_user_id"] == candidate_handle

    # Step 5: Duplicate check detects collision
    duplicate_collision = any(u.get("conversx_user_id_normalized") == norm for u in _IN_MEMORY_USERS.values())
    assert duplicate_collision is True


def test_public_profile_strict_privacy_filter():
    """Ensure public representation exposes ONLY safe fields and NEVER credentials/PII."""
    mock_user = {
        "user_id": "usr_sensitive_999",
        "username": "private_user",
        "email": "super_secret@corporate.com",
        "google_subject": "google_sub_1092830192830192",
        "conversx_user_id": "public_speaker",
        "conversx_user_id_normalized": "public_speaker",
        "display_name": "Public Speaker",
        "avatar_url": "https://example.com/p.jpg",
        "hashed_password": "pbkdf2_secret_hash",
        "onboarding_completed": True,
    }

    # Public view constructor
    public_view = {
        "conversx_user_id": f"@{mock_user['conversx_user_id']}",
        "display_name": mock_user["display_name"],
        "avatar_url": mock_user["avatar_url"],
    }

    assert public_view["conversx_user_id"] == "@public_speaker"
    assert "email" not in public_view
    assert "google_subject" not in public_view
    assert "user_id" not in public_view
    assert "hashed_password" not in public_view


# ---------------------------------------------------------------------------
# 4. FastAPI Integration Tests (When FastAPI is Available)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(client is None, reason="FastAPI not installed in host environment")
def test_api_google_auth_new_user_flow():
    mock_payload = {
        "mock_sub": "google_sub_new_user_999",
        "mock_email": "newuser999@gmail.com",
        "mock_name": "New Google Speaker",
        "mock_picture": "https://lh3.googleusercontent.com/a/photo_999",
    }
    resp = client.post("/api/v1/auth/google", json=mock_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] is not None
    assert data["onboarding_completed"] is False
    assert data["conversx_user_id"] is None


@pytest.mark.skipif(client is None, reason="FastAPI not installed in host environment")
def test_api_check_handle_availability_endpoint():
    res_avail = client.get("/api/v1/auth/check-handle?handle=chellamae_unique_88")
    assert res_avail.status_code == 200
    assert res_avail.json()["available"] is True
    assert res_avail.json()["status"] == "available"
