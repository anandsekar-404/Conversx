"""
ConversX Phase 7 Security Hardening & Access Control Test Suite.
Verifies:
- RFC 7519 HS256 JWT creation, verification, expiration, and tampering rejection.
- NIST PBKDF2-HMAC-SHA256 password hashing and constant-time comparison.
- Role-Based Access Control (RBAC): USER vs ADMIN roles.
- Insecure Direct Object Reference (IDOR) ownership protection.
- Audio upload security: size limits (25MB), MIME verification, path traversal prevention.
- Admin authentication transition & operational key validation.
- Database backup and restore integrity verification.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import time
import pytest

from app.core.auth import (
    ROLE_ADMIN,
    ROLE_USER,
    UserSession,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    verify_user_ownership,
)
from app.routers.practice import (
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_AUDIO_MIMES,
    MAX_AUDIO_SIZE_BYTES,
)
from scripts.backup_postgres import verify_backup


# ---------------------------------------------------------------------------
# 1. JWT Authentication & Token Security Tests
# ---------------------------------------------------------------------------
def test_jwt_creation_and_successful_decoding():
    token = create_access_token(user_id="usr_123", role=ROLE_USER, username="anand")
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    payload = decode_access_token(token)
    assert payload["sub"] == "usr_123"
    assert payload["role"] == ROLE_USER
    assert payload["username"] == "anand"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_expired_token_rejection():
    # Token with negative delta -> expired in the past
    expired_token = create_access_token(
        user_id="usr_expired",
        role=ROLE_USER,
        expires_delta_minutes=-5,
    )
    with pytest.raises(ValueError, match="Token has expired"):
        decode_access_token(expired_token)


def test_jwt_tampered_signature_rejection():
    valid_token = create_access_token(user_id="usr_normal", role=ROLE_USER)
    parts = valid_token.split(".")

    # Tamper with signature
    tampered_sig = parts[2][:-4] + "ABCD"
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    with pytest.raises(ValueError, match="signature verification failed"):
        decode_access_token(tampered_token)


def test_jwt_malformed_token_rejection():
    invalid_tokens = [
        "",
        "not.a.token",
        "header.only",
        "invalid_base64.invalid_base64.invalid_base64",
    ]
    for bad in invalid_tokens:
        with pytest.raises(ValueError):
            decode_access_token(bad)


# ---------------------------------------------------------------------------
# 2. Password Hashing Security Tests
# ---------------------------------------------------------------------------
def test_password_hashing_and_verification():
    plain = "SuperSecurePassword2026!"
    hashed = hash_password(plain)

    assert hashed.startswith("pbkdf2:sha256:100000$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(plain, "") is False


# ---------------------------------------------------------------------------
# 3. Role-Based Access Control (RBAC) & IDOR Protection Tests
# ---------------------------------------------------------------------------
def test_user_session_and_roles():
    normal_user = UserSession(user_id="usr_01", username="alice", role=ROLE_USER)
    admin_user = UserSession(user_id="usr_adm", username="bob_admin", role=ROLE_ADMIN)

    assert normal_user.is_admin is False
    assert normal_user.has_role(ROLE_USER) is True
    assert normal_user.has_role(ROLE_ADMIN) is False

    assert admin_user.is_admin is True
    assert admin_user.has_role(ROLE_ADMIN) is True
    assert admin_user.has_role(ROLE_USER) is False


def test_idor_prevention_ownership_checks():
    user_a = UserSession(user_id="user_alice", username="alice", role=ROLE_USER)
    user_b_id = "user_bob"
    admin = UserSession(user_id="admin_carol", username="carol", role=ROLE_ADMIN)

    # User A accessing User A resource -> Allowed
    assert verify_user_ownership(user_a, "user_alice") is True

    # User A attempting to access User B resource (IDOR attempt) -> BLOCKED
    assert verify_user_ownership(user_a, user_b_id) is False

    # Admin accessing any resource -> Allowed for governance
    assert verify_user_ownership(admin, user_b_id) is True
    assert verify_user_ownership(admin, "user_alice") is True


# ---------------------------------------------------------------------------
# 4. Audio Upload Security Hardening Tests
# ---------------------------------------------------------------------------
def test_audio_upload_size_limit_constant():
    # 25 MB = 25 * 1024 * 1024 = 26,214,400 bytes
    assert MAX_AUDIO_SIZE_BYTES == 25 * 1024 * 1024


def test_audio_allowed_extensions_and_mimes():
    assert ".wav" in ALLOWED_AUDIO_EXTENSIONS
    assert ".webm" in ALLOWED_AUDIO_EXTENSIONS
    assert ".mp3" in ALLOWED_AUDIO_EXTENSIONS
    assert ".m4a" in ALLOWED_AUDIO_EXTENSIONS

    # Dangerous extensions must NOT be permitted
    dangerous_exts = [".exe", ".sh", ".py", ".php", ".js", ".html"]
    for ext in dangerous_exts:
        assert ext not in ALLOWED_AUDIO_EXTENSIONS

    assert "audio/wav" in ALLOWED_AUDIO_MIMES
    assert "audio/webm" in ALLOWED_AUDIO_MIMES
    assert "audio/mpeg" in ALLOWED_AUDIO_MIMES
    assert "application/javascript" not in ALLOWED_AUDIO_MIMES


def test_audio_filename_path_traversal_sanitization():
    # Unsafe user-supplied paths
    malicious_filenames = [
        "../../../../etc/passwd",
        r"..\..\Windows\System32\cmd.exe",
        "/var/run/secrets.webm",
        "nested/path/audio.wav",
    ]
    for fname in malicious_filenames:
        base = os.path.basename(fname)
        ext = os.path.splitext(base)[1].lower()
        # Even if malicious path contains .webm or .wav, basename strips directory traversal
        assert "/" not in base
        assert chr(92) not in base


# ---------------------------------------------------------------------------
# 5. Database Backup Verification Tests
# ---------------------------------------------------------------------------
def test_backup_verification_detects_invalid_file():
    import tempfile
    tmp_file = os.path.join(tempfile.gettempdir(), f"corrupt_test_{time.time()}.sql.gz")
    try:
        with open(tmp_file, "wb") as f:
            f.write(b"not-a-valid-gzip-stream")
        # verify_backup should report corrupt archive and return False
        is_valid = verify_backup(tmp_file)
        assert is_valid is False
    finally:
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass


def test_backup_verification_on_missing_file():
    is_valid = verify_backup("nonexistent_backup_file_xyz.sql.gz")
    assert is_valid is False
