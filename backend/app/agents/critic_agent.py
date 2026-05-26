"""Critic Agent — reviews the Manager's synthesis against raw data.

Checks four things:
  1. Numeric grounding  — cited figures match the data snapshot
  2. Sentiment alignment — overall_view consistent with overall_sentiment
  3. Completeness       — major data signals surface in key_risks
  4. Internal consistency — strengths/risks justify the overall_view

Returns `approved` or `needs_revision`. When revising, emits a single
actionable `revision_instruction` the Manager can use directly.

Public entry point: `run_critic_agent(report, data, sentiment) -> CritiqueReport`.
Exported constant: `MAX_REVISION_CYCLES` — used by the pipeline (Task 2) to cap loops.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.agents.manager_agent import _format_data, _format_sentiment
from app.config import get_settings
from app.models.agents import DataAgentReport
from app.models.critic import CritiqueReport, CritiqueResult
from app.models.manager import FinalReport
from app.models.sentiment import SentimentAgentReport

log = logging.getLogger(__name__)

MAX_REVISION_CYCLES = 2

SYSTEM_PROMPT = """\
You are a rigorous financial-analysis auditor. You will receive:
  A) A synthesis report drafted by an analyst (overall_view, one_line_summary, \
key_strengths, key_risks).
  B) The raw financial data snapshot the analyst used.
  C) The news-sentiment snapshot the analyst used.

Your job is to audit the synthesis for four failure modes:

1. NUMERIC GROUNDING — Every figure cited in key_strengths or key_risks (prices, \
P/E, yields, market cap, beta, etc.) must exactly match the supplied data. \
Flag any figure that doesn't appear in the data as a hallucination.

2. SENTIMENT ALIGNMENT — Does overall_view match overall_sentiment? \
If they conflict (e.g. "positive" view but "bearish" sentiment), the synthesis must \
explicitly acknowledge the divergence. Flag if it doesn't.

3. COMPLETENESS — Major risk signals in the data must surface in key_risks. \
Examples: stock trading far below its 52-week high, EPS significantly below analyst \
target, high beta in a volatile market. Flag glaring omissions.

4. INTERNAL CONSISTENCY — Do the key_strengths and key_risks collectively justify \
the overall_view verdict? Flag contradictions (e.g. mostly bearish bullets \
but verdict is "positive").

Respond as a JSON object with this schema:
{
  "verdict": "approved" | "needs_revision",
  "synthesis_confidence": <float 0.0–1.0>,
  "issues": [
    {"field": "<e.g. key_strengths[1]>", "issue": "<one sentence>", \
"severity": "minor" | "major" | "fatal"},
    ...
  ],
  "revision_instruction": "<one specific directive for the analyst to fix, or null>"
}

Set verdict to "approved" only if the synthesis is well-grounded and consistent. \
If ANY major or fatal issue exists, set verdict to "needs_revision". \
revision_instruction must be null when verdict is "approved", and a single \
specific directive when "needs_revision".

CALIBRATING synthesis_confidence — follow this rubric exactly:

Start from a baseline of 0.97 and apply the deductions below. \
Floor the final value at 0.50. Report the exact result; do NOT round to a \
"nice" number like 0.90 or 0.95.

Deductions:
  -0.04  per MINOR issue found
  -0.10  per MAJOR issue found
  -0.20  per FATAL issue found
  -0.04  for each key numeric field that is null/missing in the data \
(P/E ratio, EPS, market cap, 52-week high/low each count separately)
  -0.08  if overall_sentiment conflicts with overall_view without \
explicit acknowledgement in the synthesis
  -0.03  if fewer than 3 news articles were classified (thin evidence base)
  -0.03  if the stock is trading more than 15% below its 52-week high \
and the synthesis does not mention this as a risk

Example: baseline 0.97, one MAJOR issue (−0.10), two MINOR issues (−0.08), \
one missing field (−0.04) → 0.97 − 0.22 = 0.75 → report 0.75.
"""


# --- Exceptions --------------------------------------------------------------


class CriticAgentError(Exception):
    """Base class for Critic Agent failures."""


class MissingLLMKey(CriticAgentError):
    """No Groq key configured."""


# --- Graph state -------------------------------------------------------------


class _CriticAgentState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    data: DataAgentReport
    sentiment: SentimentAgentReport
    report: FinalReport
    revision_round: int
    critique_result: CritiqueResult | None = None


# --- Node --------------------------------------------------------------------


def _critique_node(state: _CriticAgentState) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise MissingLLMKey("OPENAI_API_KEY is not set in backend/.env")

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.0,
    )
    structured = llm.with_structured_output(CritiqueResult, method="json_mode")

    r = state.report
    synthesis_block = (
        f"SYNTHESIS UNDER REVIEW (revision round {state.revision_round}):\n"
        f"  overall_view     : {r.overall_view.value}\n"
        f"  one_line_summary : {r.one_line_summary}\n"
        f"  key_strengths    :\n"
        + "\n".join(f"    [{i}] {s}" for i, s in enumerate(r.key_strengths))
        + "\n  key_risks        :\n"
        + "\n".join(f"    [{i}] {s}" for i, s in enumerate(r.key_risks))
    )
    data_block = _format_data(state.data)
    sentiment_block = _format_sentiment(state.sentiment)

    user_payload = (
        f"TICKER: {state.ticker}\n\n"
        f"{synthesis_block}\n\n"
        f"RAW DATA SNAPSHOT:\n{data_block}\n\n"
        f"NEWS SENTIMENT SNAPSHOT:\n{sentiment_block}"
    )

    log.info(
        "critic_agent: auditing %s (round %d) via Groq (%s)",
        state.ticker, state.revision_round, settings.openai_model,
    )
    result: CritiqueResult = structured.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_payload),
    ])
    return {"critique_result": result}


# --- Graph -------------------------------------------------------------------


def _build_graph():
    graph: StateGraph = StateGraph(_CriticAgentState)
    graph.add_node("critique", _critique_node)
    graph.add_edge(START, "critique")
    graph.add_edge("critique", END)
    return graph.compile()


_compiled_graph = _build_graph()


# --- Public API --------------------------------------------------------------


def run_critic_agent(
    report: FinalReport,
    data: DataAgentReport,
    sentiment: SentimentAgentReport,
    revision_round: int = 1,
) -> CritiqueReport:
    """Audit *report* against *data* and *sentiment*. Returns a `CritiqueReport`."""
    if data.ticker != report.ticker:
        raise ValueError(
            f"data/report ticker mismatch: {data.ticker!r} vs {report.ticker!r}"
        )

    result = _compiled_graph.invoke({
        "ticker": report.ticker,
        "data": data,
        "sentiment": sentiment,
        "report": report,
        "revision_round": revision_round,
    })
    critique_result: CritiqueResult = (
        result["critique_result"] if isinstance(result, dict) else result.critique_result
    )
    if critique_result is None:
        raise RuntimeError("Critic graph finished with no critique_result in state")

    return CritiqueReport(
        ticker=report.ticker,
        critique_result=critique_result,
        revision_round=revision_round,
    )


__all__ = [
    "run_critic_agent",
    "MAX_REVISION_CYCLES",
    "CriticAgentError",
    "MissingLLMKey",
]
