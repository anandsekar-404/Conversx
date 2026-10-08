"""
ConversX — application settings via pydantic-settings.
All values come from environment variables or .env file.
No secrets have defaults; missing required secrets raise on startup.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_secret_key: str
    app_domain: str = "conversx.com"
    app_url: str = "https://conversx.com"
    admin_url: str = "https://admin.conversx.com"
    api_url: str = "https://api.conversx.com"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    cookie_domain: str = ".conversx.com"
    cookie_secure: bool = False   # True in production

    # CORS
    cors_origins: List[str] = ["https://conversx.com"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Turnstile
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""

    # Cloudflare Access
    cf_access_team_domain: str = ""
    cf_access_audience: str = ""

    # Brevo
    brevo_api_key: str = ""
    brevo_from_email: str = "noreply@conversx.com"
    brevo_from_name: str = "ConversX"
    brevo_daily_cap_guard: int = 210

    # AI — Whisper
    whisper_model: str = "small"
    whisper_compute_type: str = "int8"
    whisper_device: str = "cpu"
    whisper_model_dir: str = "/models/whisper"

    # AI — Ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:3b"
    llm_max_tokens_out: int = 150
    llm_temperature: float = 0.7
    llm_rewrite_temperature: float = 0.2
    llm_timeout_seconds: int = 30

    # AI — Detoxify
    detoxify_model: str = "original"
    detoxify_device: str = "cpu"

    # Quotas
    stt_minutes_per_user_per_day: int = 30
    llm_requests_per_user_per_day: int = 50
    max_audio_clip_seconds: int = 60

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
