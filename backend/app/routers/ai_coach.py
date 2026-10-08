"""
ConversX AI Coach API Router.
Phase 7 & Security Hardening Pass.

Endpoints:
- GET  /api/v1/ai-coach/status                 - List connection statuses & masked identifiers
- POST /api/v1/ai-coach/connect                - Save encrypted provider key
- POST /api/v1/ai-coach/test                   - Test connection (connected, invalid, rate_limited, unavailable)
- DELETE /api/v1/ai-coach/connection/{provider} - Remove credential
- POST /api/v1/ai-coach/preferred              - Set preferred provider
- POST /api/v1/ai-coach/coach                  - Generate personalized AI coaching
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("conversx.routers.ai_coach")

try:
    from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
    from pydantic import BaseModel, Field

    from app.core.auth import UserSession, get_optional_current_user
    from app.core.rate_limit import check_rate_limit
    from app.services.ai_coach import (
        delete_user_ai_connection,
        generate_ai_coaching,
        get_user_ai_connections,
        save_user_ai_connection,
        set_user_preferred_provider,
        verify_ai_connection,
    )

    router = APIRouter(prefix="/api/v1/ai-coach", tags=["ai_coach"])

    class ConnectRequest(BaseModel):
        provider: str = Field(..., description="Provider name: 'openai' or 'gemini'")
        api_key: str = Field(..., min_length=10, description="Raw API key from provider dashboard")

    class TestRequest(BaseModel):
        provider: str = Field(..., description="Provider name: 'openai' or 'gemini'")
        api_key: Optional[str] = Field(None, description="Optional raw key to test before saving")

    class PreferredRequest(BaseModel):
        provider: str = Field(..., description="'openai', 'gemini', or 'ask'")

    class CoachRequest(BaseModel):
        transcript: str = Field(..., min_length=1, description="Spoken voice transcript")
        scenario: Dict[str, Any] = Field(..., description="Scenario details (title, prompt, mode)")
        communication_metrics: Dict[str, Any] = Field(..., description="ConversX deterministic 8-dimension scores")
        speaking_metrics: Optional[Dict[str, Any]] = Field(None, description="Acoustic metrics (wpm, fillers, pauses)")
        provider: Optional[str] = Field(None, description="Explicit provider override")

    def _ensure_onboarding(user: Optional[UserSession]) -> None:
        """Enforces onboarding completion for authenticated users accessing AI coaching."""
        if user and not user.onboarding_completed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ConversX User ID onboarding required. Please complete onboarding first.",
                headers={"X-Onboarding-Required": "true"}
            )

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


    @router.get("/status")
    async def get_connection_status(
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """Return safe provider status metadata. Never returns full API keys."""
        _ensure_onboarding(user)
        user_id = user.user_id if user else "guest_user"
        return get_user_ai_connections(user_id=user_id)


    @router.post("/connect")
    async def connect_provider(
        req: ConnectRequest,
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """Save and encrypt API credentials at rest for the current user."""
        _ensure_onboarding(user)
        user_id = user.user_id if user else "guest_user"
        try:
            res = save_user_ai_connection(
                user_id=user_id,
                provider=req.provider,
                raw_api_key=req.api_key
            )
            return res
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"Error saving AI connection: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save provider connection.")


    @router.post("/test")
    async def test_provider(
        req: TestRequest,
        request: Request,
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """Test API connection. Rate limited to prevent key probing abuse."""
        _ensure_onboarding(user)
        client_ip = _get_client_ip(request)
        allowed, retry_after = check_rate_limit(client_ip, "ai_test")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many connection test requests. Please wait.",
                headers={"Retry-After": str(retry_after)}
            )

        user_id = user.user_id if user else "guest_user"
        return verify_ai_connection(
            user_id=user_id,
            provider=req.provider,
            raw_api_key=req.api_key
        )


    @router.delete("/connection/{provider}")
    async def remove_connection(
        provider: str,
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """Permanently delete stored provider credentials."""
        _ensure_onboarding(user)
        user_id = user.user_id if user else "guest_user"
        deleted = delete_user_ai_connection(user_id=user_id, provider=provider)
        return {
            "deleted": deleted,
            "provider": provider,
            "status": "not_connected",
            "message": f"{provider.capitalize()} connection removed successfully."
        }


    @router.post("/preferred")
    async def set_preferred(
        req: PreferredRequest,
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """Set user's preferred AI coach provider."""
        _ensure_onboarding(user)
        user_id = user.user_id if user else "guest_user"
        pref = set_user_preferred_provider(user_id=user_id, provider=req.provider)
        return {"preferred_provider": pref}


    @router.post("/coach")
    async def request_ai_coaching(
        req: CoachRequest,
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """
        Generate personalized AI coaching for spoken response.
        Enforces strict account isolation and preserves ConversX deterministic scoring.
        """
        _ensure_onboarding(user)
        user_id = user.user_id if user else "guest_user"
        try:
            coaching = generate_ai_coaching(
                user_id=user_id,
                spoken_transcript=req.transcript,
                scenario_details=req.scenario,
                communication_scores=req.communication_metrics,
                acoustic_metrics=req.speaking_metrics,
                explicit_provider=req.provider
            )
            return coaching
        except Exception as e:
            logger.error(f"Error generating AI coaching: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate AI coaching at this time."
            )

except ImportError:
    router = None
