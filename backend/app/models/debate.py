# backend/app/models/debate.py
"""Bull and Bear case models for AI Debate Mode."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BullCase(BaseModel):
    """Structured bullish investment case from the Bull Agent."""

    ticker: str
    thesis: str = Field(description="One bold paragraph making the bullish case.")
    key_arguments: list[str] = Field(
        min_length=2,
        max_length=5,
        description="2-5 concrete bullish arguments grounded in supplied data.",
    )


class BearCase(BaseModel):
    """Structured bearish investment case from the Bear Agent."""

    ticker: str
    thesis: str = Field(description="One bold paragraph making the bearish case.")
    key_arguments: list[str] = Field(
        min_length=2,
        max_length=5,
        description="2-5 concrete bearish arguments grounded in supplied data.",
    )
