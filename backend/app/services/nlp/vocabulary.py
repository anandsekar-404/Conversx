"""
ConversX NLP Engine — Vocabulary Analysis Module.
Analyzes lexical richness (Type-Token Ratio) and flags overused basic vocabulary.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

BASIC_OVERUSED_WORDS: Dict[str, List[str]] = {
    "good": ["effective", "beneficial", "valuable", "robust", "compelling"],
    "bad": ["problematic", "ineffective", "suboptimal", "adverse", "challenging"],
    "thing": ["concept", "aspect", "element", "component", "factor"],
    "things": ["factors", "elements", "components", "aspects", "details"],
    "very": ["exceptionally", "notably", "highly", "substantially"],
    "really": ["genuinely", "particularly", "significantly"],
    "nice": ["pleasant", "favorable", "constructive", "helpful"],
    "stuff": ["materials", "deliverables", "assets", "content"],
}

def analyze_vocabulary(words: List[str]) -> Dict[str, Any]:
    if not words:
        return {"score": 50, "ttr": 0.0, "overused_words": []}

    word_count = len(words)
    unique_words = set(w.lower() for w in words)
    ttr = len(unique_words) / word_count

    overused_found: List[Dict[str, Any]] = []
    lower_words = [w.lower() for w in words]
    for basic, replacements in BASIC_OVERUSED_WORDS.items():
        count = lower_words.count(basic)
        if count >= 2:
            overused_found.append({
                "word": basic,
                "count": count,
                "suggested_alternatives": replacements[:3],
            })

    score = 75
    if ttr >= 0.75:
        score += 20
    elif ttr >= 0.60:
        score += 10
    elif ttr < 0.40:
        score -= 15

    score -= len(overused_found) * 8
    score = max(30, min(100, score))

    return {
        "score": score,
        "ttr": round(ttr, 2),
        "overused_words": overused_found,
    }
