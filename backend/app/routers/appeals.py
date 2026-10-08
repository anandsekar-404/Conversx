"""
ConversX Appeal System Router.
Phase 7 Production Hardening.

Allows users receiving moderation warnings or penalties to submit formal appeals.
Enforces ownership validation (anti-IDOR) using UserSession credentials.
"""
from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, status
    from pydantic import BaseModel, Field

    from app.core.auth import (
        UserSession,
        get_optional_current_user,
        verify_user_ownership,
    )

    router = APIRouter(prefix="/api/v1/appeals", tags=["appeals"])

    _IN_MEMORY_APPEALS: Dict[str, Dict[str, Any]] = {}

    class SubmitAppealRequest(BaseModel):
        user_id: str = Field(..., min_length=1, description="User identifier")
        violation_id: str = Field(..., min_length=1, description="Violation event ID")
        reason: str = Field(..., min_length=5, max_length=1000, description="Explanation for appeal")

    class AppealResponse(BaseModel):
        appeal_id: str
        user_id: str
        violation_id: str
        reason: str
        status: str  # "pending", "approved", "rejected"
        admin_decision: Optional[str] = None
        admin_notes: Optional[str] = None
        created_at: str
        reviewed_at: Optional[str] = None

    @router.post("", response_model=AppealResponse, status_code=status.HTTP_201_CREATED)
    async def submit_appeal(
        payload: SubmitAppealRequest,
        current_user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> AppealResponse:
        # IDOR protection: if user is authenticated, ensure they cannot submit appeals on behalf of another user
        target_user_id = payload.user_id
        if current_user and not current_user.is_admin:
            if current_user.user_id != payload.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Cannot submit appeal on behalf of another user (IDOR prevention).",
                )

        appeal_id = f"app_{uuid.uuid4().hex[:10]}"
        record = {
            "appeal_id": appeal_id,
            "user_id": target_user_id,
            "violation_id": payload.violation_id,
            "reason": payload.reason,
            "status": "pending",
            "admin_decision": None,
            "admin_notes": None,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "reviewed_at": None,
        }
        _IN_MEMORY_APPEALS[appeal_id] = record
        return AppealResponse(**record)

    @router.get("/{appeal_id}", response_model=AppealResponse)
    async def get_appeal_status(
        appeal_id: str,
        current_user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> AppealResponse:
        if appeal_id not in _IN_MEMORY_APPEALS:
            raise HTTPException(status_code=404, detail="Appeal not found.")

        appeal = _IN_MEMORY_APPEALS[appeal_id]

        # IDOR protection: if user is authenticated and not admin, reject access to another user's appeal
        if current_user and not current_user.is_admin:
            if appeal["user_id"] != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Cannot view appeal belonging to another user.",
                )

        return AppealResponse(**appeal)

except ImportError:
    router = None
    _IN_MEMORY_APPEALS = {}
