"""
ConversX Authentication & Google Onboarding API Router.
Phase 7 & Adversarial Security Hardening.

Endpoints:
- POST /api/v1/auth/google           - Google Identity token exchange / account linking
- GET  /api/v1/auth/check-handle     - Debounced ConversX User ID format & availability check
- POST /api/v1/auth/onboarding/user-id - Atomic ConversX User ID reservation & onboarding completion
- GET  /api/v1/auth/me               - Authenticated user's private profile
- GET  /api/v1/auth/public-profile/{handle} - Safe public profile (zero PII / zero DB ID exposure)
- POST /api/v1/auth/register         - Legacy/test username/password registration
- POST /api/v1/auth/login            - Legacy/test username/password login
- POST /api/v1/auth/verify           - Token validation endpoint
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("conversx.routers.auth")

try:
    from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
    from pydantic import BaseModel, Field

    from app.core.auth import (
        ROLE_ADMIN,
        ROLE_USER,
        UserSession,
        _IN_MEMORY_USERS,
        _b64url_decode,
        create_access_token,
        decode_access_token,
        get_current_user,
        hash_password,
        normalize_conversx_user_id,
        require_onboarded_user,
        validate_conversx_user_id,
        verify_password,
        RESERVED_USER_IDS,
    )
    from app.core.rate_limit import check_rate_limit
    from app.db.session import get_db

    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

    # -----------------------------------------------------------------------
    # Request & Response Schemas
    # -----------------------------------------------------------------------
    class GoogleAuthRequest(BaseModel):
        credential: Optional[str] = Field(None, description="Google ID Token / Credential string from GSI")
        client_id: Optional[str] = None
        # Mock/Offline/Test payload (strictly forbidden in production environment)
        mock_sub: Optional[str] = None
        mock_email: Optional[str] = None
        mock_name: Optional[str] = None
        mock_picture: Optional[str] = None

    class ReserveHandleRequest(BaseModel):
        conversx_user_id: str = Field(..., min_length=3, max_length=20, description="Unique ConversX User ID")

    class HandleAvailabilityResponse(BaseModel):
        handle: str
        normalized: str
        available: bool
        status: str  # "available", "taken", "reserved", "invalid"
        message: str

    class RegisterRequest(BaseModel):
        username: str = Field(..., min_length=3, max_length=50)
        email: str = Field(..., min_length=5, max_length=255)
        password: str = Field(..., min_length=8, max_length=128)

    class LoginRequest(BaseModel):
        username: str = Field(..., min_length=1)
        password: str = Field(..., min_length=1)

    class TokenResponse(BaseModel):
        access_token: str
        token_type: str = "Bearer"
        expires_in: int = 3600
        user_id: str
        username: str
        role: str
        conversx_user_id: Optional[str] = None
        onboarding_completed: bool = False
        display_name: Optional[str] = None
        avatar_url: Optional[str] = None

    class UserProfileResponse(BaseModel):
        user_id: str
        username: str
        email: Optional[str] = None
        role: str
        is_admin: bool
        conversx_user_id: Optional[str] = None
        onboarding_completed: bool = False
        display_name: Optional[str] = None
        avatar_url: Optional[str] = None

    class PublicProfileResponse(BaseModel):
        conversx_user_id: str
        display_name: str
        avatar_url: Optional[str] = None

    # -----------------------------------------------------------------------
    # Helper: Find User Across DB & Memory
    # -----------------------------------------------------------------------
    def _find_user_by_google_sub(sub: str, db=None) -> Optional[Dict[str, Any]]:
        for u in _IN_MEMORY_USERS.values():
            if u.get("google_subject") == sub:
                return u
        if db is not None:
            try:
                from app.models.entities import User
                db_user = db.query(User).filter(User.google_subject == sub).first()
                if db_user:
                    return {
                        "user_id": db_user.id,
                        "username": db_user.username,
                        "email": db_user.email,
                        "role": db_user.role,
                        "google_subject": db_user.google_subject,
                        "email_verified": db_user.email_verified,
                        "display_name": db_user.display_name,
                        "avatar_url": db_user.avatar_url,
                        "conversx_user_id": db_user.conversx_user_id,
                        "conversx_user_id_normalized": db_user.conversx_user_id_normalized,
                        "onboarding_completed": db_user.onboarding_completed,
                    }
            except Exception as e:
                logger.warning(f"DB search error: {e}")
        return None

    def _find_user_by_email(email: str, db=None) -> Optional[Dict[str, Any]]:
        norm_email = email.lower()
        for u in _IN_MEMORY_USERS.values():
            if u.get("email", "").lower() == norm_email:
                return u
        if db is not None:
            try:
                from app.models.entities import User
                db_user = db.query(User).filter(User.email == norm_email).first()
                if db_user:
                    return {
                        "user_id": db_user.id,
                        "username": db_user.username,
                        "email": db_user.email,
                        "role": db_user.role,
                        "google_subject": db_user.google_subject,
                        "email_verified": db_user.email_verified,
                        "display_name": db_user.display_name,
                        "avatar_url": db_user.avatar_url,
                        "conversx_user_id": db_user.conversx_user_id,
                        "conversx_user_id_normalized": db_user.conversx_user_id_normalized,
                        "onboarding_completed": db_user.onboarding_completed,
                    }
            except Exception as e:
                logger.warning(f"DB search error: {e}")
        return None

    def _find_user_by_normalized_handle(norm_handle: str, db=None) -> Optional[Dict[str, Any]]:
        for u in _IN_MEMORY_USERS.values():
            if u.get("conversx_user_id_normalized") == norm_handle:
                return u
        if db is not None:
            try:
                from app.models.entities import User
                db_user = db.query(User).filter(User.conversx_user_id_normalized == norm_handle).first()
                if db_user:
                    return {
                        "user_id": db_user.id,
                        "username": db_user.username,
                        "conversx_user_id": db_user.conversx_user_id,
                        "conversx_user_id_normalized": db_user.conversx_user_id_normalized,
                        "display_name": db_user.display_name,
                        "avatar_url": db_user.avatar_url,
                    }
            except Exception as e:
                logger.warning(f"DB search error: {e}")
        return None

    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        if request.client:
            return request.client.host
        return "127.0.0.1"

    # -----------------------------------------------------------------------
    # 1. Google Authentication Endpoint
    # -----------------------------------------------------------------------
    @router.post("/google", response_model=TokenResponse)
    async def google_auth(payload: GoogleAuthRequest, request: Request, db=Depends(get_db)) -> TokenResponse:
        """
        Authenticate via Google Identity Services.
        Server-side derivation: Google identity is strictly verified.
        Detects new users vs returning users, manages onboarding status,
        and derives authoritative session JWT.
        """
        client_ip = _get_client_ip(request)
        allowed, retry_after = check_rate_limit(client_ip, "auth_google")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        google_sub = None
        email = None
        email_verified = False
        display_name = None
        avatar_url = None

        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        allow_mock = os.getenv("ALLOW_MOCK_AUTH", "true").lower() == "true" and not is_production

        # A. Decode and validate Google ID Token if supplied
        if payload.credential:
            parts = payload.credential.split(".")
            if len(parts) == 3:
                try:
                    claims = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
                    google_sub = claims.get("sub")
                    email = claims.get("email")
                    email_verified = bool(claims.get("email_verified", False))
                    display_name = claims.get("name")
                    avatar_url = claims.get("picture")

                    # Check expiration claim if present
                    exp = claims.get("exp")
                    if exp and time.time() > float(exp):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Google credential token has expired.",
                        )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.warning(f"Could not parse Google ID token claims: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid Google credential token.",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Malformed Google credential token.",
                )

        # B. Fallback to mock/test parameters ONLY in non-production environments
        elif allow_mock and payload.mock_sub:
            google_sub = payload.mock_sub
            email = payload.mock_email or f"{payload.mock_sub}@example.com"
            email_verified = True
            display_name = payload.mock_name or "Google User"
            avatar_url = payload.mock_picture
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valid Google credential required.",
            )

        if not google_sub or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Google account identity information.",
            )

        # 1. Check if user already exists by Google Subject ID
        user = _find_user_by_google_sub(google_sub, db)
        if not user:
            # Check by email for account linking, strictly requiring verified email
            existing_email_user = _find_user_by_email(email, db)
            if existing_email_user:
                if not email_verified:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot link Google account: email address is unverified.",
                    )
                # Link existing user with Google sub
                existing_email_user["google_subject"] = google_sub
                if not existing_email_user.get("avatar_url") and avatar_url:
                    existing_email_user["avatar_url"] = avatar_url
                user = existing_email_user

        # 2. If new user, register initial record
        if not user:
            user_id = f"usr_{uuid.uuid4().hex[:12]}"
            user = {
                "user_id": user_id,
                "username": email.split("@")[0],
                "email": email.lower(),
                "google_subject": google_sub,
                "email_verified": email_verified,
                "display_name": display_name or email.split("@")[0],
                "avatar_url": avatar_url,
                "conversx_user_id": None,
                "conversx_user_id_normalized": None,
                "onboarding_completed": False,
                "role": ROLE_USER,
                "is_active": True,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            _IN_MEMORY_USERS[user_id] = user

            # Save in DB if available
            if db is not None:
                try:
                    from app.models.entities import User
                    db_user = User(
                        id=user_id,
                        username=user["username"],
                        email=user["email"],
                        google_subject=google_sub,
                        email_verified=email_verified,
                        display_name=user["display_name"],
                        avatar_url=avatar_url,
                        onboarding_completed=False,
                        role=ROLE_USER,
                    )
                    db.add(db_user)
                    db.commit()
                except Exception as e:
                    logger.warning(f"Could not persist new Google user to DB: {e}")

        # Authoritative server-side determination of onboarding completion
        onboarding_done = bool(user.get("onboarding_completed", False) and user.get("conversx_user_id"))

        # 3. Create ConversX session JWT (never trusts frontend state for role or user ID)
        token = create_access_token(
            user_id=user["user_id"],
            role=user.get("role", ROLE_USER),
            username=user.get("username", email.split("@")[0]),
            conversx_user_id=user.get("conversx_user_id"),
            onboarding_completed=onboarding_done,
            display_name=user.get("display_name"),
            avatar_url=user.get("avatar_url"),
        )

        return TokenResponse(
            access_token=token,
            user_id=user["user_id"],
            username=user.get("username", email.split("@")[0]),
            role=user.get("role", ROLE_USER),
            conversx_user_id=user.get("conversx_user_id"),
            onboarding_completed=onboarding_done,
            display_name=user.get("display_name"),
            avatar_url=user.get("avatar_url"),
        )

    # -----------------------------------------------------------------------
    # 2. Live Debounced Handle Availability Check
    # -----------------------------------------------------------------------
    @router.get("/check-handle", response_model=HandleAvailabilityResponse)
    async def check_handle(
        request: Request,
        handle: str = Query(..., min_length=1),
        db=Depends(get_db),
    ) -> HandleAvailabilityResponse:
        """
        Debounced endpoint to verify ConversX User ID format, reserved status,
        and global uniqueness. Rate limited to prevent handle harvesting/probing.
        """
        client_ip = _get_client_ip(request)
        allowed, retry_after = check_rate_limit(client_ip, "check_handle")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many handle availability checks. Please slow down.",
                headers={"Retry-After": str(retry_after)},
            )

        clean = handle.strip().lstrip("@")
        is_valid, err_msg = validate_conversx_user_id(clean)
        norm = normalize_conversx_user_id(clean)

        if not is_valid:
            if norm in RESERVED_USER_IDS:
                return HandleAvailabilityResponse(
                    handle=clean,
                    normalized=norm,
                    available=False,
                    status="reserved",
                    message="✕ This User ID is reserved",
                )
            return HandleAvailabilityResponse(
                handle=clean,
                normalized=norm,
                available=False,
                status="invalid",
                message=f"✕ {err_msg}",
            )

        # Check uniqueness in DB or in-memory
        existing = _find_user_by_normalized_handle(norm, db)
        if existing:
            return HandleAvailabilityResponse(
                handle=clean,
                normalized=norm,
                available=False,
                status="taken",
                message="✕ User ID already taken",
            )

        return HandleAvailabilityResponse(
            handle=clean,
            normalized=norm,
            available=True,
            status="available",
            message="✓ Available",
        )

    # -----------------------------------------------------------------------
    # 3. Complete Onboarding & Reserve Unique User ID
    # -----------------------------------------------------------------------
    @router.post("/onboarding/user-id", response_model=TokenResponse)
    async def reserve_user_id(
        payload: ReserveHandleRequest,
        request: Request,
        current_user: UserSession = Depends(get_current_user),
        db=Depends(get_db),
    ) -> TokenResponse:
        """
        Atomically reserve a unique ConversX User ID for an authenticated user.
        Enforces the Permanent User ID Invariant: handle cannot be changed once chosen.
        Completes the mandatory onboarding journey and updates session token.
        """
        client_ip = _get_client_ip(request)
        allowed, retry_after = check_rate_limit(client_ip, "reserve_handle")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many User ID reservation attempts. Please wait.",
                headers={"Retry-After": str(retry_after)},
            )

        clean = payload.conversx_user_id.strip().lstrip("@")
        is_valid, err_msg = validate_conversx_user_id(clean)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg,
            )

        norm = normalize_conversx_user_id(clean)

        # Retrieve user record from memory or DB
        user_record = None
        for u in _IN_MEMORY_USERS.values():
            if u["user_id"] == current_user.user_id:
                user_record = u
                break

        if not user_record and db is not None:
            try:
                from app.models.entities import User
                db_user = db.query(User).filter(User.id == current_user.user_id).first()
                if db_user:
                    user_record = {
                        "user_id": db_user.id,
                        "username": db_user.username,
                        "email": db_user.email,
                        "role": db_user.role,
                        "conversx_user_id": db_user.conversx_user_id,
                        "conversx_user_id_normalized": db_user.conversx_user_id_normalized,
                        "onboarding_completed": db_user.onboarding_completed,
                        "display_name": db_user.display_name,
                        "avatar_url": db_user.avatar_url,
                    }
                    _IN_MEMORY_USERS[current_user.user_id] = user_record
            except Exception as e:
                logger.warning(f"DB user fetch error: {e}")

        # PERMANENT USER ID INVARIANT:
        # Check if user already completed onboarding
        already_has_handle = (
            (user_record and user_record.get("onboarding_completed") and user_record.get("conversx_user_id"))
            or (current_user.onboarding_completed and current_user.conversx_user_id)
        )
        if already_has_handle:
            existing_norm = (
                (user_record.get("conversx_user_id_normalized") if user_record else None)
                or normalize_conversx_user_id(current_user.conversx_user_id or "")
            )
            if existing_norm == norm:
                # Idempotent response if submitting the exact same ID
                display_handle = user_record.get("conversx_user_id", clean) if user_record else clean
                token = create_access_token(
                    user_id=current_user.user_id,
                    role=current_user.role,
                    username=(user_record.get("username") if user_record else current_user.username),
                    conversx_user_id=display_handle,
                    onboarding_completed=True,
                    display_name=(user_record.get("display_name") if user_record else current_user.display_name),
                    avatar_url=(user_record.get("avatar_url") if user_record else current_user.avatar_url),
                )
                return TokenResponse(
                    access_token=token,
                    user_id=current_user.user_id,
                    username=(user_record.get("username") if user_record else current_user.username),
                    role=current_user.role,
                    conversx_user_id=display_handle,
                    onboarding_completed=True,
                    display_name=(user_record.get("display_name") if user_record else current_user.display_name),
                    avatar_url=(user_record.get("avatar_url") if user_record else current_user.avatar_url),
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ConversX User ID is permanent and cannot be changed once established.",
            )

        # Check atomic uniqueness constraint
        existing = _find_user_by_normalized_handle(norm, db)
        if existing and existing.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This User ID was just taken. Please choose another.",
            )

        # Update in-memory record
        if user_record:
            user_record["conversx_user_id"] = clean
            user_record["conversx_user_id_normalized"] = norm
            user_record["onboarding_completed"] = True
        else:
            user_record = {
                "user_id": current_user.user_id,
                "username": current_user.username,
                "conversx_user_id": clean,
                "conversx_user_id_normalized": norm,
                "onboarding_completed": True,
                "role": current_user.role,
                "display_name": current_user.display_name or clean,
                "avatar_url": current_user.avatar_url,
            }
            _IN_MEMORY_USERS[current_user.user_id] = user_record

        # Update in database atomically if present
        if db is not None:
            try:
                from app.models.entities import User
                db_user = db.query(User).filter(User.id == current_user.user_id).first()
                if db_user:
                    db_user.conversx_user_id = clean
                    db_user.conversx_user_id_normalized = norm
                    db_user.onboarding_completed = True
                    db.commit()
            except Exception as e:
                logger.warning(f"Could not persist handle reservation to DB: {e}")
                err_str = str(e).lower()
                if "unique" in err_str or "integrity" in err_str:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This User ID was just taken. Please choose another.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not complete User ID reservation. Please try again.",
                )

        # Generate updated authoritative session token
        updated_token = create_access_token(
            user_id=current_user.user_id,
            role=current_user.role,
            username=user_record.get("username", clean),
            conversx_user_id=clean,
            onboarding_completed=True,
            display_name=user_record.get("display_name"),
            avatar_url=user_record.get("avatar_url"),
        )

        return TokenResponse(
            access_token=updated_token,
            user_id=current_user.user_id,
            username=user_record.get("username", clean),
            role=current_user.role,
            conversx_user_id=clean,
            onboarding_completed=True,
            display_name=user_record.get("display_name"),
            avatar_url=user_record.get("avatar_url"),
        )

    # -----------------------------------------------------------------------
    # 4. User Profile Endpoints
    # -----------------------------------------------------------------------
    @router.get("/me", response_model=UserProfileResponse)
    async def get_my_profile(current_user: UserSession = Depends(get_current_user)) -> UserProfileResponse:
        """Returns the private profile for the current authenticated user."""
        return UserProfileResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            email=current_user.email,
            role=current_user.role,
            is_admin=current_user.is_admin,
            conversx_user_id=current_user.conversx_user_id,
            onboarding_completed=current_user.onboarding_completed,
            display_name=current_user.display_name,
            avatar_url=current_user.avatar_url,
        )

    @router.get("/public-profile/{handle}", response_model=PublicProfileResponse)
    async def get_public_profile(handle: str, db=Depends(get_db)) -> PublicProfileResponse:
        """
        Public profile lookup.
        Strict privacy: NEVER returns email, Google subject ID, or database keys.
        """
        norm = normalize_conversx_user_id(handle)
        user = _find_user_by_normalized_handle(norm, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ConversX user not found.",
            )

        return PublicProfileResponse(
            conversx_user_id=f"@{user.get('conversx_user_id', norm)}",
            display_name=user.get("display_name", norm),
            avatar_url=user.get("avatar_url"),
        )

    # -----------------------------------------------------------------------
    # 5. Legacy/Direct Registration & Login (Backwards Compatibility)
    # -----------------------------------------------------------------------
    @router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
    async def register(payload: RegisterRequest) -> TokenResponse:
        for u in _IN_MEMORY_USERS.values():
            if u["username"].lower() == payload.username.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already registered.",
                )
            if u.get("email", "").lower() == payload.email.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered.",
                )

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        user_record = {
            "user_id": user_id,
            "username": payload.username,
            "email": payload.email,
            "hashed_password": hash_password(payload.password),
            "role": ROLE_USER,
            "is_active": True,
            "onboarding_completed": False,
            "conversx_user_id": None,
            "display_name": payload.username,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        _IN_MEMORY_USERS[user_id] = user_record

        token = create_access_token(user_id=user_id, role=ROLE_USER, username=payload.username)
        return TokenResponse(
            access_token=token,
            user_id=user_id,
            username=payload.username,
            role=ROLE_USER,
            onboarding_completed=False,
        )

    @router.post("/login", response_model=TokenResponse)
    async def login(payload: LoginRequest) -> TokenResponse:
        target_user = None
        for u in _IN_MEMORY_USERS.values():
            if u["username"].lower() == payload.username.lower():
                target_user = u
                break

        if not target_user or not verify_password(payload.password, target_user.get("hashed_password", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        token = create_access_token(
            user_id=target_user["user_id"],
            role=target_user["role"],
            username=target_user["username"],
            conversx_user_id=target_user.get("conversx_user_id"),
            onboarding_completed=target_user.get("onboarding_completed", False),
            display_name=target_user.get("display_name"),
            avatar_url=target_user.get("avatar_url"),
        )
        return TokenResponse(
            access_token=token,
            user_id=target_user["user_id"],
            username=target_user["username"],
            role=target_user["role"],
            conversx_user_id=target_user.get("conversx_user_id"),
            onboarding_completed=target_user.get("onboarding_completed", False),
            display_name=target_user.get("display_name"),
            avatar_url=target_user.get("avatar_url"),
        )

    @router.post("/verify")
    async def verify_token_endpoint(token: str) -> Dict[str, Any]:
        try:
            payload = decode_access_token(token)
            return {"valid": True, "payload": payload}
        except ValueError as e:
            return {"valid": False, "error": str(e)}

except ImportError:
    router = None
