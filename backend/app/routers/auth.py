"""
ConversX User & Admin Authentication Router.
Phase 7 Production Hardening.

Provides endpoints for:
- User registration: POST /api/v1/auth/register
- User/Admin login: POST /api/v1/auth/login
- Current user session check: GET /api/v1/auth/me
- Token verification: POST /api/v1/auth/verify
"""
from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, Optional

try:
    from fastapi import APIRouter, Depends, HTTPException, status
    from pydantic import BaseModel, EmailStr, Field

    from app.core.auth import (
        ROLE_ADMIN,
        ROLE_USER,
        UserSession,
        _IN_MEMORY_USERS,
        create_access_token,
        decode_access_token,
        get_current_user,
        hash_password,
        verify_password,
    )

    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

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

    class UserProfileResponse(BaseModel):
        user_id: str
        username: str
        email: Optional[str] = None
        role: str
        is_admin: bool

    @router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
    async def register(payload: RegisterRequest) -> TokenResponse:
        # Check existing username in memory or DB
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
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        _IN_MEMORY_USERS[user_id] = user_record

        token = create_access_token(user_id=user_id, role=ROLE_USER, username=payload.username)
        return TokenResponse(
            access_token=token,
            user_id=user_id,
            username=payload.username,
            role=ROLE_USER,
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
        )
        return TokenResponse(
            access_token=token,
            user_id=target_user["user_id"],
            username=target_user["username"],
            role=target_user["role"],
        )

    @router.get("/me", response_model=UserProfileResponse)
    async def get_my_profile(current_user: UserSession = Depends(get_current_user)) -> UserProfileResponse:
        return UserProfileResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            email=current_user.email,
            role=current_user.role,
            is_admin=current_user.is_admin,
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
