"""
ConversX - Application Settings & Configuration.
Provides strict production configuration validation, dual-mode support
(pydantic-settings when available, standard-library fallback in host/test environments).
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from app.core.config_validator import validate_production_config, ConfigurationError

try:
    from pydantic import field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


def _clean_origin(orig: str) -> str:
    return orig.strip(" '\"[]")


if HAS_PYDANTIC:
    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )

        # Application
        app_env: str = os.getenv("APP_ENV", "development")
        app_secret_key: str = os.getenv("APP_SECRET_KEY", "conversx-dev-secret-key-32chars-min-len!!")
        app_domain: str = os.getenv("APP_DOMAIN", "conversx.com")
        app_url: str = os.getenv("APP_URL", "https://conversx.com")
        admin_url: str = os.getenv("ADMIN_URL", "https://admin.conversx.com")
        api_url: str = os.getenv("API_URL", "https://api.conversx.com")

        # Database
        database_url: str = os.getenv("DATABASE_URL", "sqlite:///./conversx_dev.db")

        # Redis
        redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

        debug: bool = os.getenv("DEBUG", "false").lower() in ("true", "1")
        allow_mock_auth: bool = os.getenv("ALLOW_MOCK_AUTH", "false").lower() in ("true", "1")

        # Auth
        jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "conversx-production-jwt-secret-key-phase7")
        jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
        cookie_domain: str = os.getenv("COOKIE_DOMAIN", ".conversx.com")
        cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1")

        # CORS
        cors_origins: List[str] = ["https://conversx.com", "https://www.conversx.com"]

        @field_validator("cors_origins", mode="before")
        @classmethod
        def parse_cors(cls, v: str | List[str]) -> List[str]:
            if isinstance(v, str):
                return [_clean_origin(origin) for origin in v.split(",") if _clean_origin(origin)]
            return v

        # Quotas
        stt_minutes_per_user_per_day: int = 30
        llm_requests_per_user_per_day: int = 50
        max_audio_clip_seconds: int = 60

        @property
        def is_production(self) -> bool:
            return self.app_env.lower() == "production"

        @property
        def is_test(self) -> bool:
            return self.app_env.lower() == "test"

else:
    class Settings:
        """Pure-Python standard-library fallback for host environments without pydantic."""
        def __init__(self, **kwargs) -> None:
            self.debug = kwargs.get("debug", os.getenv("DEBUG", "false").lower() in ("true", "1"))
            self.allow_mock_auth = kwargs.get("allow_mock_auth", os.getenv("ALLOW_MOCK_AUTH", "false").lower() in ("true", "1"))
            self.app_env = kwargs.get("app_env", os.getenv("APP_ENV", "development"))
            self.app_secret_key = kwargs.get("app_secret_key", os.getenv("APP_SECRET_KEY", "conversx-dev-secret-key-32chars-min-len!!"))
            self.app_domain = kwargs.get("app_domain", os.getenv("APP_DOMAIN", "conversx.com"))
            self.app_url = kwargs.get("app_url", os.getenv("APP_URL", "https://conversx.com"))
            self.admin_url = kwargs.get("admin_url", os.getenv("ADMIN_URL", "https://admin.conversx.com"))
            self.api_url = kwargs.get("api_url", os.getenv("API_URL", "https://api.conversx.com"))
            self.database_url = kwargs.get("database_url", os.getenv("DATABASE_URL", "sqlite:///./conversx_dev.db"))
            self.redis_url = kwargs.get("redis_url", os.getenv("REDIS_URL", "redis://redis:6379/0"))
            self.jwt_secret_key = kwargs.get("jwt_secret_key", os.getenv("JWT_SECRET_KEY", "conversx-production-jwt-secret-key-phase7"))
            self.jwt_algorithm = kwargs.get("jwt_algorithm", os.getenv("JWT_ALGORITHM", "HS256"))
            self.access_token_expire_minutes = int(kwargs.get("access_token_expire_minutes", os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")))
            self.refresh_token_expire_days = int(kwargs.get("refresh_token_expire_days", os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")))
            self.cookie_domain = kwargs.get("cookie_domain", os.getenv("COOKIE_DOMAIN", ".conversx.com"))
            self.cookie_secure = kwargs.get("cookie_secure", os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1"))

            cors_raw = kwargs.get("cors_origins", os.getenv("CORS_ORIGINS", "https://conversx.com,https://www.conversx.com"))
            if isinstance(cors_raw, str):
                self.cors_origins = [_clean_origin(o) for o in cors_raw.split(",") if _clean_origin(o)]
            else:
                self.cors_origins = list(cors_raw)

            self.stt_minutes_per_user_per_day = 30
            self.llm_requests_per_user_per_day = 50
            self.max_audio_clip_seconds = 60

        @property
        def is_production(self) -> bool:
            return self.app_env.lower() == "production"

        @property
        def is_test(self) -> bool:
            return self.app_env.lower() == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
