from __future__ import annotations

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    wardesk_contact: str = Field(default="you@example.com")
    database_url: str = ""
    redis_url: str = ""
    anthropic_api_key: str = ""
    steam_api_key: str = ""
    ingest_interval_seconds: int = 45
    rate_limit_guard: bool = True
    community_base_url: HttpUrl = Field(default="https://api.helldivers2.dev")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])


settings = Settings()
