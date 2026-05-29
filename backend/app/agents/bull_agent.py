# backend/app/agents/bull_agent.py
"""Bull Agent — constructs the strongest possible bullish case for a ticker.

Single LLM call (no LangGraph overhead needed for a one-shot analyst).
Reuses the `_format_data` / `_format_sentiment` helpers from manager_agent
to feed the same structured context, ensuring grounding consistency.

Public entry point: `run_bull_agent(data, sentiment) -> BullCase`.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.manager_agent import _format_data, _format_sentiment
from app.config import get_settings
from app.models.agents import DataAgentReport
from app.models.debate import BullCase
from app.models.sentiment import SentimentAgentReport
from app.utils.llm_retry import llm_retry
from app.utils.sanitize import sanitize_bull_thesis

log = logging.getLogger(__name__)


class BullAgentError(Exception):
    """Raised when the Bull Agent fails to produce a valid case."""


_SYSTEM_PROMPT = (
    "You are a contrarian BULL analyst. Your sole job is to build the "
    "STRONGEST possible bullish investment case for the stock using ONLY "
    "the factual data and news provided — no invented facts.\n\n"
    "Rules:\n"
    "1. Every argument must cite a specific metric, ratio, trend, or headline "
    "from the context.\n"
    "2. Highlight undervaluation, growth catalysts, and positive momentum.\n"
    "3. If news sentiment is unavailable, focus entirely on fundamentals.\n\n"
    "## thesis field\n"
    "Write a cohesive FUTURE-FACING narrative paragraph of 3-4 sentences about the NEXT 12-24 MONTHS. "
    "Focus on strategic positioning, upcoming catalysts, and market psychology. "
    "Use forward-looking language: 'expected to capitalize on', 'positioned to benefit from', "
    "'over the next 12 months'. "
    "CRITICAL: Do NOT include bullet points, numbered lists, or mathematical breakdowns — "
    "flowing prose only. Do NOT describe the current 52-week price range. "
    "Do NOT simply restate the same data points from key_arguments — analyze what they imply for the future.\n\n"
    "Respond as a JSON object matching this exact schema:\n"
    '{"ticker": "<TICKER>", '
    '"thesis": "<cohesive 3-4 sentence forward-looking narrative — NO bullets>"}'
)


def run_bull_agent(
    data: DataAgentReport,
    sentiment: SentimentAgentReport,
) -> BullCase:
    """Build the strongest bullish investment case for the ticker."""
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    structured = llm.with_structured_output(BullCase, method="json_mode")

    payload = (
        f"TICKER: {data.ticker}\n\n"
        f"FUNDAMENTALS & PRICE:\n{_format_data(data)}\n\n"
        f"NEWS & SENTIMENT:\n{_format_sentiment(sentiment)}"
    )
    log.info("bull_agent: building bull case for %s", data.ticker)

    @llm_retry
    def _invoke() -> BullCase:
        return structured.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=payload),
        ])

    try:
        result: BullCase = _invoke()
    except Exception as exc:
        log.exception("bull_agent: LLM call failed ticker=%s", data.ticker)
        raise BullAgentError(f"Failed to generate bull case for {data.ticker}") from exc

    clean_thesis = sanitize_bull_thesis(result.thesis)
    if clean_thesis != result.thesis:
        log.debug("bull_agent: sanitized thesis for %s (stripped trailing bullets)", data.ticker)
        result = result.model_copy(update={"thesis": clean_thesis})
    return result


__all__ = ["run_bull_agent", "BullAgentError"]
