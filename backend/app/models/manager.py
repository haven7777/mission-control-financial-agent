"""Manager Agent output models.

`ManagerSynthesis` is the LLM-facing structured-output schema — the
analyst's judgement only. `FinalReport` is what the FastAPI endpoint
returns to clients: synthesis + the underlying snapshots + provenance,
so the UI can render either layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.agents import DataAgentReport
from app.models.debate import BullCase, BearCase
from app.models.filings import FilingsContext
from app.models.sentiment import SentimentAgentReport
from app.models.transcript import TranscriptContext


class OverallView(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class ManagerSynthesis(BaseModel):
    """LLM-returned synthesis (the analyst's judgement)."""

    overall_view: OverallView
    one_line_summary: str = Field(
        description="A single sentence capturing the headline view."
    )
    key_strengths: list[str] = Field(
        min_length=1, max_length=6,
        description="2-6 bullets, each one sentence, grounded in the supplied data/sentiment.",
    )
    key_risks: list[str] = Field(
        min_length=1, max_length=6,
        description="2-6 bullets, each one sentence, grounded in the supplied data/sentiment.",
    )
    deep_narrative: str | None = Field(
        default=None,
        description=(
            "Three-paragraph institutional narrative. "
            "Paragraph 1: SEC filing analysis with exact risk section names and financial metrics. "
            "Paragraph 2: Exec quote analysis with evasion signal subtext. "
            "Paragraph 3: Bull-vs-bear verdict with one key monitoring signal. "
            "Omit entirely when filings_context or transcript_context is absent."
        ),
    )
    executive_summary: str | None = Field(
        default=None,
        description=(
            "A dense, comprehensive institutional executive summary consisting of exactly "
            "3 to 4 detailed sentences. Must be at least 70 words. "
            "Generated ONLY when RESEARCH_MODE is DEEP. Null in FAST mode."
        ),
    )


class FinalReport(BaseModel):
    """Full pipeline output returned to clients."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    company_name: str

    # Synthesis (flattened from ManagerSynthesis for easy UI rendering)
    overall_view: OverallView
    one_line_summary: str
    key_strengths: list[str]
    key_risks: list[str]

    # Debate (populated when debate mode is active)
    bull_case: BullCase | None = None
    bear_case: BearCase | None = None

    # SEC filings context (populated when Supabase + EDGAR are available)
    filings_context: FilingsContext | None = None

    # Earnings call transcript analysis (populated when FMP is configured)
    transcript_context: TranscriptContext | None = None

    # Deep institutional narrative (populated when both filings and transcript are present)
    deep_narrative: str | None = None

    # Dense investment thesis paragraph — Deep mode only
    executive_summary: str | None = None

    # Grounding so consumers can drill down without a second request
    data_snapshot: DataAgentReport
    sentiment_snapshot: SentimentAgentReport

    # Provenance
    model_used: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delta_refreshed: bool = False  # True when served from cache with live data refresh
