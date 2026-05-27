# backend/app/agents/bear_agent.py
"""Bear Agent — constructs the strongest possible bearish case for a ticker.

Mirrors bull_agent.py exactly in structure; differs only in system prompt
(pessimistic framing) and return type (BearCase vs BullCase).

Public entry point: `run_bear_agent(data, sentiment) -> BearCase`.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.manager_agent import _format_data, _format_sentiment
from app.config import get_settings
from app.models.agents import DataAgentReport
from app.models.debate import BearCase
from app.models.sentiment import SentimentAgentReport

log = logging.getLogger(__name__)


class BearAgentError(Exception):
    """Raised when the Bear Agent fails to produce a valid case."""


_SYSTEM_PROMPT = (
    "You are a contrarian BEAR analyst. Your sole job is to build the "
    "STRONGEST possible bearish investment case for the stock using ONLY "
    "the factual data and news provided — no invented facts.\n\n"
    "Rules:\n"
    "1. Every argument must cite a specific metric, ratio, trend, or headline "
    "from the context.\n"
    "2. Highlight overvaluation signals, downside risks, and negative momentum.\n"
    "3. If news sentiment is unavailable, focus entirely on fundamental risks.\n\n"
    "Respond as a JSON object matching this exact schema:\n"
    '{"ticker": "<TICKER>", "thesis": "<one bold bearish paragraph>", '
    '"key_arguments": ["<grounded argument>", ...]}\n'
    "Include 2-5 key_arguments."
)


def run_bear_agent(
    data: DataAgentReport,
    sentiment: SentimentAgentReport,
) -> BearCase:
    """Build the strongest bearish investment case for the ticker."""
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    structured = llm.with_structured_output(BearCase, method="json_mode")

    payload = (
        f"TICKER: {data.ticker}\n\n"
        f"FUNDAMENTALS & PRICE:\n{_format_data(data)}\n\n"
        f"NEWS & SENTIMENT:\n{_format_sentiment(sentiment)}"
    )
    log.info("bear_agent: building bear case for %s", data.ticker)
    try:
        result: BearCase = structured.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=payload),
        ])
    except Exception as exc:
        log.error("bear_agent: LLM call failed for %s: %s", data.ticker, exc)
        raise BearAgentError(f"Failed to generate bear case for {data.ticker}") from exc
    return result


__all__ = ["run_bear_agent", "BearAgentError"]
