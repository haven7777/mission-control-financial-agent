"""Typed settings loaded from `backend/.env` via pydantic-settings.

All third-party API keys live here (per the architecture's
"keys on backend only" rule). Code should depend on `get_settings()`
rather than reading `os.environ` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = Field(default="dev", description="Runtime environment (dev|prod).")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins; defaults to the Next.js dev server.",
    )

    # Third-party API keys — all optional at config time; services check before calling.
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    alpha_vantage_api_key: str | None = None
    tavily_api_key: str | None = None

    # LangSmith tracing
    langsmith_api_key: str | None = None
    langsmith_tracing: bool = False
    langsmith_project: str = "financial-agent"

    @property
    def alpha_vantage_configured(self) -> bool:
        """True iff a non-demo Alpha Vantage key is loaded."""
        key = self.alpha_vantage_api_key
        return bool(key) and key.lower() != "demo"


@lru_cache
def get_settings() -> Settings:
    """Process-wide singleton; cached so we read `.env` once."""
    return Settings()
