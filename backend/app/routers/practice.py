"""
ConversX - Practice & Communication Coaching API Router.
Provides endpoints for response analysis, scenarios retrieval, daily challenges,
session tracking, and progress metrics.
"""
from __future__ import annotations

import datetime
import os
import uuid
from typing import Any, Dict, List, Optional

# Audio upload security constants (Phase 7 Hardening)
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".webm", ".mp3", ".ogg", ".m4a", ".aac"}
ALLOWED_AUDIO_MIMES = {
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/webm", "video/webm",
    "audio/mpeg", "audio/mp3",
    "audio/ogg", "application/ogg",
    "audio/mp4", "audio/x-m4a", "audio/m4a",
    "audio/aac", "application/octet-stream"
}

_SESSION_HISTORY: List[Dict[str, Any]] = []

try:
    from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
    from pydantic import BaseModel, Field

    from app.core.auth import (
        UserSession,
        get_optional_current_user,
        verify_user_ownership,
    )
    from app.services.practice import analyze_practice_response
    from app.services.scenarios import (
        PRACTICE_MODES,
        get_all_scenarios,
        get_scenario_by_id,
        get_today_challenge,
    )

    router = APIRouter(prefix="/api/v1/practice", tags=["practice-coach"])
    progress_router = APIRouter(prefix="/api/v1/progress", tags=["progress"])

    class AnalyzeRequest(BaseModel):
        text: str = Field(..., min_length=1, description="User spoken or written response text")
        scenario_id: Optional[str] = Field(None, description="Scenario identifier being practiced")
        attempt_number: int = Field(1, ge=1, le=10, description="Attempt number for retry comparison")
        delivery_score: Optional[int] = Field(None, ge=0, le=100, description="Voice delivery score if voice practice")
        speaking_metrics: Optional[Dict[str, Any]] = Field(None, description="Voice metrics (wpm, fillers, pauses)")

    class SayItBetterSchema(BaseModel):
        original_text: str
        suggested_text: str
        improvements_made: List[str]
        coaching_summary: str

    class AnalyzeResponse(BaseModel):
        scenario_id: Optional[str]
        communication_score: int
        dimension_scores: Dict[str, int]
        delivery_score: Optional[int] = None
        positive_feedback: List[str]
        improvement_feedback: List[str]
        coaching_tip: str
        say_it_better: SayItBetterSchema
        attempt_number: int
        moderation_status: str
        disclaimer: str

    class RecordSessionRequest(BaseModel):
        scenario_id: str
        practice_type: str = "casual"
        attempt_number: int = 1
        score: int
        delivery_score: Optional[int] = None
        wpm: Optional[float] = None
        filler_rate: Optional[float] = None
        speaking_duration: Optional[float] = None
        is_voice: bool = False
        dimension_scores: Optional[Dict[str, int]] = None
        detected_issues_count: int = 0
        session_id: Optional[str] = None
        user_id: Optional[str] = "guest_user"

    class VoiceAnalyzeRequest(BaseModel):
        transcript: str = Field(..., min_length=1, description="Transcribed speech from Web Speech API or Whisper")
        duration_seconds: float = Field(..., gt=0, description="Total speaking duration in seconds")
        scenario_id: Optional[str] = Field(None, description="Scenario identifier")
        speech_events: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed speech events from STT")

    class SpeakingMetricsSchema(BaseModel):
        word_count: int
        duration_seconds: float
        wpm: float
        pace_category: str
        pace_label: str
        filler_count: int
        filler_rate: float
        detected_fillers: Dict[str, int]
        pause_count: int
        long_pause_count: int
        average_pause_duration: float
        pause_available: bool

    class DeliveryDimensionsSchema(BaseModel):
        pace: int
        filler_control: int
        flow_control: int

    class VoiceAnalyzeResponse(BaseModel):
        scenario_id: Optional[str]
        transcript: str
        speaking_metrics: SpeakingMetricsSchema
        delivery_score: int
        delivery_dimensions: DeliveryDimensionsSchema
        delivery_feedback: Dict[str, Any]
        communication_score: int
        communication_dimension_scores: Dict[str, int]
        positive_feedback: List[str]
        improvement_feedback: List[str]
        coaching_tip: str
        say_it_better: SayItBetterSchema
        moderation_status: str
        disclaimer: str

    @router.post("/analyze", response_model=AnalyzeResponse)
    async def analyze_response_endpoint(payload: AnalyzeRequest) -> AnalyzeResponse:
        res = analyze_practice_response(
            text=payload.text,
            scenario_id=payload.scenario_id,
            attempt_number=payload.attempt_number,
            delivery_score=payload.delivery_score,
            speaking_metrics=payload.speaking_metrics,
        )
        return AnalyzeResponse(
            scenario_id=res.scenario_id,
            communication_score=res.communication_score,
            dimension_scores=res.dimension_scores,
            delivery_score=res.delivery_score,
            positive_feedback=res.positive_feedback,
            improvement_feedback=res.improvement_feedback,
            coaching_tip=res.coaching_tip,
            say_it_better=SayItBetterSchema(
                original_text=res.say_it_better.original_text,
                suggested_text=res.say_it_better.suggested_text,
                improvements_made=res.say_it_better.improvements_made,
                coaching_summary=res.say_it_better.coaching_summary,
            ),
            attempt_number=res.attempt_number,
            moderation_status=res.moderation_status,
            disclaimer=res.disclaimer,
        )

    @router.get("/modes")
    async def list_practice_modes_endpoint() -> Dict[str, Any]:
        return {"modes": PRACTICE_MODES}

    @router.get("/scenarios")
    async def list_scenarios_endpoint(mode: Optional[str] = Query(None)) -> Dict[str, Any]:
        scenarios = get_all_scenarios(mode=mode)
        return {"scenarios": scenarios, "count": len(scenarios)}

    @router.get("/scenarios/{scenario_id}")
    async def get_scenario_endpoint(scenario_id: str) -> Dict[str, Any]:
        sc = get_scenario_by_id(scenario_id)
        if not sc:
            raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
        return sc

    @router.get("/challenges/today")
    async def get_today_challenge_endpoint() -> Dict[str, Any]:
        return get_today_challenge()

    @router.post("/session")
    async def record_session_endpoint(
        payload: RecordSessionRequest,
        current_user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        target_user_id = "guest_user"
        if current_user:
            if not current_user.onboarding_completed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="ConversX User ID onboarding required. Please complete onboarding first.",
                    headers={"X-Onboarding-Required": "true"}
                )
            if not current_user.is_admin:
                if payload.user_id and payload.user_id != current_user.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: Cannot record practice session for another user.",
                    )
                target_user_id = current_user.user_id
            else:
                target_user_id = payload.user_id or current_user.user_id
        elif payload.user_id and payload.user_id != "guest_user":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to record practice session for a specific user ID.",
            )

        record = {
            "id": payload.session_id or str(uuid.uuid4()),
            "user_id": target_user_id,
            "scenario_id": payload.scenario_id,
            "practice_type": payload.practice_type,
            "attempt_number": payload.attempt_number,
            "score": payload.score,
            "dimension_scores": payload.dimension_scores or {},
            "delivery_score": payload.delivery_score,
            "wpm": payload.wpm,
            "filler_rate": payload.filler_rate,
            "speaking_duration": payload.speaking_duration,
            "is_voice": payload.is_voice,
            "detected_issues_count": payload.detected_issues_count,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        _SESSION_HISTORY.append(record)
        return {"status": "success", "session_id": record["id"], "recorded": True}

    @router.post("/voice/analyze-audio", response_model=VoiceAnalyzeResponse)
    async def analyze_voice_audio_upload(
        file: UploadFile = File(..., description="Audio file (wav, mp3, webm, m4a)"),
        scenario_id: Optional[str] = Form(None),
    ) -> VoiceAnalyzeResponse:
        import tempfile
        import shutil
        from app.services.whisper_stt import transcribe_audio_file
        from app.services.practice import analyze_voice_response

        raw_filename = file.filename or "audio.webm"
        base_name = os.path.basename(raw_filename)
        ext = os.path.splitext(base_name)[1].lower()
        if not ext or ext not in ALLOWED_AUDIO_EXTENSIONS:
            ext = ".webm"

        raw_mime = (file.content_type or "").lower().split(";")[0].strip()
        if raw_mime and raw_mime not in ALLOWED_AUDIO_MIMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio type: '{raw_mime}'. Supported: wav, webm, mp3, ogg, m4a, aac.",
            )

        temp_dir = tempfile.gettempdir()
        safe_temp_name = f"conversx_voice_{uuid.uuid4().hex}{ext}"
        tmp_path = os.path.join(temp_dir, safe_temp_name)

        total_bytes = 0
        chunk_size = 1024 * 1024
        try:
            with open(tmp_path, "wb") as tmp_file:
                while True:
                    chunk = file.file.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > MAX_AUDIO_SIZE_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Audio file exceeds maximum size limit of 25 MB.",
                        )
                    tmp_file.write(chunk)

            if total_bytes == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded audio file is empty.",
                )

            stt_result = transcribe_audio_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        transcript = stt_result.get("transcript", "").strip()
        duration = stt_result.get("duration_seconds", 10.0)

        res = analyze_voice_response(
            transcript=transcript,
            duration_seconds=duration,
            scenario_id=scenario_id,
            speech_events=stt_result.get("segments", []),
        )

        metrics_schema = SpeakingMetricsSchema(
            word_count=res.speaking_metrics.word_count,
            duration_seconds=res.speaking_metrics.duration_seconds,
            wpm=res.speaking_metrics.wpm,
            pace_category=res.speaking_metrics.pace_category,
            pace_label=res.speaking_metrics.pace_label,
            filler_count=res.speaking_metrics.filler_count,
            filler_rate=res.speaking_metrics.filler_rate,
            detected_fillers=res.speaking_metrics.detected_fillers,
            pause_count=res.speaking_metrics.pause_count,
            long_pause_count=res.speaking_metrics.long_pause_count,
            average_pause_duration=res.speaking_metrics.average_pause_duration,
            pause_available=res.speaking_metrics.pause_available,
        )

        deliv_schema = DeliveryDimensionsSchema(
            pace=res.delivery_dimensions.pace,
            filler_control=res.delivery_dimensions.filler_control,
            flow_control=res.delivery_dimensions.flow_control,
        )

        return VoiceAnalyzeResponse(
            scenario_id=res.scenario_id,
            transcript=res.transcript,
            speaking_metrics=metrics_schema,
            delivery_score=res.delivery_score,
            delivery_dimensions=deliv_schema,
            delivery_feedback=res.delivery_feedback,
            communication_score=res.communication_score,
            communication_dimension_scores=res.communication_dimension_scores,
            positive_feedback=res.positive_feedback,
            improvement_feedback=res.improvement_feedback,
            coaching_tip=res.coaching_tip,
            say_it_better=SayItBetterSchema(
                original_text=res.say_it_better.original_text,
                suggested_text=res.say_it_better.suggested_text,
                improvements_made=res.say_it_better.improvements_made,
                coaching_summary=res.say_it_better.coaching_summary,
            ),
            moderation_status=res.moderation_status,
            disclaimer=res.disclaimer,
        )

    @router.post("/voice/analyze", response_model=VoiceAnalyzeResponse)
    async def analyze_voice_endpoint(payload: VoiceAnalyzeRequest) -> VoiceAnalyzeResponse:
        from app.services.practice import analyze_voice_response

        res = analyze_voice_response(
            transcript=payload.transcript,
            duration_seconds=payload.duration_seconds,
            scenario_id=payload.scenario_id,
            speech_events=payload.speech_events,
        )

        metrics_schema = SpeakingMetricsSchema(
            word_count=res.speaking_metrics.word_count,
            duration_seconds=res.speaking_metrics.duration_seconds,
            wpm=res.speaking_metrics.wpm,
            pace_category=res.speaking_metrics.pace_category,
            pace_label=res.speaking_metrics.pace_label,
            filler_count=res.speaking_metrics.filler_count,
            filler_rate=res.speaking_metrics.filler_rate,
            detected_fillers=res.speaking_metrics.detected_fillers,
            pause_count=res.speaking_metrics.pause_count,
            long_pause_count=res.speaking_metrics.long_pause_count,
            average_pause_duration=res.speaking_metrics.average_pause_duration,
            pause_available=res.speaking_metrics.pause_available,
        )

        deliv_schema = DeliveryDimensionsSchema(
            pace=res.delivery_dimensions.pace,
            filler_control=res.delivery_dimensions.filler_control,
            flow_control=res.delivery_dimensions.flow_control,
        )

        return VoiceAnalyzeResponse(
            scenario_id=res.scenario_id,
            transcript=res.transcript,
            speaking_metrics=metrics_schema,
            delivery_score=res.delivery_score,
            delivery_dimensions=deliv_schema,
            delivery_feedback=res.delivery_feedback,
            communication_score=res.communication_score,
            communication_dimension_scores=res.communication_dimension_scores,
            positive_feedback=res.positive_feedback,
            improvement_feedback=res.improvement_feedback,
            coaching_tip=res.coaching_tip,
            say_it_better=SayItBetterSchema(
                original_text=res.say_it_better.original_text,
                suggested_text=res.say_it_better.suggested_text,
                improvements_made=res.say_it_better.improvements_made,
                coaching_summary=res.say_it_better.coaching_summary,
            ),
            moderation_status=res.moderation_status,
            disclaimer=res.disclaimer,
        )

    @progress_router.get("")
    async def get_progress_overview_endpoint(
        user_id: Optional[str] = Query("guest_user"),
        current_user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> Dict[str, Any]:
        target_user_id = "guest_user"
        if current_user:
            if not current_user.is_admin:
                if user_id and user_id != current_user.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: Cannot access another user's progress data.",
                    )
                target_user_id = current_user.user_id
            else:
                target_user_id = user_id or current_user.user_id
        else:
            if user_id and user_id != "guest_user":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required to access user progress data.",
                )

        user_sessions = [s for s in _SESSION_HISTORY if s["user_id"] == target_user_id]

        if not user_sessions:
            return {
                "overall_score": 75,
                "practice_sessions_count": 0,
                "average_score": 75,
                "best_score": 75,
                "current_streak_days": 1,
                "improvement_pct": 0,
                "dimension_averages": {
                    "clarity": 75,
                    "grammar": 80,
                    "vocabulary": 70,
                    "confidence": 70,
                    "professionalism": 85,
                    "respectfulness": 100,
                    "filler_control": 70,
                    "structure": 70,
                },
                "recent_sessions": [],
            }

        scores = [s["score"] for s in user_sessions]
        avg_score = round(sum(scores) / len(scores))
        best_score = max(scores)

        first_score = scores[0]
        latest_score = scores[-1]
        imp_pct = round(((latest_score - first_score) / max(1, first_score)) * 100) if len(scores) > 1 else 0

        dim_sums: Dict[str, int] = {}
        dim_counts: Dict[str, int] = {}
        for s in user_sessions:
            dims = s.get("dimension_scores") or {}
            for d, val in dims.items():
                dim_sums[d] = dim_sums.get(d, 0) + val
                dim_counts[d] = dim_counts.get(d, 0) + 1

        dim_avgs = {d: round(dim_sums[d] / dim_counts[d]) for d in dim_sums}

        return {
            "overall_score": avg_score,
            "practice_sessions_count": len(user_sessions),
            "average_score": avg_score,
            "best_score": best_score,
            "current_streak_days": min(7, max(1, len(user_sessions))),
            "improvement_pct": imp_pct,
            "dimension_averages": dim_avgs or {
                "clarity": 75,
                "grammar": 80,
                "vocabulary": 70,
                "confidence": 70,
                "professionalism": 85,
                "respectfulness": 100,
                "filler_control": 70,
                "structure": 70,
            },
            "recent_sessions": list(reversed(user_sessions[-5:])),
        }

    @progress_router.get("/history")
    async def get_history_endpoint(
        user_id: Optional[str] = Query("guest_user"),
        limit: int = Query(20, ge=1, le=100),
        current_user: Optional[UserSession] = Depends(get_optional_current_user),
    ) -> List[Dict[str, Any]]:
        if current_user and not current_user.is_admin:
            if user_id != current_user.user_id and user_id != "guest_user":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Cannot access another user's session history.",
                )
        user_sessions = [s for s in _SESSION_HISTORY if s["user_id"] == user_id]
        return list(reversed(user_sessions[-limit:]))

except ImportError:
    router = None
    progress_router = None
