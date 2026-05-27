"""Filings RAG models — chunks retrieved from SEC EDGAR."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FilingChunk(BaseModel):
    """One embedded text chunk from a 10-K/10-Q section."""

    model_config = ConfigDict(extra="forbid")

    section: str       # 'risk_factors' | 'mda'
    content: str
    similarity: float  # cosine similarity 0-1


class FilingsContext(BaseModel):
    """Aggregated SEC filing context passed to the Manager Agent."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    form_type: str              # '10-K' | '10-Q'
    chunks: list[FilingChunk]
    is_empty: bool = False      # True when EDGAR returned nothing or Supabase unconfigured
