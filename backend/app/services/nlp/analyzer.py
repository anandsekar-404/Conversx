"""
ConversX Modular NLP Analyzer Facade.
Combines grammar, vocabulary, clarity, confidence, and structure modules into a unified API.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

from app.services.nlp.grammar import analyze_grammar
from app.services.nlp.vocabulary import analyze_vocabulary
from app.services.nlp.clarity import analyze_clarity
from app.services.nlp.confidence import analyze_confidence
from app.services.nlp.structure import analyze_structure

def split_sentences(text: str) -> List[str]:
    raw = re.split(r"[.!?]+", text)
    return [s.strip() for s in raw if s.strip()]

def run_nlp_analysis(text: str) -> Dict[str, Any]:
    sentences = split_sentences(text)
    words = re.findall(r"\b[A-Za-z0-9'-]+\b", text)

    grammar_res = analyze_grammar(text)
    vocab_res = analyze_vocabulary(words)
    clarity_res = analyze_clarity(text, sentences)
    confidence_res = analyze_confidence(text)
    structure_res = analyze_structure(text, len(sentences))

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "grammar": grammar_res,
        "vocabulary": vocab_res,
        "clarity": clarity_res,
        "confidence": confidence_res,
        "structure": structure_res,
    }
