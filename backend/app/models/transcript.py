"""Earnings call transcript analysis models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class DodgedQuestion(BaseModel):
    """One analyst Q&A exchange where management gave an evasive response."""

    model_config = ConfigDict(extra="forbid")

    analyst_question: str
    management_response: str
    evasion_signal: str


class TranscriptContext(BaseModel):
    """Aggregated earnings call analysis passed to the Manager Agent."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    quarter: int = 0
    year: int = 0
    date: str | None = None
    executive_tone: Literal["confident", "cautious", "defensive", "neutral"] = "neutral"
    management_sentiment: Literal["positive", "neutral", "negative"] = "neutral"
    key_forward_statements: list[str] = []
    dodged_questions: list[DodgedQuestion] = []
    is_empty: bool = False
