"""
ConversX Whisper Speech-to-Text Service.
Controlled singleton loader using faster-whisper.
Configurable via environment variables (WHISPER_MODEL, WHISPER_DEVICE).
Does not reload model on every request. Supports CPU execution safely.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("conversx.whisper")

_WHISPER_MODEL_INSTANCE: Optional[Any] = None
_WHISPER_LOAD_ATTEMPTED: bool = False

def get_whisper_config() -> Tuple[str, str, str]:
    model_size = os.getenv("WHISPER_MODEL", "small")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8" if device == "cpu" else "float16")
    return model_size, device, compute_type

def get_whisper_model() -> Optional[Any]:
    global _WHISPER_MODEL_INSTANCE, _WHISPER_LOAD_ATTEMPTED
    if _WHISPER_MODEL_INSTANCE is not None:
        return _WHISPER_MODEL_INSTANCE

    if _WHISPER_LOAD_ATTEMPTED:
        return None

    _WHISPER_LOAD_ATTEMPTED = True
    model_size, device, compute_type = get_whisper_config()

    try:
        from faster_whisper import WhisperModel
        logger.info(f"Loading Whisper model singleton: size={model_size}, device={device}, compute_type={compute_type}")
        _WHISPER_MODEL_INSTANCE = WhisperModel(
            model_size_or_path=model_size,
            device=device,
            compute_type=compute_type,
            download_root=os.getenv("WHISPER_DOWNLOAD_ROOT", None),
        )
        logger.info("Whisper model loaded successfully.")
        return _WHISPER_MODEL_INSTANCE
    except Exception as e:
        logger.warning(f"Could not load faster-whisper model ({e}). Using mock/fallback transcription.")
        return None

def transcribe_audio_file(
    audio_path_or_file: str,
    language: str = "en",
) -> Dict[str, Any]:
    """
    Transcribes audio using the loaded Whisper singleton model.
    Falls back gracefully if running in testing/mock environment.
    """
    model = get_whisper_model()
    if model is None:
        # Fallback or mock behavior when Whisper is not initialized
        return {
            "transcript": "Hello everyone. This is a transcribed voice response practicing communication clarity.",
            "duration_seconds": 12.5,
            "language": language,
            "segments": [
                {
                    "start": 0.0,
                    "end": 6.0,
                    "text": "Hello everyone. This is a transcribed voice response",
                },
                {
                    "start": 6.8,
                    "end": 12.5,
                    "text": "practicing communication clarity.",
                },
            ],
            "is_fallback": True,
        }

    try:
        segments, info = model.transcribe(
            audio_path_or_file,
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        transcript_parts = []
        segment_list = []
        for segment in segments:
            transcript_parts.append(segment.text.strip())
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            })

        full_transcript = " ".join(transcript_parts).strip()
        return {
            "transcript": full_transcript,
            "duration_seconds": round(info.duration, 1),
            "language": info.language,
            "segments": segment_list,
            "is_fallback": False,
        }
    except Exception as err:
        logger.error(f"Whisper transcription failed: {err}")
        return {
            "transcript": "",
            "duration_seconds": 0.0,
            "language": language,
            "segments": [],
            "error": str(err),
            "is_fallback": True,
        }
