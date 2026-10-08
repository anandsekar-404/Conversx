"""
ConversX - Communication Analysis & Coaching Engine.
100% Deterministic evaluation across 8 dimensions:
- Clarity (20%)
- Grammar (15%)
- Vocabulary (10%)
- Confidence (15%)
- Professionalism (15%)
- Respectfulness (10%)
- Filler Control (10%)
- Structure (5%)

Provides actionable, encouraging feedback and deterministic 'Say It Better' alternatives.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.moderation import (
    analyze_communication as analyze_moderation,
    normalize_text,
    tokenize_words,
)
from app.services.scenarios import get_scenario_by_id

# ---------------------------------------------------------------------------
# Configurable Vocabulary & Rule Dictionaries
# ---------------------------------------------------------------------------
DEFAULT_FILLER_WORDS: List[str] = [
    "um", "uh", "like", "actually", "basically", "you know",
    "so", "hmm", "sort of", "kind of", "i mean", "right",
]

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

INFORMAL_CONTRACTIONS: Dict[str, str] = {
    "gonna": "going to",
    "wanna": "want to",
    "gotta": "have to",
    "dunno": "do not know",
    "kinda": "kind of",
    "sorta": "sort of",
    "cuz": "because",
    "cause": "because",
    "u": "you",
    "r": "are",
    "plz": "please",
    "thx": "thank you",
    "y'all": "you all",
}

HEDGING_PHRASES: List[str] = [
    "i think maybe", "i'm not sure but", "im not sure but",
    "i guess", "might be wrong but", "sorry but", "probably maybe",
    "just kind of", "just sort of", "i don't know if this makes sense",
    "idk", "sort of basically",
]

ASSERTIVE_PHRASES: List[str] = [
    "i recommend", "our goal is", "i propose", "the data shows",
    "i accomplished", "we determined", "the key result", "specifically",
    "in summary", "i delivered", "the main advantage",
]

STRUCTURAL_OPENINGS: List[str] = [
    "hello", "hi", "good morning", "good afternoon", "good evening",
    "my name is", "i am writing to", "today i would like to",
    "the purpose of", "i want to discuss", "to begin with",
]

STRUCTURAL_SUPPORTS: List[str] = [
    "because", "for example", "specifically", "in particular",
    "furthermore", "as a result", "for instance", "such as",
    "the reason is", "moreover", "in addition",
]

STRUCTURAL_CONCLUSIONS: List[str] = [
    "therefore", "in conclusion", "to summarize", "in summary",
    "looking forward to", "as a next step", "thank you",
    "in short", "ultimately", "to wrap up",
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class DimensionScores:
    clarity: int
    grammar: int
    vocabulary: int
    confidence: int
    professionalism: int
    respectfulness: int
    filler_control: int
    structure: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "clarity": self.clarity,
            "grammar": self.grammar,
            "vocabulary": self.vocabulary,
            "confidence": self.confidence,
            "professionalism": self.professionalism,
            "respectfulness": self.respectfulness,
            "filler_control": self.filler_control,
            "structure": self.structure,
        }


@dataclass
class SayItBetterResult:
    original_text: str
    suggested_text: str
    improvements_made: List[str]
    coaching_summary: str


@dataclass
class PracticeAnalysisResult:
    scenario_id: Optional[str]
    original_text: str
    word_count: int
    sentence_count: int
    overall_score: int
    dimension_scores: DimensionScores
    detected_fillers: List[Dict[str, Any]]
    detected_grammar_issues: List[Dict[str, Any]]
    detected_wordiness: List[Dict[str, Any]]
    detected_hedges: List[str]
    positive_feedback: List[str]
    improvement_feedback: List[str]
    coaching_tip: str
    say_it_better: SayItBetterResult
    moderation_status: str


# ---------------------------------------------------------------------------
# Sub-Analyzers
# ---------------------------------------------------------------------------
def analyze_fillers(text: str, filler_list: List[str] = DEFAULT_FILLER_WORDS) -> Tuple[List[Dict[str, Any]], int]:
    """Detect configured filler words using boundary-aware regex."""
    clean_lower = text.lower()
    detected = []
    total_fillers = 0

    for filler in filler_list:
        escaped = re.escape(filler)
        pattern = r"(?:^|[\s,;.-])" + escaped + r"(?=[\s,;.-]|$)"
        matches = list(re.finditer(pattern, clean_lower))
        if matches:
            count = len(matches)
            total_fillers += count
            detected.append({
                "filler": filler,
                "count": count,
            })

    detected.sort(key=lambda x: x["count"], reverse=True)
    return detected, total_fillers


def analyze_grammar(text: str) -> List[Dict[str, Any]]:
    """Detect obvious grammatical errors using deterministic rule patterns."""
    issues = []
    clean_lower = text.lower()

    # 1. "a" vs "an" before obvious vowel/consonant letters
    # a + vowel: "a apple", "a elephant", "a idea", "a option", "a urgent"
    a_vowel_matches = re.finditer(r"\b(a)\s+([aeiou][a-z]+)\b", clean_lower)
    for m in a_vowel_matches:
        following_word = m.group(2)
        # Exclude common exception words like "user", "university", "unique"
        if not following_word.startswith(("uni", "use", "one")):
            issues.append({
                "type": "article_usage",
                "matched": f"a {following_word}",
                "suggestion": f"an {following_word}",
                "explanation": f"Use 'an' instead of 'a' before vowel sounds.",
            })

    # an + consonant: "an book", "an car", "an dog"
    an_cons_matches = re.finditer(r"\b(an)\s+([bcdfghjklmnpqrstvwxyz][a-z]+)\b", clean_lower)
    for m in an_cons_matches:
        following_word = m.group(2)
        # Exclude common silent-h words like "hour", "honest", "honor"
        if not following_word.startswith(("hour", "honest", "honor")):
            issues.append({
                "type": "article_usage",
                "matched": f"an {following_word}",
                "suggestion": f"a {following_word}",
                "explanation": f"Use 'a' instead of 'an' before consonant sounds.",
            })

    # 2. Repeated adjacent words ("the the", "is is", "and and")
    repeated_matches = re.finditer(r"\b([a-zA-Z]{2,})\s+\1\b", text, flags=re.IGNORECASE)
    for m in repeated_matches:
        word = m.group(1)
        issues.append({
            "type": "duplicate_word",
            "matched": f"{word} {word}",
            "suggestion": word,
            "explanation": f"Duplicate adjacent word '{word}' detected.",
        })

    # 3. Double negatives
    double_negs = [
        ("don't have no", "do not have any"),
        ("dont have no", "do not have any"),
        ("didn't see nothing", "did not see anything"),
        ("didnt see nothing", "did not see anything"),
        ("can't get no", "cannot get any"),
        ("cant get no", "cannot get any"),
        ("won't do nothing", "will not do anything"),
        ("wont do nothing", "will not do anything"),
    ]
    for pattern, fix in double_negs:
        if pattern in clean_lower:
            issues.append({
                "type": "double_negative",
                "matched": pattern,
                "suggestion": fix,
                "explanation": "Double negative detected. Rephrase for clear positive/negative polarity.",
            })

    # 4. Subject-verb agreement cues
    sv_errors = [
        ("they is", "they are"),
        ("we is", "we are"),
        ("you is", "you are"),
        ("i is", "I am"),
        ("i are", "I am"),
        ("he don't", "he does not"),
        ("she don't", "she does not"),
        ("it don't", "it does not"),
    ]
    for pattern, fix in sv_errors:
        if re.search(r"\b" + re.escape(pattern) + r"\b", clean_lower):
            issues.append({
                "type": "subject_verb_agreement",
                "matched": pattern,
                "suggestion": fix,
                "explanation": f"Subject-verb disagreement: '{pattern}' should typically be '{fix}'.",
            })

    return issues


def analyze_clarity_and_wordiness(text: str, tokens: List[str]) -> Tuple[int, List[Dict[str, Any]], List[str]]:
    """Evaluate sentence complexity, overly long sentences, and wordy phrases."""
    clean_lower = text.lower()
    wordiness_detected = []
    for phrase, concise in WORDY_PHRASES.items():
        if phrase in clean_lower:
            wordiness_detected.append({
                "wordy": phrase,
                "concise": concise,
            })

    # Split into sentences
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    long_sentences = []
    for s in sentences:
        s_words = s.split()
        if len(s_words) > 28:
            long_sentences.append(s)

    # Base clarity score 100
    penalty = 0
    penalty += len(long_sentences) * 12
    penalty += len(wordiness_detected) * 8

    # Average sentence length penalty
    if sentences:
        avg_len = len(tokens) / len(sentences)
        if avg_len > 24:
            penalty += int((avg_len - 24) * 2)

    score = max(35, min(100, 100 - penalty))
    return score, wordiness_detected, long_sentences


def analyze_vocabulary(tokens: List[str]) -> Tuple[int, Dict[str, int], float]:
    """Measure vocabulary variety (Type-Token Ratio) and basic repetitive words."""
    if not tokens:
        return 50, {}, 0.0

    total_count = len(tokens)
    unique_tokens = set(t.lower() for t in tokens)
    ttr = len(unique_tokens) / total_count  # lexical diversity

    # Overused basic words count
    basic_counts = {}
    clean_tokens = [t.lower() for t in tokens]
    for basic_word in BASIC_OVERUSED_WORDS.keys():
        cnt = clean_tokens.count(basic_word)
        if cnt >= 2:
            basic_counts[basic_word] = cnt

    # Score from TTR and overused words
    # A natural paragraph typically has TTR around 0.55 - 0.85
    base = 70
    if ttr >= 0.70:
        base += 20
    elif ttr >= 0.55:
        base += 10
    elif ttr < 0.40:
        base -= 15

    # Penalize excessive basic words
    overuse_penalty = sum(cnt * 3 for cnt in basic_counts.values())
    score = max(40, min(100, base - overuse_penalty))

    return score, basic_counts, round(ttr, 2)


def analyze_confidence(text: str) -> Tuple[int, List[str], List[str]]:
    """Detect hedging markers versus assertive expressions."""
    clean_lower = text.lower()
    hedges_found = []
    for hedge in HEDGING_PHRASES:
        if hedge in clean_lower:
            hedges_found.append(hedge)

    assertive_found = []
    for assertive in ASSERTIVE_PHRASES:
        if assertive in clean_lower:
            assertive_found.append(assertive)

    base = 85
    penalty = len(hedges_found) * 14
    boost = min(15, len(assertive_found) * 5)
    score = max(30, min(100, base - penalty + boost))

    return score, hedges_found, assertive_found


def analyze_professionalism(text: str, tokens: List[str]) -> Tuple[int, List[str]]:
    """Detect informal contractions, texting abbreviations, and shouty caps."""
    clean_lower = text.lower()
    informal_found = []

    for informal, formal in INFORMAL_CONTRACTIONS.items():
        if re.search(r"\b" + re.escape(informal) + r"\b", clean_lower):
            informal_found.append(f"{informal} -> {formal}")

    # Check for excessive ALL CAPS words (excluding single letters like 'I')
    caps_words = [w for w in text.split() if w.isupper() and len(w) > 2]
    if len(caps_words) >= 2:
        informal_found.append(f"Excessive capitalization: {', '.join(caps_words[:3])}")

    penalty = len(informal_found) * 12
    score = max(40, min(100, 100 - penalty))
    return score, informal_found


def analyze_structure(text: str, sentence_count: int) -> Tuple[int, Dict[str, bool]]:
    """Evaluate opening, main body, supporting reasoning, and conclusion."""
    clean_lower = text.lower()
    has_opening = any(op in clean_lower for op in STRUCTURAL_OPENINGS)
    has_support = any(sp in clean_lower for sp in STRUCTURAL_SUPPORTS)
    has_conclusion = any(cl in clean_lower for cl in STRUCTURAL_CONCLUSIONS)
    has_body = sentence_count >= 2

    # Score calculation
    pts = 40  # base
    if has_opening:
        pts += 15
    if has_body:
        pts += 15
    if has_support:
        pts += 15
    if has_conclusion:
        pts += 15

    components = {
        "opening": has_opening,
        "main_point": has_body,
        "supporting_detail": has_support,
        "conclusion": has_conclusion,
    }
    return min(100, pts), components


# ---------------------------------------------------------------------------
# Deterministic "Say It Better" Engine
# ---------------------------------------------------------------------------
def generate_say_it_better(
    text: str,
    fillers: List[Dict[str, Any]],
    wordy: List[Dict[str, Any]],
    grammar: List[Dict[str, Any]],
    informal: List[str],
) -> SayItBetterResult:
    """Produce a deterministic, improved alternative response with explanation."""
    improved = text
    improvements = []

    # 1. Remove filler words (replace with space, keep punctuation sensible)
    filler_tokens_removed = 0
    for f in fillers:
        filler_word = f["filler"]
        pattern = r"\b" + re.escape(filler_word) + r"\b[\s,]?\s*"
        matches = len(re.findall(pattern, improved, flags=re.IGNORECASE))
        if matches > 0:
            improved = re.sub(pattern, "", improved, flags=re.IGNORECASE)
            filler_tokens_removed += matches

    if filler_tokens_removed > 0:
        improvements.append(f"Removed {filler_tokens_removed} filler word(s) to sharpen delivery.")

    # 2. Replace wordy phrases with concise phrasing
    for w in wordy:
        pattern = re.compile(re.escape(w["wordy"]), re.IGNORECASE)
        if pattern.search(improved):
            improved = pattern.sub(w["concise"], improved)
            improvements.append(f"Replaced wordy phrase '{w['wordy']}' with '{w['concise']}'.")

    # 3. Replace informal contractions
    for inf_item in informal:
        if " -> " in inf_item:
            inf, formal = inf_item.split(" -> ")
            pattern = re.compile(r"\b" + re.escape(inf) + r"\b", re.IGNORECASE)
            if pattern.search(improved):
                improved = pattern.sub(formal, improved)
                improvements.append(f"Replaced informal word '{inf}' with professional '{formal}'.")

    # 4. Clean up duplicate words and punctuation spacing
    improved = re.sub(r"\\b([a-zA-Z]{2,})\s+\\b", r"", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\s+", " ", improved).strip()
    improved = re.sub(r"\s+([.,!?;:])", r"", improved)

    # 5. Ensure sentences start with capital letters
    sentences = re.split(r"([.!?]\s*)", improved)
    capitalized_parts = []
    for part in sentences:
        if part and part[0].isalpha():
            part = part[0].upper() + part[1:]
        capitalized_parts.append(part)
    improved = "".join(capitalized_parts)

    if not improvements:
        improvements.append("Response is already clear and well-structured.")
        coaching_summary = "Your phrasing is well balanced. Continue practicing with different scenarios."
    else:
        coaching_summary = "Cleaned up conversational clutter and reinforced professional clarity."

    return SayItBetterResult(
        original_text=text,
        suggested_text=improved,
        improvements_made=improvements,
        coaching_summary=coaching_summary,
    )


# ---------------------------------------------------------------------------
# Master Practice Analysis Entrypoint
# ---------------------------------------------------------------------------
def analyze_practice_response(text: str, scenario_id: Optional[str] = None) -> PracticeAnalysisResult:
    """
    Complete deterministic communication practice analysis pipeline:
    1. Clarity (20%)
    2. Grammar (15%)
    3. Vocabulary (10%)
    4. Confidence (15%)
    5. Professionalism (15%)
    6. Respectfulness (10%) -> Reuses Firebase rule-based moderation engine
    7. Filler Control (10%)
    8. Structure (5%)
    """
    raw_text = text or ""
    normalized = normalize_text(raw_text)
    tokens = tokenize_words(normalized)
    word_count = len(tokens)

    # Handle empty response
    if not tokens:
        dim = DimensionScores(50, 50, 50, 50, 50, 100, 100, 40)
        return PracticeAnalysisResult(
            scenario_id=scenario_id,
            original_text=raw_text,
            word_count=0,
            sentence_count=0,
            overall_score=50,
            dimension_scores=dim,
            detected_fillers=[],
            detected_grammar_issues=[],
            detected_wordiness=[],
            detected_hedges=[],
            positive_feedback=["Ready for your response."],
            improvement_feedback=["Type or speak a complete sentence to receive comprehensive feedback."],
            coaching_tip="Start with a strong opening sentence that addresses the prompt directly.",
            say_it_better=SayItBetterResult(raw_text, raw_text, ["No input provided."], "Ready to assist."),
            moderation_status="safe",
        )

    # Count sentences
    sentences = [s.strip() for s in re.split(r"[.!?]+", raw_text) if s.strip()]
    sentence_count = max(1, len(sentences))

    # 1. Fillers Analysis
    detected_fillers, total_fillers = analyze_fillers(raw_text)
    # Filler control: 100 minus penalty per filler
    filler_penalty = total_fillers * 12
    filler_score = max(0, min(100, 100 - filler_penalty))

    # 2. Grammar Analysis
    detected_grammar = analyze_grammar(raw_text)
    grammar_penalty = len(detected_grammar) * 15
    grammar_score = max(30, min(100, 100 - grammar_penalty))

    # 3. Clarity & Wordiness
    clarity_score, detected_wordiness, long_sentences = analyze_clarity_and_wordiness(raw_text, tokens)

    # 4. Vocabulary Analysis
    vocab_score, overused_words, ttr = analyze_vocabulary(tokens)

    # 5. Confidence Analysis
    confidence_score, hedges_found, assertive_found = analyze_confidence(raw_text)

    # 6. Professionalism Analysis
    prof_score, informal_found = analyze_professionalism(raw_text, tokens)

    # 7. Respectfulness & Severe Language (REUSES MODERATION ENGINE)
    mod_result = analyze_moderation(raw_text)
    respect_score = mod_result.score
    mod_status = mod_result.status

    # 8. Structure Analysis
    struct_score, struct_components = analyze_structure(raw_text, sentence_count)

    # 9. Overall Score Calculation (Documented Deterministic Formula)
    # Weights:
    # Clarity: 20%, Grammar: 15%, Vocabulary: 10%, Confidence: 15%,
    # Professionalism: 15%, Respectfulness: 10%, Filler Control: 10%, Structure: 5%
    overall = (
        0.20 * clarity_score
        + 0.15 * grammar_score
        + 0.10 * vocab_score
        + 0.15 * confidence_score
        + 0.15 * prof_score
        + 0.10 * respect_score
        + 0.10 * filler_score
        + 0.05 * struct_score
    )
    overall_score = max(0, min(100, round(overall)))

    dimension_scores = DimensionScores(
        clarity=clarity_score,
        grammar=grammar_score,
        vocabulary=vocab_score,
        confidence=confidence_score,
        professionalism=prof_score,
        respectfulness=respect_score,
        filler_control=filler_score,
        structure=struct_score,
    )

    # 10. Generate Encouraging Feedback (What you did well / What to improve)
    positive_feedback = []
    improvement_feedback = []

    if respect_score >= 95:
        positive_feedback.append("Tone is respectful and workplace-appropriate.")
    if filler_score >= 90:
        positive_feedback.append("Excellent filler word control—speech is crisp and intentional.")
    if clarity_score >= 80:
        positive_feedback.append("Clear message flow with digestible sentence lengths.")
    if grammar_score >= 90:
        positive_feedback.append("Clean sentence mechanics and grammatical agreement.")
    if confidence_score >= 85:
        positive_feedback.append("Decisive phrasing without excessive self-doubt or hedging.")
    if struct_score >= 80:
        positive_feedback.append("Solid response structure with clear opening and supporting details.")

    if not positive_feedback:
        positive_feedback.append("Good start! Your core message is understandable.")

    # Actionable improvement points
    if total_fillers > 0:
        top_fillers = ", ".join(f"'{f['filler']}' ({f['count']}x)" for f in detected_fillers[:2])
        improvement_feedback.append(f"Used {total_fillers} filler word(s) ({top_fillers}). Pause silently instead of using verbal crutches.")

    if detected_grammar:
        top_g = detected_grammar[0]
        improvement_feedback.append(f"Grammar check: {top_g['explanation']}")

    if long_sentences:
        improvement_feedback.append(f"Detected {len(long_sentences)} overly long sentence(s). Break ideas into concise 15-20 word thoughts.")

    if hedges_found:
        top_h = hedges_found[0]
        improvement_feedback.append(f"Avoid self-doubting hedges like '{top_h}'. Speak with direct conviction.")

    if informal_found:
        improvement_feedback.append(f"Elevate informal language: {informal_found[0]}.")

    if mod_status in ["warning", "harmful", "severe"]:
        improvement_feedback.append("Avoid harsh, insulting, or aggressive phrasing. Focus on constructive collaboration.")

    if not improvement_feedback:
        improvement_feedback.append("Strong response! Try practicing with a more complex scenario or tighter time constraint.")

    # Coaching tip based on scenario
    scenario = get_scenario_by_id(scenario_id) if scenario_id else None
    if scenario and "guidance" in scenario:
        coaching_tip = scenario["guidance"]
    elif total_fillers >= 2:
        coaching_tip = "When you feel the urge to say 'um' or 'like', take a silent breath. Silence conveys confidence."
    elif len(long_sentences) > 0:
        coaching_tip = "Aim for one core idea per sentence. Short, punchy sentences make your points memorable."
    else:
        coaching_tip = "Use the Rule of Three: state your point, give one concrete example, and end with the impact."

    # 11. "Say It Better" Alternative
    say_it_better = generate_say_it_better(
        raw_text,
        detected_fillers,
        detected_wordiness,
        detected_grammar,
        informal_found,
    )

    return PracticeAnalysisResult(
        scenario_id=scenario_id,
        original_text=raw_text,
        word_count=word_count,
        sentence_count=sentence_count,
        overall_score=overall_score,
        dimension_scores=dimension_scores,
        detected_fillers=detected_fillers,
        detected_grammar_issues=detected_grammar,
        detected_wordiness=detected_wordiness,
        detected_hedges=hedges_found,
        positive_feedback=positive_feedback,
        improvement_feedback=improvement_feedback,
        coaching_tip=coaching_tip,
        say_it_better=say_it_better,
        moderation_status=mod_status,
    )


# ---------------------------------------------------------------------------
# Phase 5: Voice Communication Coach — Speaking Metrics & Delivery Scoring
# ---------------------------------------------------------------------------

VOICE_DELIVERY_DISCLAIMER = (
    "ConversX evaluates delivery using deterministic pace, filler frequency, and speech continuity. "
    "ConversX does not claim to detect emotions, vocal tone, or psychological confidence."
)


@dataclass
class SpeakingMetrics:
    word_count: int
    duration_seconds: float
    wpm: float
    pace_category: str
    pace_label: str
    filler_count: int
    filler_rate: float
    detected_fillers: List[Dict[str, Any]]
    pause_count: int
    long_pause_count: int
    average_pause_duration: float
    pause_available: bool


@dataclass
class DeliveryDimensions:
    pace: int
    filler_control: int
    flow_control: int


@dataclass
class VoicePracticeAnalysisResult:
    scenario_id: Optional[str]
    transcript: str
    speaking_metrics: SpeakingMetrics
    delivery_score: int
    delivery_dimensions: DeliveryDimensions
    delivery_feedback: Dict[str, Any]
    communication_score: int
    communication_dimension_scores: Dict[str, int]
    positive_feedback: List[str]
    improvement_feedback: List[str]
    coaching_tip: str
    say_it_better: Dict[str, Any]
    moderation_status: str
    disclaimer: str = VOICE_DELIVERY_DISCLAIMER


def classify_pace_tempo(wpm: float) -> Tuple[str, str]:
    if wpm <= 0:
        return "none", "No Speech Detected"
    if wpm < 100:
        return "very_slow", "Very Slow (<100 WPM)"
    if wpm < 120:
        return "slow", "Deliberate / Slow (100–119 WPM)"
    if wpm <= 160:
        return "optimal", "Optimal / Conversational (120–160 WPM)"
    if wpm <= 185:
        return "fast", "Brisk / Fast (161–185 WPM)"
    return "very_fast", "Rushed (>185 WPM)"


def calculate_speaking_metrics(
    transcript: str,
    duration_seconds: float,
    speech_events: Optional[List[Dict[str, Any]]] = None,
    custom_fillers: Optional[List[str]] = None,
) -> SpeakingMetrics:
    words = tokenize_words(transcript or "")
    word_count = len(words)
    clean_duration = max(0.1, float(duration_seconds or 0))
    minutes = clean_duration / 60.0
    wpm = round(word_count / minutes, 1) if word_count > 0 else 0.0

    pace_cat, pace_label = classify_pace_tempo(wpm)

    # Fillers
    fillers_to_check = custom_fillers or DEFAULT_FILLER_WORDS
    normalized = normalize_text(transcript or "")
    detected_fillers = []
    total_fillers = 0

    for filler in fillers_to_check:
        pat = r"\b" + re.escape(filler) + r"\b"
        matches = re.findall(pat, normalized, flags=re.IGNORECASE)
        if matches:
            count = len(matches)
            total_fillers += count
            detected_fillers.append({"filler": filler, "count": count})

    filler_rate = round((total_fillers / max(1, word_count)) * 100, 1) if word_count > 0 else 0.0

    # Pause analysis
    pause_count = 0
    long_pause_count = 0
    avg_pause = 0.0
    pause_available = False

    if speech_events and len(speech_events) >= 2:
        pauses = []
        for i in range(1, len(speech_events)):
            prev = speech_events[i - 1]
            curr = speech_events[i]
            if "endTime" in prev and "startTime" in curr:
                gap = (curr["startTime"] - prev["endTime"]) / 1000.0
                if gap >= 0.8:
                    pauses.append(gap)
                    if gap >= 2.0:
                        long_pause_count += 1
        if pauses:
            pause_count = len(pauses)
            avg_pause = round(sum(pauses) / pause_count, 1)
        pause_available = True

    return SpeakingMetrics(
        word_count=word_count,
        duration_seconds=round(clean_duration, 1),
        wpm=wpm,
        pace_category=pace_cat,
        pace_label=pace_label,
        filler_count=total_fillers,
        filler_rate=filler_rate,
        detected_fillers=detected_fillers,
        pause_count=pause_count,
        long_pause_count=long_pause_count,
        average_pause_duration=avg_pause,
        pause_available=pause_available,
    )


def calculate_delivery_score(metrics: SpeakingMetrics) -> Tuple[int, DeliveryDimensions, Dict[str, Any]]:
    if metrics.word_count == 0:
        return (
            0,
            DeliveryDimensions(pace=0, filler_control=0, flow_control=0),
            {
                "strengths": [],
                "improvements": ["No speech detected in your recording. Please try speaking into the microphone again."],
                "tip": "Ensure your microphone is enabled and speaking audio is captured.",
            },
        )

    # 1. Pace Score (35%)
    wpm = metrics.wpm
    if 125 <= wpm <= 155:
        pace_score = 100
    elif (115 <= wpm < 125) or (155 < wpm <= 165):
        pace_score = 90
    elif (100 <= wpm < 115) or (165 < wpm <= 180):
        pace_score = 75
    elif (80 <= wpm < 100) or (180 < wpm <= 200):
        pace_score = 60
    else:
        pace_score = 40

    # 2. Filler Control Score (35%)
    rate = metrics.filler_rate
    if rate == 0:
        filler_score = 100
    elif rate <= 1.5:
        filler_score = 92
    elif rate <= 3.0:
        filler_score = 82
    elif rate <= 5.0:
        filler_score = 70
    elif rate <= 8.0:
        filler_score = 50
    else:
        filler_score = 35

    # 3. Flow & Continuity Score (30%)
    flow_score = 85
    if metrics.pause_available:
        pauses_per_30s = (metrics.pause_count / max(15.0, metrics.duration_seconds)) * 30.0
        if 0.8 <= pauses_per_30s <= 3.5:
            flow_score += 15
        elif pauses_per_30s < 0.5 and metrics.duration_seconds > 30:
            flow_score -= 10
        if metrics.long_pause_count > 0:
            flow_score -= min(30, metrics.long_pause_count * 12)
    else:
        words_per_sec = metrics.word_count / metrics.duration_seconds
        if 2.0 <= words_per_sec <= 2.8:
            flow_score = 90
        elif words_per_sec > 3.3 or words_per_sec < 1.4:
            flow_score = 75

    flow_score = max(20, min(100, flow_score))

    delivery_score = round(pace_score * 0.35 + filler_score * 0.35 + flow_score * 0.30)
    delivery_score = max(0, min(100, delivery_score))

    # Feedback
    strengths = []
    improvements = []
    if pace_score >= 90:
        strengths.append(f"Optimal conversational pace ({wpm} WPM).")
    elif wpm > 165:
        improvements.append(f"Pace was brisk ({wpm} WPM). Slight slowing helps complex ideas land.")
    elif wpm < 115:
        improvements.append(f"Pace was deliberate ({wpm} WPM). Aim for 125–150 WPM for stronger energy.")

    if filler_score >= 90:
        strengths.append(f"High vocal composure: filler rate was only {rate}%.")
    elif rate > 4.0:
        improvements.append(f"Filler rate was {rate}% ({metrics.filler_count} fillers). Replace verbal fillers with brief pauses.")

    if flow_score >= 85:
        strengths.append("Smooth conversational continuity and pacing.")
    elif metrics.long_pause_count > 1:
        improvements.append(f"{metrics.long_pause_count} extended silences detected. Keeping pauses under 1.5s sustains engagement.")

    tip = "Pause silently for 1 second instead of saying 'um' or 'like'."
    if wpm > 170:
        tip = "Consciously breathe between thoughts to steady your cadence."
    elif wpm < 110:
        tip = "Connect ideas with active transition phrases to maintain conversational momentum."

    return (
        delivery_score,
        DeliveryDimensions(pace=pace_score, filler_control=filler_score, flow_control=flow_score),
        {"strengths": strengths, "improvements": improvements, "tip": tip},
    )


def analyze_voice_response(
    transcript: str,
    duration_seconds: float,
    scenario_id: Optional[str] = None,
    speech_events: Optional[List[Dict[str, Any]]] = None,
) -> VoicePracticeAnalysisResult:
    # 1. Speaking metrics
    metrics = calculate_speaking_metrics(transcript, duration_seconds, speech_events)

    # 2. Communication analysis (existing 8 dimensions + moderation)
    comm_analysis = analyze_practice_response(transcript, scenario_id)

    # 3. Delivery scoring
    delivery_score, delivery_dims, delivery_feedback = calculate_delivery_score(metrics)

    return VoicePracticeAnalysisResult(
        scenario_id=scenario_id,
        transcript=transcript.strip(),
        speaking_metrics=metrics,
        delivery_score=delivery_score,
        delivery_dimensions=delivery_dims,
        delivery_feedback=delivery_feedback,
        communication_score=comm_analysis.overall_score,
        communication_dimension_scores=comm_analysis.dimension_scores,
        positive_feedback=comm_analysis.positive_feedback,
        improvement_feedback=comm_analysis.improvement_feedback,
        coaching_tip=comm_analysis.coaching_tip,
        say_it_better=comm_analysis.say_it_better,
        moderation_status=comm_analysis.moderation_status,
        disclaimer=VOICE_DELIVERY_DISCLAIMER,
    )
