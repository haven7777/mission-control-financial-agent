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
    tavily_api_key: str | None = None
    fmp_api_key: str | None = None

    # LLM model selection
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model used when Groq is the active LLM provider.",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model used when OpenAI is the active LLM provider.",
    )

    # LangSmith tracing
    langsmith_api_key: str | None = None
    langsmith_tracing: bool = False
    langsmith_project: str = "financial-agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    @property
    def langsmith_configured(self) -> bool:
        """True iff both a LangSmith key is present and tracing is opted in."""
        return bool(self.langsmith_api_key) and self.langsmith_tracing

    # ── Supabase (report cache + future pgvector RAG) ─────────────────────
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    report_cache_ttl_hours: int = Field(
        default=24,
        description="Hours before a cached FinalReport is considered stale.",
    )

    @property
    def supabase_configured(self) -> bool:
        """True iff both Supabase URL and service-role key are present."""
        return bool(self.supabase_url) and bool(self.supabase_service_role_key)

    @property
    def fmp_configured(self) -> bool:
        """True iff an FMP API key is present."""
        return bool(self.fmp_api_key)


@lru_cache
def get_settings() -> Settings:
    """Process-wide singleton; cached so we read `.env` once."""
    return Settings()
