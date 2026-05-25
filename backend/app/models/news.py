"""Pydantic models for news search responses.

Mirrors the field shape returned by Tavily's `/search` endpoint, but
keeps our schema stable if we ever swap providers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewsArticle(BaseModel):
    """A single news search result. Provider-agnostic."""

    model_config = ConfigDict(extra="ignore")

    title: str
    url: str
    content: str = Field(description="Snippet / summary text from the provider.")
    score: float | None = Field(default=None, description="Provider relevance score, 0-1.")
    published_date: datetime | None = None

    @field_validator("published_date", mode="before")
    @classmethod
    def _empty_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class NewsSearchResult(BaseModel):
    """Top-level result of a news search."""

    model_config = ConfigDict(extra="ignore")

    query: str
    articles: list[NewsArticle]
