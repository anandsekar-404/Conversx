"""
ConversX AI Coach API Router.
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
    from fastapi import APIRouter, Depends, HTTPException, Query, status
    from pydantic import BaseModel, Field

    from app.core.auth import UserSession, get_optional_current_user
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


    @router.get("/status")
    async def get_connection_status(
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """Return safe provider status metadata. Never returns full API keys."""
        user_id = user.user_id if user else "guest_user"
        return get_user_ai_connections(user_id=user_id)


    @router.post("/connect")
    async def connect_provider(
        req: ConnectRequest,
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """Save and encrypt API credentials at rest for the current user."""
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
        user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        """Test API connection. Returns sanitized states: connected, invalid, rate_limited, unavailable."""
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
        Core ConversX score is preserved and returned untouched.
        """
        user_id = user.user_id if user else "guest_user"
        coaching_result = generate_ai_coaching(
            user_id=user_id,
            transcript=req.transcript,
            scenario_data=req.scenario,
            communication_metrics=req.communication_metrics,
            speaking_metrics=req.speaking_metrics,
            preferred_provider=req.provider
        )
        return coaching_result

except ImportError:
    # Test environment fallback when FastAPI is not present
    router = None
