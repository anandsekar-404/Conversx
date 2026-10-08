"""
ConversX - Moderation API Router.
Provides deterministic rule-based communication analysis, rule retrieval,
and admin endpoints for moderation rule governance.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.moderation import (
    analyze_communication,
    rule_cache,
    DEFAULT_CATEGORIES,
    DEFAULT_SEVERITY_LEVELS,
    DEFAULT_IMPROVEMENT_SUGGESTIONS,
)

logger = logging.getLogger("conversx.api.moderation")

router = APIRouter(prefix="/api/v1/moderation", tags=["moderation"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    text: str = Field(..., max_length=10000, description="User communication text to analyze")
    language: str = Field(default="en", max_length=10, description="Language code")


class MatchedRuleSchema(BaseModel):
    type: str
    match: str
    category: str
    severity: int
    rule_id: Optional[str] = None


class SuggestionSchema(BaseModel):
    category: str
    suggestion: str
    example: str


class CommunicationResultSchema(BaseModel):
    status: str
    score: int
    matched_count: int
    categories: List[str]
    severity: int
    dimensions: Dict[str, int]
    original_text: str
    normalized_text: str
    matched_rules: List[MatchedRuleSchema]
    suggestion: Optional[SuggestionSchema] = None
    source: str


class RuleItemSchema(BaseModel):
    id: Optional[str] = None
    word: Optional[str] = None
    phrase: Optional[str] = None
    category: str
    severity: int = Field(..., ge=0, le=4)
    active: bool = True
    language: str = "en"
    type: str = "word"  # "word" | "phrase"


class RuleCreateRequest(BaseModel):
    type: str = Field(..., description="'word' for badWords, 'phrase' for harassmentPatterns")
    text: str = Field(..., min_length=1, max_length=200, description="The word or phrase pattern")
    category: str = Field(..., description="Category key (e.g. insult, threat)")
    severity: int = Field(..., ge=0, le=4, description="Severity 0 to 4")
    language: str = Field(default="en", description="Language code")
    active: bool = Field(default=True, description="Whether rule is active")


# ---------------------------------------------------------------------------
# Public Moderation Endpoints
# ---------------------------------------------------------------------------
@router.post("/analyze", response_model=CommunicationResultSchema)
async def analyze_text(req: AnalyzeRequest) -> CommunicationResultSchema:
    """
    Analyze user text using the 100% deterministic rule-based engine.
    Returns communication score, severity, matched rules, and constructive suggestions.
    """
    result = analyze_communication(req.text)
    return CommunicationResultSchema(
        status=result.status,
        score=result.score,
        matched_count=result.matched_count,
        categories=result.categories,
        severity=result.severity,
        dimensions=result.dimensions,
        original_text=result.original_text,
        normalized_text=result.normalized_text,
        matched_rules=[
            MatchedRuleSchema(
                type=m["type"],
                match=m["match"],
                category=m["category"],
                severity=m["severity"],
                rule_id=m.get("rule_id"),
            )
            for m in result.matched_rules
        ],
        suggestion=SuggestionSchema(**result.suggestion) if result.suggestion else None,
        source=result.source,
    )


@router.get("/rules")
async def get_active_rules(language: str = "en") -> Dict[str, Any]:
    """
    Retrieve active cached moderation rules for client-side local matching.
    Includes bad words, harassment phrases, categories, and severity definitions.
    """
    words = [
        {"id": r.get("id"), "word": w, "category": r.get("category"), "severity": r.get("severity", 2)}
        for w, r in rule_cache.bad_words.items()
        if r.get("active", True) and r.get("language", "en") == language
    ]

    phrases = [
        {"id": r.get("id"), "phrase": r.get("phrase"), "category": r.get("category"), "severity": r.get("severity", 3)}
        for r in rule_cache.harassment_patterns
        if r.get("active", True) and r.get("language", "en") == language
    ]

    return {
        "bad_words": words,
        "harassment_patterns": phrases,
        "categories": rule_cache.categories,
        "severity_levels": rule_cache.severity_levels,
        "suggestions": rule_cache.suggestions,
        "source": rule_cache.source,
        "synced_at": rule_cache.last_sync_time,
    }


@router.get("/categories")
async def get_categories() -> Dict[str, Any]:
    """Get all configured moderation categories and definitions."""
    return {"categories": rule_cache.categories}


@router.get("/severity-levels")
async def get_severity_levels() -> Dict[str, Any]:
    """Get all severity level thresholds and action definitions."""
    return {"severity_levels": rule_cache.severity_levels}


@router.get("/suggestions")
async def get_suggestions() -> Dict[str, Any]:
    """Get all 'Say It Better' deterministic suggestions."""
    return {"suggestions": rule_cache.suggestions}


# ---------------------------------------------------------------------------
# Admin Governance Endpoints
# ---------------------------------------------------------------------------
@router.post("/admin/sync")
async def admin_sync_rules() -> Dict[str, Any]:
    """Force synchronization of moderation rules from Firebase Firestore."""
    success = rule_cache.sync_from_firestore()
    return {
        "synced": success,
        "source": rule_cache.source,
        "total_bad_words": len(rule_cache.bad_words),
        "total_harassment_patterns": len(rule_cache.harassment_patterns),
        "timestamp": rule_cache.last_sync_time,
    }


@router.get("/admin/rules")
async def admin_list_rules(
    category: Optional[str] = Query(None, description="Filter by category"),
    severity: Optional[int] = Query(None, ge=0, le=4, description="Filter by severity"),
    active: Optional[bool] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search term"),
) -> Dict[str, Any]:
    """List all moderation rules with filtering and search support."""
    results: List[Dict[str, Any]] = []

    # Process bad words
    for w, r in rule_cache.bad_words.items():
        item = {
            "id": r.get("id", f"bw_{w}"),
            "type": "word",
            "content": w,
            "category": r.get("category", "insult"),
            "severity": r.get("severity", 2),
            "active": r.get("active", True),
            "language": r.get("language", "en"),
        }
        results.append(item)

    # Process patterns
    for r in rule_cache.harassment_patterns:
        item = {
            "id": r.get("id"),
            "type": "phrase",
            "content": r.get("phrase", ""),
            "category": r.get("category", "harassment"),
            "severity": r.get("severity", 3),
            "active": r.get("active", True),
            "language": r.get("language", "en"),
        }
        results.append(item)

    # Apply filters
    if category:
        results = [r for r in results if r["category"] == category]
    if severity is not None:
        results = [r for r in results if r["severity"] == severity]
    if active is not None:
        results = [r for r in results if r["active"] == active]
    if search:
        s = search.lower().strip()
        results = [r for r in results if s in r["content"].lower()]

    return {"total": len(results), "rules": results}


@router.post("/admin/rules")
async def admin_create_rule(req: RuleCreateRequest) -> Dict[str, Any]:
    """Add a new rule to the moderation database."""
    content = req.text.lower().strip()
    rule_data = {
        "category": req.category,
        "severity": req.severity,
        "active": req.active,
        "language": req.language,
    }

    if req.type == "word":
        rule_id = f"custom_word_{int(time.time() * 1000)}"
        rule_cache.bad_words[content] = {**rule_data, "word": content, "id": rule_id}
        # If Firestore client available, persist
        if rule_cache._firestore_db:
            try:
                rule_cache._firestore_db.collection("badWords").document(rule_id).set({
                    **rule_data,
                    "word": content,
                })
            except Exception as e:
                logger.error("Failed to write rule to Firestore: %s", e)
        return {"status": "created", "type": "word", "id": rule_id, "word": content}

    elif req.type == "phrase":
        rule_id = f"custom_phrase_{int(time.time() * 1000)}"
        pattern_entry = {**rule_data, "phrase": content, "id": rule_id}
        rule_cache.harassment_patterns.append(pattern_entry)
        if rule_cache._firestore_db:
            try:
                rule_cache._firestore_db.collection("harassmentPatterns").document(rule_id).set({
                    **rule_data,
                    "phrase": content,
                })
            except Exception as e:
                logger.error("Failed to write pattern to Firestore: %s", e)
        return {"status": "created", "type": "phrase", "id": rule_id, "phrase": content}

    else:
        raise HTTPException(status_code=400, detail="Invalid rule type; must be 'word' or 'phrase'")


@router.delete("/admin/rules/{rule_type}/{rule_identifier}")
async def admin_delete_rule(rule_type: str, rule_identifier: str) -> Dict[str, Any]:
    """Delete or deactivate a rule."""
    if rule_type == "word":
        key = rule_identifier.lower().strip()
        if key in rule_cache.bad_words:
            del rule_cache.bad_words[key]
            return {"status": "deleted", "type": "word", "identifier": key}
        # Try finding by ID
        for w, r in list(rule_cache.bad_words.items()):
            if r.get("id") == rule_identifier:
                del rule_cache.bad_words[w]
                return {"status": "deleted", "type": "word", "id": rule_identifier}
        raise HTTPException(status_code=404, detail="Word rule not found")

    elif rule_type == "phrase":
        initial_len = len(rule_cache.harassment_patterns)
        rule_cache.harassment_patterns = [
            p for p in rule_cache.harassment_patterns
            if p.get("id") != rule_identifier and p.get("phrase") != rule_identifier.lower().strip()
        ]
        if len(rule_cache.harassment_patterns) < initial_len:
            return {"status": "deleted", "type": "phrase", "identifier": rule_identifier}
        raise HTTPException(status_code=404, detail="Phrase rule not found")

    else:
        raise HTTPException(status_code=400, detail="Invalid rule type")
