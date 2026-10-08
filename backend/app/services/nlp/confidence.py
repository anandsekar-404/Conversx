"""
ConversX NLP Engine — Confidence Language Analysis Module.
Identifies self-deprecating hedging language and rewards assertive framing.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

HEDGING_PHRASES: List[str] = [
    "i guess", "i think maybe", "sort of think", "kind of feel",
    "maybe kinda", "sorry but", "just my opinion but",
    "i might be wrong but", "not really sure but",
]

ASSERTIVE_PHRASES: List[str] = [
    "i recommend", "i propose", "our analysis shows", "i am confident",
    "in my experience", "the key priority is", "the data indicates",
    "i successfully led", "we achieved", "my goal is to",
]

def analyze_confidence(text: str) -> Dict[str, Any]:
    normalized = text.lower()
    hedges_found = [h for h in HEDGING_PHRASES if h in normalized]
    assertive_found = [a for a in ASSERTIVE_PHRASES if a in normalized]

    score = 80 - (len(hedges_found) * 12) + (len(assertive_found) * 8)
    score = max(35, min(100, score))

    return {
        "score": score,
        "hedges_detected": hedges_found,
        "assertive_detected": assertive_found,
    }
