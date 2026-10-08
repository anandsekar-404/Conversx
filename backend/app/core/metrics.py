"""
ConversX Operational Metrics & Cardinality Protection Utilities.
Phase 8 Production Hardening.
"""
from __future__ import annotations

import re
from typing import List, Tuple

# Regex patterns to normalize dynamic IDs and avoid high-cardinality label explosion
ID_NORMALIZATIONS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"/rooms/room_[a-zA-Z0-9_-]+"), "/rooms/:room_id"),
    (re.compile(r"/public-profile/@[a-zA-Z0-9_]+"), "/public-profile/:handle"),
    (re.compile(r"/topics/disc_[0-9]+"), "/topics/:topic_id"),
    (re.compile(r"/scenarios/[a-zA-Z0-9_-]+"), "/scenarios/:scenario_id"),
    (re.compile(r"/appeals/app_[a-zA-Z0-9_-]+"), "/appeals/:appeal_id"),
    (re.compile(r"/connection/[a-zA-Z0-9_-]+"), "/connection/:provider"),
]


def normalize_metric_path(path: str) -> str:
    """Normalizes dynamic path parameters to prevent high-cardinality Prometheus labels."""
    normalized = path.split("?")[0]
    for pattern, replacement in ID_NORMALIZATIONS:
        normalized = pattern.sub(replacement, normalized)
    return normalized
