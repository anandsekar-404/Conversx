"""
ConversX NLP Engine — Communication Structure Analysis Module.
Evaluates four-part structured delivery: Opening, Main Point, Supporting Evidence, Conclusion.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

OPENING_MARKERS: List[str] = [
    "hello", "hi", "good morning", "good afternoon", "thank you",
    "i would like to", "to begin with", "firstly", "the purpose of",
]

SUPPORT_MARKERS: List[str] = [
    "for example", "specifically", "in particular", "for instance",
    "because", "as a result", "furthermore", "in addition",
]

CONCLUSION_MARKERS: List[str] = [
    "in conclusion", "to summarize", "in summary", "overall",
    "looking forward", "thank you for your time", "i look forward to",
    "that is why", "ultimately",
]

def analyze_structure(text: str, sentence_count: int) -> Dict[str, Any]:
    normalized = text.lower()
    has_opening = any(m in normalized for m in OPENING_MARKERS) or sentence_count >= 1
    has_support = any(m in normalized for m in SUPPORT_MARKERS)
    has_conclusion = any(m in normalized for m in CONCLUSION_MARKERS)

    score = 60
    if has_opening:
        score += 15
    if has_support:
        score += 15
    if has_conclusion:
        score += 10

    if sentence_count < 2:
        score = min(score, 65)

    score = max(40, min(100, score))
    return {
        "score": score,
        "has_opening": has_opening,
        "has_support": has_support,
        "has_conclusion": has_conclusion,
    }
