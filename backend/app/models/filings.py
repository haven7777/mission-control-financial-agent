"""Filings RAG models — chunks retrieved from SEC EDGAR."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FilingChunk(BaseModel):
    """One embedded text chunk from a 10-K/10-Q section."""

    model_config = ConfigDict(extra="forbid")

    section: Literal["risk_factors", "mda"]
    content: str
    similarity: float = Field(ge=0.0, le=1.0, description="Cosine similarity score.")


class FilingsContext(BaseModel):
    """Aggregated SEC filing context passed to the Manager Agent."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    form_type: Literal["10-K", "10-Q"]
    chunks: list[FilingChunk]
    is_empty: bool = False      # True when EDGAR returned nothing or Supabase unconfigured
