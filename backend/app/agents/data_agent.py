"""Data Agent — wraps the Alpha Vantage service inside a LangGraph node.

Single node for now (only one agent). The graph structure scaffolds the
seams that Sentiment and Manager agents will plug into later. No LLM
calls in this step — pure data fetching + Pydantic validation.

Public entry point: `run_data_agent(ticker) -> DataAgentReport`.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.models.agents import DataAgentReport
from app.models.financial import CompanyOverview, StockQuote
from app.services.alpha_vantage import (
    fetch_company_overview,
    fetch_global_quote,
)
from app.tools.financial_metrics import get_financial_metrics

log = logging.getLogger(__name__)


class _DataAgentState(BaseModel):
    """Internal LangGraph state for the Data Agent.

    Fields default to `None` so partial-progress states stay typed.
    Pydantic validation runs on every transition, satisfying the
    architecture's strict-validation-between-steps rule.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    quote: StockQuote | None = None
    overview: CompanyOverview | None = None


def _fetch_node(state: _DataAgentState) -> dict:
    """The one node — fetch quote + overview through the protected service.

    Returns a delta dict that LangGraph merges into state.
    Exceptions (typed `DataFetchError` subclasses) propagate to the caller
    so existing HTTP error mapping in `routers/quote.py` still works once
    we expose this via FastAPI.
    """
    ticker = state.ticker
    log.info("data_agent: fetching ticker=%s", ticker)
    quote = fetch_global_quote(ticker)
    overview = fetch_company_overview(ticker)
    return {"quote": quote, "overview": overview}


def _build_graph():
    graph: StateGraph = StateGraph(_DataAgentState)
    graph.add_node("fetch", _fetch_node)
    graph.add_edge(START, "fetch")
    graph.add_edge("fetch", END)
    return graph.compile()


# Compile once at import; reuse across calls.
_compiled_graph = _build_graph()


def run_data_agent(ticker: str) -> DataAgentReport:
    """Invoke the Data Agent graph for a single ticker.

    Raises any of the typed `DataFetchError` subclasses on upstream failure.
    """
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("ticker must be non-empty")

    result = _compiled_graph.invoke({"ticker": normalized})
    # LangGraph 1.x returns the final state as a dict (or a model, depending
    # on schema). Handle both for forward-compat.
    quote = result["quote"] if isinstance(result, dict) else result.quote
    overview = result["overview"] if isinstance(result, dict) else result.overview

    if quote is None or overview is None:
        raise RuntimeError(
            f"Data Agent finished with incomplete state for {normalized!r}: "
            f"quote={quote is not None}, overview={overview is not None}"
        )

    try:
        metrics_dict: dict = get_financial_metrics.run(normalized)
    except Exception as exc:
        log.warning("data_agent: FinancialMetricsTool failed for %s: %s", normalized, exc)
        metrics_dict = {}

    return DataAgentReport(
        ticker=normalized,
        quote=quote,
        overview=overview,
        financial_metrics=metrics_dict,
    )
