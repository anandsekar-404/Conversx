"""
ConversX - Rule-Based Communication Moderation Engine.
100% Deterministic rule-based detection using Firebase Firestore as the source of truth.
No Machine Learning, NLP models, or external AI moderation APIs are used.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("conversx.moderation")

# ---------------------------------------------------------------------------
# Default Curated Fallback Rules (Seed Data)
# Used when initializing Firestore or as in-memory fallback if Firestore is offline
# ---------------------------------------------------------------------------
DEFAULT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "insult": {"label": "Insult", "default_severity": 2, "description": "Demeaning or disparaging language aimed at a person."},
    "profanity": {"label": "Profanity", "default_severity": 1, "description": "Vulgar, offensive, or crude language."},
    "personal_attack": {"label": "Personal Attack", "default_severity": 3, "description": "Attacking character or integrity rather than ideas."},
    "threat": {"label": "Threat", "default_severity": 4, "description": "Expressions of intention to inflict harm or intimidate."},
    "harassment": {"label": "Harassment", "default_severity": 3, "description": "Repeated unwanted, hostile, or intimidating behavior."},
    "sexual_harassment": {"label": "Sexual Harassment", "default_severity": 4, "description": "Unwelcome sexualized comments or advances."},
    "bullying": {"label": "Bullying", "default_severity": 3, "description": "Coercive, degrading, or domineering language."},
    "hate_or_abuse": {"label": "Hate / Abuse", "default_severity": 4, "description": "Derogatory speech targeting protected characteristics."},
    "aggressive_language": {"label": "Aggressive Language", "default_severity": 2, "description": "Hostile, antagonistic, or confrontational phrasing."},
}

DEFAULT_SEVERITY_LEVELS: Dict[int, Dict[str, str]] = {
    0: {"label": "Safe", "action": "allow"},
    1: {"label": "Mild", "action": "flag"},
    2: {"label": "Warning", "action": "warn"},
    3: {"label": "Harmful", "action": "block"},
    4: {"label": "Severe", "action": "strike"},
}

DEFAULT_IMPROVEMENT_SUGGESTIONS: Dict[str, Dict[str, str]] = {
    "insult": {
        "suggestion": "Express disagreement with ideas or decisions without attacking the individual.",
        "example": "I don't agree with that approach. Could we explore an alternative solution?",
    },
    "profanity": {
        "suggestion": "Replace crude language with constructive terms to keep the conversation professional.",
        "example": "This situation is very frustrating, but let's work on resolving it.",
    },
    "personal_attack": {
        "suggestion": "Focus your feedback on the work or specific behavior rather than personal attributes.",
        "example": "I noticed an issue with this specific deliverable that we should address.",
    },
    "threat": {
        "suggestion": "State your boundaries and expectations clearly and calmly without intimidation.",
        "example": "If this agreement cannot be met, we will need to escalate to the project lead.",
    },
    "harassment": {
        "suggestion": "Respect interpersonal boundaries and communicate with professional courtesy.",
        "example": "Let's keep our communication focused on the agenda for today's meeting.",
    },
    "bullying": {
        "suggestion": "Foster an encouraging environment where questions and different viewpoints are welcomed.",
        "example": "Everyone is still learning this system; let's walk through it together.",
    },
    "aggressive_language": {
        "suggestion": "De-escalate tension by asking open-ended questions rather than making demands.",
        "example": "What do you think is preventing us from meeting this deadline?",
    },
    "hate_or_abuse": {
        "suggestion": "Maintain zero tolerance for abusive speech and uphold inclusive communication.",
        "example": "Let's treat everyone with dignity and respect their background.",
    },
    "sexual_harassment": {
        "suggestion": "Keep workplace and platform interactions professional and respectful.",
        "example": "Please keep discussions focused purely on professional collaboration.",
    },
}

# Standard seed bad words (lowercase, token-matched)
DEFAULT_BAD_WORDS: List[Dict[str, Any]] = [
    {"word": "idiot", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "stupid", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "dumb", "category": "insult", "severity": 1, "active": True, "language": "en"},
    {"word": "moron", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "useless", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "incompetent", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"word": "loser", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "pathetic", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "fool", "category": "insult", "severity": 1, "active": True, "language": "en"},
    {"word": "jerk", "category": "insult", "severity": 1, "active": True, "language": "en"},
    {"word": "damn", "category": "profanity", "severity": 1, "active": True, "language": "en"},
    {"word": "hell", "category": "profanity", "severity": 1, "active": True, "language": "en"},
    {"word": "crap", "category": "profanity", "severity": 1, "active": True, "language": "en"},
    {"word": "bastard", "category": "profanity", "severity": 2, "active": True, "language": "en"},
    {"word": "bitch", "category": "harassment", "severity": 3, "active": True, "language": "en"},
    {"word": "asshole", "category": "profanity", "severity": 2, "active": True, "language": "en"},
    {"word": "shut up", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"word": "worthless", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "trash", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "kill", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"word": "destroy", "category": "threat", "severity": 3, "active": True, "language": "en"},
    {"word": "hurt", "category": "threat", "severity": 3, "active": True, "language": "en"},
    {"word": "pagal", "category": "insult", "severity": 2, "active": True, "language": "hi"},
    {"word": "bewakoof", "category": "insult", "severity": 2, "active": True, "language": "hi"},
    {"word": "muttal", "category": "insult", "severity": 2, "active": True, "language": "ta"},
]

# Standard seed harassment multi-word patterns (phrase-matched)
DEFAULT_HARASSMENT_PATTERNS: List[Dict[str, Any]] = [
    {"phrase": "you are useless", "category": "personal_attack", "severity": 3, "active": True, "language": "en"},
    {"phrase": "your idea is stupid", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"phrase": "nobody likes you", "category": "bullying", "severity": 3, "active": True, "language": "en"},
    {"phrase": "get lost", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"phrase": "i will hurt you", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"phrase": "i will destroy you", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"phrase": "you better watch your back", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"phrase": "i will hunt you down", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"phrase": "kill yourself", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"phrase": "you are worthless", "category": "bullying", "severity": 3, "active": True, "language": "en"},
    {"phrase": "waste of space", "category": "bullying", "severity": 3, "active": True, "language": "en"},
    {"phrase": "you are an idiot", "category": "personal_attack", "severity": 3, "active": True, "language": "en"},
    {"phrase": "shut your mouth", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"phrase": "you have no brain", "category": "personal_attack", "severity": 3, "active": True, "language": "en"},
    {"phrase": "you should be fired", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class MatchedRule:
    type: str  # "word" or "phrase"
    match: str
    category: str
    severity: int
    rule_id: Optional[str] = None


class MatchedRuleDict(dict):
    """Dictionary supporting both item access ('r["match"]') and attribute access ('r.match')."""
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'MatchedRuleDict' object has no attribute '{name}'")


@dataclass
class CommunicationResult:
    status: str  # "safe" | "mild" | "warning" | "harmful" | "severe"
    score: int   # 0 to 100
    matched_count: int
    categories: List[str]
    severity: int  # 0 to 4
    dimensions: Dict[str, int]
    original_text: str
    normalized_text: str
    matched_rules: List[MatchedRuleDict]
    suggestion: Optional[Dict[str, str]] = None
    source: str = "in_memory_rules"

    @property
    def severity_label(self) -> str:
        labels = {0: "Safe", 1: "Mild", 2: "Warning", 3: "Harmful", 4: "Severe"}
        return labels.get(self.severity, "Safe")


# ---------------------------------------------------------------------------
# Text Normalization (Master Prompt Section 3)
# ---------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """
    Deterministic normalization (Master Prompt Section 3):
    - Unicode NFKD decomposition
    - Remove combining diacritical marks (accents)
    - Lowercase conversion
    - Replace non-alphanumeric punctuation and symbols with spaces to protect boundaries
    - Normalize repeated spaces and strip
    Preserves original for display; this is for matching only.
    """
    if not text:
        return ""

    # Normalize Unicode characters
    norm = unicodedata.normalize("NFKD", text)

    # Remove combining diacritical marks (e.g. stúpíd -> stupid)
    norm = "".join(c for c in norm if not unicodedata.combining(c))

    # Lowercase
    norm = norm.lower()

    # Replace punctuation and symbols with spaces to ensure clean token boundaries
    norm = re.sub(r"[^\w\s]", " ", norm, flags=re.UNICODE)

    # Collapse multiple whitespaces and strip
    norm = re.sub(r"\s+", " ", norm).strip()

    return norm


def tokenize_words(normalized_text: str) -> List[str]:
    """
    Extract individual word tokens from normalized text.
    """
    if not normalized_text:
        return []
    return [t for t in normalized_text.split() if t]


# ---------------------------------------------------------------------------
# Moderation Rule Cache & Storage (Master Prompt Section 2 & 10)
# ---------------------------------------------------------------------------
class RuleCache:
    """In-memory cache for active moderation rules with Firestore sync."""

    def __init__(self) -> None:
        self.bad_words: Dict[str, Dict[str, Any]] = {}
        self.harassment_patterns: List[Dict[str, Any]] = []
        self.categories: Dict[str, Dict[str, Any]] = dict(DEFAULT_CATEGORIES)
        self.severity_levels: Dict[int, Dict[str, str]] = dict(DEFAULT_SEVERITY_LEVELS)
        self.suggestions: Dict[str, Dict[str, str]] = dict(DEFAULT_IMPROVEMENT_SUGGESTIONS)
        self.last_sync_time: float = 0.0
        self.source: str = "fallback_seed"
        self._firestore_db = None
        self._init_fallback_rules()

    def _init_fallback_rules(self) -> None:
        """Seed cache with default curated rules or seed_rules.json if present."""
        self.bad_words.clear()
        self.harassment_patterns = []

        seed_file = os.path.join(os.path.dirname(__file__), "seed_rules.json")
        loaded_from_file = False
        if os.path.exists(seed_file):
            try:
                with open(seed_file, "r", encoding="utf-8") as f:
                    seed_data = json.load(f)
                for idx, rule in enumerate(seed_data.get("bad_words", [])):
                    w = rule["word"].lower().strip()
                    self.bad_words[w] = {**rule, "id": f"seed_w_{idx+1}"}
                for idx, rule in enumerate(seed_data.get("harassment_patterns", [])):
                    self.harassment_patterns.append({
                        **rule,
                        "phrase": rule["phrase"].lower().strip(),
                        "id": f"seed_p_{idx+1}",
                    })
                if "improvement_suggestions" in seed_data:
                    self.suggestions.update(seed_data["improvement_suggestions"])
                loaded_from_file = True
            except Exception as e:
                logger.warning("Could not read seed_rules.json: %s", e)

        if not loaded_from_file:
            for idx, rule in enumerate(DEFAULT_BAD_WORDS):
                w = rule["word"].lower().strip()
                self.bad_words[w] = {**rule, "id": f"seed_word_{idx}"}
            for idx, rule in enumerate(DEFAULT_HARASSMENT_PATTERNS):
                self.harassment_patterns.append({
                    **rule,
                    "phrase": rule["phrase"].lower().strip(),
                    "id": f"seed_phrase_{idx}",
                })

        self.source = "fallback_seed"
        self.last_sync_time = time.time()
        logger.info(
            "RuleCache initialized: %d words, %d patterns (seed_file=%s)",
            len(self.bad_words),
            len(self.harassment_patterns),
            loaded_from_file,
        )

    def set_firestore_client(self, db_client: Any) -> None:
        """Inject an authenticated Google Cloud / Firebase Firestore client."""
        self._firestore_db = db_client
        self.sync_from_firestore()

    def sync_from_firestore(self) -> bool:
        """Fetch active rules from Firebase Firestore."""
        if not self._firestore_db:
            return False

        try:
            bw_ref = self._firestore_db.collection("badWords").where("active", "==", True).stream()
            new_bad_words: Dict[str, Dict[str, Any]] = {}
            for doc in bw_ref:
                data = doc.to_dict()
                word = data.get("word", "").lower().strip()
                if word:
                    new_bad_words[word] = {**data, "id": doc.id}

            hp_ref = self._firestore_db.collection("harassmentPatterns").where("active", "==", True).stream()
            new_patterns: List[Dict[str, Any]] = []
            for doc in hp_ref:
                data = doc.to_dict()
                phrase = data.get("phrase", "").lower().strip()
                if phrase:
                    new_patterns.append({**data, "id": doc.id, "phrase": phrase})

            sugg_ref = self._firestore_db.collection("improvementSuggestions").stream()
            new_sugg: Dict[str, Dict[str, str]] = {}
            for doc in sugg_ref:
                data = doc.to_dict()
                if "suggestion" in data:
                    new_sugg[doc.id] = data

            if new_bad_words:
                self.bad_words = new_bad_words
            if new_patterns:
                self.harassment_patterns = new_patterns
            if new_sugg:
                self.suggestions.update(new_sugg)

            self.source = "firebase_firestore"
            self.last_sync_time = time.time()
            logger.info(
                "Successfully synchronized rules from Firebase: %d words, %d patterns",
                len(self.bad_words),
                len(self.harassment_patterns),
            )
            return True
        except Exception as e:
            logger.error("Failed to sync rules from Firebase Firestore: %s", e)
            return False


# Global cache instance
rule_cache = RuleCache()


# ---------------------------------------------------------------------------
# Matching Engine (Master Prompt Section 4 & 12)
# ---------------------------------------------------------------------------
def match_words(tokens: List[str], active_words: Dict[str, Dict[str, Any]]) -> List[MatchedRule]:
    """
    Level 1: Exact word matching with token-aware boundary checking.
    Avoids false positives (e.g. 'classic' won't match 'ass', 'therapist' won't match 'rape').
    """
    matched: List[MatchedRule] = []
    seen: Set[str] = set()

    for token in tokens:
        clean_tok = token.lower()
        if clean_tok in active_words:
            rule_def = active_words[clean_tok]
            if not rule_def.get("active", True):
                continue
            key = f"word:{clean_tok}:{rule_def['category']}"
            if key not in seen:
                seen.add(key)
                matched.append(
                    MatchedRule(
                        type="word",
                        match=rule_def.get("word", clean_tok),
                        category=rule_def.get("category", "insult"),
                        severity=int(rule_def.get("severity", 1)),
                        rule_id=rule_def.get("id"),
                    )
                )

    return matched


def match_phrases(normalized_text: str, active_patterns: List[Dict[str, Any]]) -> List[MatchedRule]:
    """
    Level 2: Phrase matching against harassmentPatterns.
    Uses regex word boundaries to prevent substring false positives.
    """
    matched: List[MatchedRule] = []
    seen: Set[str] = set()

    for pattern in active_patterns:
        if not pattern.get("active", True):
            continue
        phrase = pattern.get("phrase", "").strip().lower()
        if not phrase:
            continue

        clean_phrase = re.sub(r"[^\w\s]", " ", phrase)
        clean_phrase = re.sub(r"\s+", " ", clean_phrase).strip()
        if not clean_phrase:
            continue

        # Regex boundary matching
        regex_pattern = rf"(?:^|\s){re.escape(clean_phrase)}(?:\s|$)"
        if re.search(regex_pattern, normalized_text):
            key = f"phrase:{clean_phrase}:{pattern.get('category')}"
            if key not in seen:
                seen.add(key)
                matched.append(
                    MatchedRule(
                        type="phrase",
                        match=phrase,
                        category=pattern.get("category", "harassment"),
                        severity=int(pattern.get("severity", 2)),
                        rule_id=pattern.get("id"),
                    )
                )

    return matched


# ---------------------------------------------------------------------------
# Severity & Score Calculation (Master Prompt Section 5 & 6)
# ---------------------------------------------------------------------------
def calculate_severity_and_score(
    matched_rules: List[MatchedRule], total_tokens: int
) -> Tuple[int, str, int, Dict[str, int]]:
    """
    Deterministic calculation:
    - 0 = Safe
    - 1 = Mild
    - 2 = Warning
    - 3 = Harmful
    - 4 = Severe
    Score: 0 to 100 based on severity penalties.
    """
    if not matched_rules:
        return 0, "safe", 100, {
            "respectfulness": 100,
            "clarity": 95,
            "aggressiveness": 0,
            "professionalism": 100,
        }

    max_severity = max(r.severity for r in matched_rules)
    count = len(matched_rules)

    if max_severity == 1:
        base_deduction = 18
        status = "mild"
    elif max_severity == 2:
        base_deduction = 38
        status = "warning"
    elif max_severity == 3:
        base_deduction = 68
        status = "harmful"
    else:  # 4
        base_deduction = 92
        status = "severe"

    additional_deduction = min(30, (count - 1) * 8)
    final_score = max(0, min(100, 100 - (base_deduction + additional_deduction)))

    # Calculate deterministic communication dimensions
    respectfulness = max(0, 100 - (max_severity * 22 + count * 4))
    aggressiveness = min(100, max_severity * 24 + count * 4)
    professionalism = max(0, 100 - (max_severity * 20 + count * 5))
    clarity = max(50, 95 - (count * 4))

    dimensions = {
        "respectfulness": int(respectfulness),
        "clarity": int(clarity),
        "aggressiveness": int(aggressiveness),
        "professionalism": int(professionalism),
    }

    return max_severity, status, final_score, dimensions


# ---------------------------------------------------------------------------
# Constructive Suggestions - "Say It Better" (Master Prompt Section 7)
# ---------------------------------------------------------------------------
def select_suggestion(matched_rules: List[MatchedRule]) -> Optional[Dict[str, str]]:
    """Select deterministic 'Say It Better' suggestion based on matched category."""
    if not matched_rules:
        return None

    # Pick category of the highest severity match
    sorted_matches = sorted(matched_rules, key=lambda r: r.severity, reverse=True)
    top_match = sorted_matches[0]
    category = top_match.category

    suggestion_data = rule_cache.suggestions.get(category)
    if suggestion_data:
        return {
            "category": category,
            "suggestion": suggestion_data.get("suggestion", ""),
            "example": suggestion_data.get("example", ""),
        }

    return {
        "category": category,
        "suggestion": "Focus on expressing your perspective constructively and maintaining mutual respect.",
        "example": "I'd like to share an alternative perspective so we can find a solution together.",
    }


# ---------------------------------------------------------------------------
# Master Analysis Entrypoint
# ---------------------------------------------------------------------------
def analyze_communication(text: str) -> CommunicationResult:
    """
    Analyze user communication through the 100% rule-based moderation workflow:
    1. Normalize input deterministically while preserving original text.
    2. Tokenize words with boundary protection.
    3. Run Level 1 token-aware word matching against Firebase badWords.
    4. Run Level 2 phrase matching against Firebase harassmentPatterns.
    5. Aggregate all matches into matched_rules.
    6. Calculate deterministic severity, status, communication score, and dimensions.
    7. Generate 'Say It Better' suggestion based on matched categories.
    """
    original_text = text or ""
    normalized = normalize_text(original_text)

    # Empty string is safe
    if not normalized:
        return CommunicationResult(
            status="safe",
            score=100,
            matched_count=0,
            categories=[],
            severity=0,
            dimensions={"respectfulness": 100, "clarity": 95, "aggressiveness": 0, "professionalism": 100},
            original_text=original_text,
            normalized_text="",
            matched_rules=[],
            suggestion=None,
            source=rule_cache.source,
        )

    # Tokenize words
    tokens = tokenize_words(normalized)

    # Run Level 1: Word Matching
    word_matches = match_words(tokens, rule_cache.bad_words)

    # Run Level 2: Phrase Matching
    phrase_matches = match_phrases(normalized, rule_cache.harassment_patterns)

    # Combine matches
    all_matches = word_matches + phrase_matches

    # Extract unique categories
    categories = sorted(list({m.category for m in all_matches}))

    # Calculate severity & communication scores
    severity, status, score, dimensions = calculate_severity_and_score(all_matches, len(tokens))

    # Generate suggestion
    suggestion = select_suggestion(all_matches)

    # Convert matches to serializable dicts with attribute access
    matched_dicts = [
        MatchedRuleDict({
            "type": m.type,
            "match": m.match,
            "category": m.category,
            "severity": m.severity,
            "rule_id": m.rule_id,
        })
        for m in all_matches
    ]

    return CommunicationResult(
        status=status,
        score=score,
        matched_count=len(all_matches),
        categories=categories,
        severity=severity,
        dimensions=dimensions,
        original_text=original_text,
        normalized_text=normalized,
        matched_rules=matched_dicts,
        suggestion=suggestion,
        source=rule_cache.source,
    )


class ModerationService:
    def __init__(self, cache: RuleCache = rule_cache) -> None:
        self.rule_cache = cache

    def analyze_communication(self, text: str) -> CommunicationResult:
        return analyze_communication(text)

    def normalize(self, text: str) -> str:
        return normalize_text(text)


_moderation_service_instance: Optional[ModerationService] = None


def get_moderation_service() -> ModerationService:
    global _moderation_service_instance
    if _moderation_service_instance is None:
        _moderation_service_instance = ModerationService(rule_cache)
    return _moderation_service_instance
