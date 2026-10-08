"""
ConversX NLP Engine — Clarity & Conciseness Analysis Module.
Detects wordy idioms, overly long run-on sentences, and phrasing clutter.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

WORDY_PHRASES: Dict[str, str] = {
    "due to the fact that": "because",
    "in order to": "to",
    "at the present time": "now",
    "at this point in time": "currently",
    "in spite of the fact that": "although",
    "for the purpose of": "to",
    "in the event that": "if",
    "has the ability to": "can",
    "in close proximity to": "near",
    "each and every": "every",
}

def analyze_clarity(text: str, sentences: List[str]) -> Dict[str, Any]:
    wordy_found: List[Dict[str, str]] = []
    normalized = text.lower()

    for phrase, replacement in WORDY_PHRASES.items():
        if phrase in normalized:
            wordy_found.append({"phrase": phrase, "suggested": replacement})

    long_sentences: List[str] = []
    for s in sentences:
        s_words = s.strip().split()
        if len(s_words) > 32:
            long_sentences.append(s.strip())

    score = 100 - (len(wordy_found) * 10) - (len(long_sentences) * 15)
    score = max(25, min(100, score))

    return {
        "score": score,
        "wordy_phrases": wordy_found,
        "long_sentences": long_sentences,
    }
