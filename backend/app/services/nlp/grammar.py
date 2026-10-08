"""
ConversX NLP Engine — Grammar Analysis Module.
Deterministic, rule-based detection of common grammatical and structural friction points.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

GRAMMAR_RULES: List[Dict[str, Any]] = [
    {
        "id": "duplicate_adjacent_word",
        "pattern": r"\b([A-Za-z]+)\s+\1\b",
        "issue": "Accidental repeated word",
        "suggestion": "Remove duplicated word",
        "penalty": 15,
    },
    {
        "id": "double_negative",
        "pattern": r"\b(don't|do not|can't|cannot|won't|will not|didn't)\s+(no|nothing|nobody|never|nowhere)\b",
        "issue": "Double negative detected",
        "suggestion": "Use single negative (e.g., 'don't have any' or 'have no')",
        "penalty": 15,
    },
    {
        "id": "article_an_before_consonant",
        "pattern": r"\b[Aa]n\s+(book|project|team|system|person|computer|company|presentation|problem|solution)\b",
        "issue": "Article mismatch: 'an' used before a consonant sound",
        "suggestion": "Use 'a' before consonant sounds",
        "penalty": 10,
    },
    {
        "id": "article_a_before_vowel",
        "pattern": r"\b[Aa]\s+(apple|engineer|interview|opportunity|overview|answer|error|example|idea|issue)\b",
        "issue": "Article mismatch: 'a' used before a vowel sound",
        "suggestion": "Use 'an' before vowel sounds",
        "penalty": 10,
    },
    {
        "id": "subject_verb_they_is",
        "pattern": r"\b(they|we)\s+(is|was)\b",
        "issue": "Subject-verb agreement mismatch",
        "suggestion": "Use 'are' or 'were' with plural pronouns",
        "penalty": 15,
    },
]

def analyze_grammar(text: str) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    penalty = 0

    for rule in GRAMMAR_RULES:
        matches = list(re.finditer(rule["pattern"], text, flags=re.IGNORECASE))
        if matches:
            issues.append({
                "rule_id": rule["id"],
                "match": matches[0].group(0),
                "issue": rule["issue"],
                "suggestion": rule["suggestion"],
                "count": len(matches),
            })
            penalty += rule["penalty"] * len(matches)

    score = max(30, 100 - penalty)
    return {
        "score": score,
        "issues": issues,
        "penalty": penalty,
    }
