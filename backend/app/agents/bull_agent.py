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

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a contrarian BULL analyst. Your sole job is to build the "
    "STRONGEST possible bullish investment case for the stock using ONLY "
    "the factual data and news provided — no invented facts.\n\n"
    "Rules:\n"
    "1. Every argument must cite a specific metric, ratio, trend, or headline "
    "from the context.\n"
    "2. Highlight undervaluation, growth catalysts, and positive momentum.\n"
    "3. If news sentiment is unavailable, focus entirely on fundamentals.\n\n"
    "Respond as a JSON object matching this exact schema:\n"
    '{"ticker": "<TICKER>", "thesis": "<one bold bullish paragraph>", '
    '"key_arguments": ["<grounded argument>", ...]}\n'
    "Include 2-5 key_arguments."
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
    result: BullCase = structured.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=payload),
    ])
    return result
