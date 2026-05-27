"""Full-pipeline graph with Critic reflection loop (v3.0).

Graph shape:

    START ──> data ─────┐
        └──> sentiment ─┴──> manager ──> critic ──┐
                                  ↑                │ needs_revision
                                  └────────────────┘ (≤ MAX_REVISION_CYCLES)
                                                   │
                                                  END  (approved OR cycles exhausted)

`data` and `sentiment` execute concurrently; `manager` waits for both.
After `manager` drafts a synthesis, `critic` audits it. If the verdict is
`needs_revision` and the cycle cap has not been reached, the pipeline routes
back to `manager` with the Critic's revision instruction prepended to the
prompt. Otherwise it exits.

Public entry point: `run_full_analysis(ticker) -> FinalReport`.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.agents.critic_agent import MAX_REVISION_CYCLES, run_critic_agent
from app.agents.data_agent import run_data_agent
from app.agents.manager_agent import run_manager_agent
from app.agents.sentiment_agent import NoArticlesFoundError, run_sentiment_agent
from app.models.agents import DataAgentReport
from app.models.critic import CritiqueReport, CritiqueVerdict
from app.models.manager import FinalReport
from app.models.sentiment import Sentiment, SentimentAgentReport

log = logging.getLogger(__name__)


class _PipelineState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    data: DataAgentReport | None = None
    sentiment: SentimentAgentReport | None = None
    financial_metrics: dict = {}
    news_sentiment: dict = {}
    final: FinalReport | None = None
    critique: CritiqueReport | None = None
    revision_round: int = 1


# --- Nodes -------------------------------------------------------------------


def _data_node(state: _PipelineState) -> dict:
    log.info("pipeline: data node for %s", state.ticker)
    report = run_data_agent(state.ticker)
    return {"data": report, "financial_metrics": report.financial_metrics}


def _sentiment_node(state: _PipelineState) -> dict:
    log.info("pipeline: sentiment node for %s", state.ticker)
    try:
        report = run_sentiment_agent(state.ticker)
    except NoArticlesFoundError:
        log.warning("pipeline: no articles found for %s — using zero-news sentinel", state.ticker)
        report = SentimentAgentReport(
            ticker=state.ticker,
            query="N/A",
            articles_analyzed=0,
            overall_sentiment=Sentiment.NEUTRAL,
            overall_confidence=0.0,
            classified=[],
            is_zero_news=True,
        )
    return {"sentiment": report, "news_sentiment": report.news_sentiment}


def _manager_node(state: _PipelineState) -> dict:
    if state.data is None or state.sentiment is None:
        raise RuntimeError(
            "manager node reached without both inputs: "
            f"data={state.data is not None}, sentiment={state.sentiment is not None}"
        )
    revision_instruction = (
        state.critique.critique_result.revision_instruction
        if state.critique is not None else None
    )
    log.info("pipeline: manager node for %s (round %d)", state.ticker, state.revision_round)
    return {"final": run_manager_agent(state.data, state.sentiment, revision_instruction)}


def _critic_node(state: _PipelineState) -> dict:
    log.info("pipeline: critic node for %s (round %d)", state.ticker, state.revision_round)
    critique = run_critic_agent(
        state.final, state.data, state.sentiment, state.revision_round
    )
    log.info(
        "pipeline: critic verdict=%s confidence=%.2f issues=%d",
        critique.critique_result.verdict.value,
        critique.critique_result.synthesis_confidence,
        len(critique.critique_result.issues),
    )
    # Increment revision_round so the routing condition and next manager call
    # see the updated count.
    return {"critique": critique, "revision_round": state.revision_round + 1}


# --- Routing -----------------------------------------------------------------


def _should_revise(state: _PipelineState) -> str:
    """Route back to manager for revision, or exit.

    After the critic node runs, `revision_round` has already been incremented.
    We loop only if: (a) verdict is needs_revision AND (b) the new round is
    still within the cap (≤ MAX_REVISION_CYCLES).
    """
    if (
        state.critique is not None
        and state.critique.critique_result.verdict == CritiqueVerdict.NEEDS_REVISION
        and state.revision_round <= MAX_REVISION_CYCLES
    ):
        log.info(
            "pipeline: routing to revision round %d/%d",
            state.revision_round, MAX_REVISION_CYCLES,
        )
        return "manager"
    log.info("pipeline: synthesis finalised — routing to END")
    return END


# --- Graph -------------------------------------------------------------------


def _build_graph():
    graph: StateGraph = StateGraph(_PipelineState)

    graph.add_node("data", _data_node)
    graph.add_node("sentiment", _sentiment_node)
    graph.add_node("manager", _manager_node)
    graph.add_node("critic", _critic_node)

    # data + sentiment run in parallel, both feed into manager
    graph.add_edge(START, "data")
    graph.add_edge(START, "sentiment")
    graph.add_edge("data", "manager")
    graph.add_edge("sentiment", "manager")

    # manager always goes to critic for review
    graph.add_edge("manager", "critic")

    # critic routes to manager (revision) or END (approved / cap reached)
    graph.add_conditional_edges("critic", _should_revise)

    return graph.compile()


_compiled_graph = _build_graph()


def run_full_analysis(ticker: str) -> FinalReport:
    """Run the full pipeline with Critic reflection loop. Returns the final `FinalReport`."""
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("ticker must be non-empty")
    result = _compiled_graph.invoke({"ticker": normalized})
    final = result["final"] if isinstance(result, dict) else result.final
    if final is None:
        raise RuntimeError("Pipeline finished with no FinalReport in state")
    return final
