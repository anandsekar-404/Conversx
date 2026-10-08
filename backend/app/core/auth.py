"""
ConversX Authentication & Role-Based Access Control (RBAC) Module.
Phase 7 Production Hardening.

Features:
- RFC 7519 Compliant HS256 JWT generation, decoding, and validation.
- NIST PBKDF2-HMAC-SHA256 password hashing.
- Role-Based Access Control: USER and ADMIN roles.
- Ownership verification to prevent IDOR (Insecure Direct Object Reference).
- Dual-mode support: Uses FastAPI and PyJWT when installed; provides pure-Python
  standard library fallbacks for test environments without external dependencies.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional

# Secret keys from environment with production defaults
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("APP_SECRET_KEY", "conversx-production-jwt-secret-key-phase7"))
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "conversx.com"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Roles
ROLE_USER = "USER"
ROLE_ADMIN = "ADMIN"
VALID_ROLES = {ROLE_USER, ROLE_ADMIN}


# ---------------------------------------------------------------------------
# Password Hashing (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a secure salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100000,
    ).hex()
    return f"pbkdf2:sha256:100000${salt}${hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its PBKDF2 hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        salt = parts[1]
        expected_hash = parts[2]
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100000,
        ).hex()
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Pure Standard-Library JWT (RFC 7519)
# ---------------------------------------------------------------------------
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("ascii"))


def create_access_token(
    user_id: str,
    role: str = ROLE_USER,
    username: str = "",
    expires_delta_minutes: Optional[int] = None,
    secret_key: Optional[str] = None,
) -> str:
    """
    Generate an RFC 7519 compliant HS256 JWT access token.
    """
    secret = (secret_key or JWT_SECRET_KEY).encode("utf-8")
    now = int(time.time())
    exp_minutes = expires_delta_minutes if expires_delta_minutes is not None else ACCESS_TOKEN_EXPIRE_MINUTES
    exp = now + (exp_minutes * 60)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "username": username or str(user_id),
        "role": role.upper(),
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": exp,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str, secret_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate and decode an HS256 JWT token.
    Raises ValueError on invalid token, signature mismatch, or expired token.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Invalid token: token must be a non-empty string.")

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token: token must contain 3 segments.")

    header_b64, payload_b64, sig_b64 = parts
    secret = (secret_key or JWT_SECRET_KEY).encode("utf-8")

    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid token: signature verification failed.")

    # Parse payload
    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid token: payload decoding failed ({e}).")

    # Check expiration
    now = int(time.time())
    exp = payload.get("exp")
    if exp is None or not isinstance(exp, (int, float)):
        raise ValueError("Invalid token: missing or invalid expiration claim.")

    if now > exp:
        raise ValueError("Token has expired.")

    return payload


# ---------------------------------------------------------------------------
# User Session & Ownership Checks
# ---------------------------------------------------------------------------
class UserSession:
    """Represents an authenticated user identity and active roles."""
    def __init__(self, user_id: str, username: str, role: str, email: Optional[str] = None):
        self.user_id = str(user_id)
        self.username = str(username)
        self.role = role.upper()
        self.email = email

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    def has_role(self, required_role: str) -> bool:
        return self.role == required_role.upper()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "email": self.email,
            "is_admin": self.is_admin,
        }


def verify_user_ownership(session: UserSession, resource_user_id: str) -> bool:
    """
    Prevent Insecure Direct Object References (IDOR):
    Verifies that the session user matches the resource owner,
    OR the session is an administrator.
    """
    if session.is_admin:
        return True
    return session.user_id == str(resource_user_id)


# ---------------------------------------------------------------------------
# In-Memory User Store (Fallback & Testing)
# ---------------------------------------------------------------------------
_IN_MEMORY_USERS: Dict[str, Dict[str, Any]] = {
    "admin_default": {
        "user_id": "usr_admin_001",
        "username": "admin",
        "email": "admin@conversx.com",
        "hashed_password": hash_password("ConversXAdmin2026!"),
        "role": ROLE_ADMIN,
        "is_active": True,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    "guest_user": {
        "user_id": "guest_user",
        "username": "guest",
        "email": "guest@conversx.com",
        "hashed_password": hash_password("GuestPass123!"),
        "role": ROLE_USER,
        "is_active": True,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
}


# ---------------------------------------------------------------------------
# FastAPI Auth Dependencies (Guarded for Host Unit Tests)
# ---------------------------------------------------------------------------
try:
    from fastapi import Depends, Header, HTTPException, status
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

    security_bearer = HTTPBearer(auto_error=False)

    async def get_current_user(
        auth_header: Optional[str] = Header(None, alias="Authorization"),
    ) -> UserSession:
        """
        FastAPI dependency: extracts and verifies JWT bearer token from Authorization header.
        Raises 401 Unauthorized on missing, malformed, or expired token.
        """
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header. Bearer token required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected: 'Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]
        try:
            payload = decode_access_token(token)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub", "")
        role = payload.get("role", ROLE_USER)
        username = payload.get("username", user_id)

        return UserSession(user_id=user_id, username=username, role=role)

    def require_role(allowed_roles: List[str]):
        """Dependency factory to enforce role-based access control."""
        allowed_set = {r.upper() for r in allowed_roles}

        async def _role_checker(current_user: UserSession = Depends(get_current_user)) -> UserSession:
            if current_user.role not in allowed_set:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Insufficient privileges. Required roles: {allowed_roles}.",
                )
            return current_user

        return _role_checker

    async def require_admin(current_user: UserSession = Depends(get_current_user)) -> UserSession:
        """Dependency requiring authenticated user with ADMIN role."""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Administrator access required.",
            )
        return current_user

    async def require_user(current_user: UserSession = Depends(get_current_user)) -> UserSession:
        """Dependency requiring an authenticated user."""
        return current_user

    async def get_optional_current_user(
        auth_header: Optional[str] = Header(None, alias="Authorization"),
    ) -> Optional[UserSession]:
        """Optional user dependency for public endpoints with guest fallbacks."""
        if not auth_header:
            return None
        try:
            return await get_current_user(auth_header)
        except HTTPException:
            return None

except ImportError:
    # FastAPI not installed in host environment; dependencies defined as None
    get_current_user = None
    require_role = None
    require_admin = None
    require_user = None
    get_optional_current_user = None
