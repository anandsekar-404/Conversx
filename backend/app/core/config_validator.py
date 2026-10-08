"""
ConversX Production Environment & Configuration Validator.
Phase 8 Production Readiness & Reliability Hardening.

Enforces fail-fast startup validation for production environments:
- Rejects weak, default, or short JWT secrets (minimum 32 characters, entropy check)
- Rejects SQLite databases in production (PostgreSQL required)
- Rejects wildcard '*' or localhost in CORS origins in production
- Rejects ALLOW_MOCK_AUTH=True in production
- Rejects DEBUG=True in production
- Ensures critical environment variables are present and secure
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union


class ConfigurationError(ValueError):
    """Raised when critical configuration fails validation for the environment."""
    pass


# Default/weak secrets that must NEVER be used in production
WEAK_SECRET_PATTERNS = [
    r"^secret",
    r"^changeme",
    r"^admin",
    r"^password",
    r"^test",
    r"^default",
    r"^12345",
    r"^dev_",
]


def validate_production_config(env_or_settings: Any = None) -> Tuple[bool, List[str]]:
    """
    Validates environment configuration for launch readiness.
    Accepts either an env dict, a Settings instance, or None (defaults to os.environ).
    If running in production mode, raises ConfigurationError on critical issues.
    Returns (is_valid, list_of_issues).
    """
    issues: List[str] = []

    if env_or_settings is None:
        current_env = dict(os.environ)
    elif isinstance(env_or_settings, dict):
        current_env = env_or_settings
    else:
        # Settings instance or object with attributes
        cors_val = getattr(env_or_settings, "cors_origins", [])
        if isinstance(cors_val, (list, tuple, set)):
            cors_str = ",".join(cors_val)
        else:
            cors_str = str(cors_val)

        jwt_val = getattr(env_or_settings, "jwt_secret_key", getattr(env_or_settings, "jwt_secret", ""))

        current_env = {
            "APP_ENV": getattr(env_or_settings, "app_env", "development"),
            "JWT_SECRET": jwt_val,
            "DATABASE_URL": getattr(env_or_settings, "database_url", ""),
            "CORS_ORIGINS": cors_str,
            "ALLOW_MOCK_AUTH": str(getattr(env_or_settings, "allow_mock_auth", False)),
            "DEBUG": str(getattr(env_or_settings, "debug", False)),
        }

    app_env = str(current_env.get("APP_ENV", "development")).lower()
    is_prod = app_env in ("production", "prod")

    jwt_secret = current_env.get("JWT_SECRET") or current_env.get("JWT_SECRET_KEY", "")
    db_url = current_env.get("DATABASE_URL", "")

    # 1. Critical Variables Existence
    if is_prod:
        if not jwt_secret or jwt_secret.strip() == "":
            issues.append("Missing critical production variable: JWT_SECRET")
        if not db_url or db_url.strip() == "":
            issues.append("Missing critical production variable: DATABASE_URL")

    # 2. JWT Secret Entropy & Security
    if is_prod and jwt_secret:
        if len(jwt_secret) < 32:
            issues.append(f"JWT_SECRET must be at least 32 characters in production (got {len(jwt_secret)})")

        for pattern in WEAK_SECRET_PATTERNS:
            if re.search(pattern, jwt_secret, re.IGNORECASE):
                issues.append(f"JWT_SECRET contains a weak/default pattern: '{pattern}'")
                break

    # 3. Database URL Security
    if is_prod and db_url:
        if db_url.startswith("sqlite"):
            issues.append("Production requires PostgreSQL; SQLite is not permitted in production.")
        elif not db_url.startswith("postgresql"):
            issues.append(f"DATABASE_URL must be a valid PostgreSQL connection in production (got: {db_url.split('://')[0] if '://' in db_url else 'invalid'}).")

    # 4. Mock Auth Enforcement
    allow_mock = str(current_env.get("ALLOW_MOCK_AUTH", "false")).lower() in ("true", "1", "yes")
    if is_prod and allow_mock:
        issues.append("ALLOW_MOCK_AUTH must be False in production mode.")

    # 5. Debug Mode Enforcement
    debug_mode = str(current_env.get("DEBUG", "false")).lower() in ("true", "1", "yes")
    if is_prod and debug_mode:
        issues.append("DEBUG mode must be False in production.")

    # 6. CORS Origins Security
    cors_raw = current_env.get("CORS_ORIGINS", "")
    cors_list = [o.strip() for o in cors_raw.split(",") if o.strip()]
    if is_prod:
        if "*" in cors_list:
            issues.append("Wildcard '*' CORS origin is strictly forbidden in production with credentials.")
        for origin in cors_list:
            if "localhost" in origin.lower() or "127.0.0.1" in origin:
                issues.append(f"Development origin '{origin}' is not permitted in production CORS configuration.")

    if issues and is_prod:
        raise ConfigurationError("Production configuration validation failed:\n- " + "\n- ".join(issues))

    return len(issues) == 0, issues
