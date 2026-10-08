"""
ConversX In-Memory Rate Limiting Module.
Provides lightweight sliding-window rate limiting for authentication and handle checks.
Works as a defense-in-depth layer behind Nginx reverse proxy.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# Client IP -> list of request timestamps
_REQUEST_HISTORY: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    # endpoint_key: (max_requests, window_seconds)
    "auth_google": (15, 60),       # 15 requests per minute
    "check_handle": (60, 60),      # 60 requests per minute
    "reserve_handle": (20, 60),    # 20 requests per minute
    "ai_test": (20, 60),           # 20 requests per minute
    "general_auth": (30, 60),      # 30 requests per minute
}


def check_rate_limit(client_ip: str, endpoint_key: str, custom_limit: Optional[Tuple[int, int]] = None) -> Tuple[bool, int]:
    """
    Checks if a client has exceeded rate limit for a given endpoint.
    Returns (is_allowed, retry_after_seconds).
    """
    # Bypass in test environment if configured
    if os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true":
        return True, 0

    if not client_ip:
        client_ip = "127.0.0.1"

    max_reqs, window_sec = custom_limit or RATE_LIMITS.get(endpoint_key, (60, 60))
    now = time.time()
    cutoff = now - window_sec

    history = _REQUEST_HISTORY[client_ip][endpoint_key]
    # Prune expired entries
    _REQUEST_HISTORY[client_ip][endpoint_key] = [t for t in history if t > cutoff]
    history = _REQUEST_HISTORY[client_ip][endpoint_key]

    if len(history) >= max_reqs:
        oldest = history[0]
        retry_after = max(1, int(oldest + window_sec - now))
        return False, retry_after

    _REQUEST_HISTORY[client_ip][endpoint_key].append(now)
    return True, 0


def reset_rate_limits():
    """Clears all rate limiting history (for unit tests)."""
    _REQUEST_HISTORY.clear()
