"""Full-pipeline graph: Data + Sentiment (in parallel) → Manager.

LangGraph runs nodes whose incoming dependencies are satisfied; with the
graph shape::

    START ──> data ─────┐
        └──> sentiment ─┴──> manager ──> END

`data` and `sentiment` execute concurrently. `manager` waits until both
land before synthesizing. Net effect: end-to-end latency is roughly
max(data, sentiment) + manager, not their sum.

Public entry point: `run_full_analysis(ticker) -> FinalReport`.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.agents.data_agent import run_data_agent
from app.agents.manager_agent import run_manager_agent
from app.agents.sentiment_agent import run_sentiment_agent
from app.models.agents import DataAgentReport
from app.models.manager import FinalReport
from app.models.sentiment import SentimentAgentReport

log = logging.getLogger(__name__)


class _PipelineState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    data: DataAgentReport | None = None
    sentiment: SentimentAgentReport | None = None
    final: FinalReport | None = None


def _data_node(state: _PipelineState) -> dict:
    log.info("pipeline: data node for %s", state.ticker)
    return {"data": run_data_agent(state.ticker)}


def _sentiment_node(state: _PipelineState) -> dict:
    log.info("pipeline: sentiment node for %s", state.ticker)
    return {"sentiment": run_sentiment_agent(state.ticker)}


def _manager_node(state: _PipelineState) -> dict:
    if state.data is None or state.sentiment is None:
        raise RuntimeError(
            "manager node reached without both inputs: "
            f"data={state.data is not None}, sentiment={state.sentiment is not None}"
        )
    log.info("pipeline: manager node for %s", state.ticker)
    return {"final": run_manager_agent(state.data, state.sentiment)}


def _build_graph():
    graph: StateGraph = StateGraph(_PipelineState)
    graph.add_node("data", _data_node)
    graph.add_node("sentiment", _sentiment_node)
    graph.add_node("manager", _manager_node)
    graph.add_edge(START, "data")
    graph.add_edge(START, "sentiment")
    graph.add_edge("data", "manager")
    graph.add_edge("sentiment", "manager")
    graph.add_edge("manager", END)
    return graph.compile()


_compiled_graph = _build_graph()


def run_full_analysis(ticker: str) -> FinalReport:
    """Run Data + Sentiment in parallel, then Manager. Returns the FinalReport."""
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("ticker must be non-empty")
    result = _compiled_graph.invoke({"ticker": normalized})
    final = result["final"] if isinstance(result, dict) else result.final
    if final is None:
        raise RuntimeError("Pipeline finished with no FinalReport in state")
    return final
