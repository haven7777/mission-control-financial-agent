"""Full-pipeline graph with Critic reflection loop (v3.0).

Graph shape:

    START ──> data ──────┐
        ├──> sentiment ──┼──> debate ──> manager ──> critic ──┐
        └──> filings ────┘                         ↑           │ needs_revision
                                                   └───────────┘ (≤ MAX_REVISION_CYCLES)
                                                               │
                                                              END  (approved OR cycles exhausted)

`data`, `sentiment`, and `filings` execute concurrently; all three feed into `debate`.
`debate` runs Bull and Bear agents concurrently, then feeds into `manager`.
After `manager` drafts a synthesis, `critic` audits it. If the verdict is
`needs_revision` and the cycle cap has not been reached, the pipeline routes
back to `manager` with the Critic's revision instruction prepended to the
prompt. Otherwise it exits.

Public entry point: `run_full_analysis(ticker) -> FinalReport`.
"""

from __future__ import annotations

import logging
import queue
import threading

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.agents.bear_agent import run_bear_agent
from app.agents.bull_agent import run_bull_agent
from app.agents.critic_agent import MAX_REVISION_CYCLES, run_critic_agent
from app.agents.data_agent import run_data_agent
from app.agents.filings_agent import run_filings_agent
from app.agents.manager_agent import run_manager_agent
from app.agents.transcript_agent import run_transcript_agent
from app.models.transcript import TranscriptContext
from app.agents.sentiment_agent import NoArticlesFoundError, run_sentiment_agent
from app.models.agents import DataAgentReport
from app.models.critic import CritiqueReport, CritiqueVerdict
from app.models.debate import BearCase, BullCase
from app.models.filings import FilingsContext
from app.models.manager import FinalReport
from app.models.sentiment import Sentiment, SentimentAgentReport

# Hard upper bound on any single agent thread before we degrade or fail.
# Set per audit (Fix 1): prevents one slow LLM from deadlocking the pipeline.
_THREAD_TIMEOUT_SECS = 45

log = logging.getLogger(__name__)


class _PipelineState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    data: DataAgentReport | None = None
    sentiment: SentimentAgentReport | None = None
    filings_context: FilingsContext | None = None
    transcript_context: TranscriptContext | None = None
    financial_metrics: dict = {}
    news_sentiment: dict = {}
    bull_case: BullCase | None = None
    bear_case: BearCase | None = None
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


def _filings_node(state: _PipelineState) -> dict:
    log.info("pipeline: filings node for %s", state.ticker)
    ctx = run_filings_agent(state.ticker)
    return {"filings_context": ctx}


def _transcript_node(state: _PipelineState) -> dict:
    log.info("pipeline: transcript node for %s", state.ticker)
    ctx = run_transcript_agent(state.ticker)
    return {"transcript_context": ctx}


def _debate_node(state: _PipelineState) -> dict:
    """Run Bull and Bear agents concurrently; failures are non-fatal (logged, None returned)."""
    log.info("pipeline: debate node for %s", state.ticker)
    q: queue.Queue = queue.Queue()

    def _run_bull() -> None:
        try:
            q.put(("bull_ok", run_bull_agent(state.data, state.sentiment)))
        except Exception as exc:
            log.exception("pipeline: bull agent failed ticker=%s", state.ticker)
            q.put(("bull_err", exc))

    def _run_bear() -> None:
        try:
            q.put(("bear_ok", run_bear_agent(state.data, state.sentiment)))
        except Exception as exc:
            log.exception("pipeline: bear agent failed ticker=%s", state.ticker)
            q.put(("bear_err", exc))

    bull_t = threading.Thread(target=_run_bull, daemon=True)
    bear_t = threading.Thread(target=_run_bear, daemon=True)
    bull_t.start()
    bear_t.start()
    bull_t.join(timeout=_THREAD_TIMEOUT_SECS)
    bear_t.join(timeout=_THREAD_TIMEOUT_SECS)
    if bull_t.is_alive() or bear_t.is_alive():
        log.critical(
            "pipeline: debate threads exceeded %ds timeout ticker=%s bull_alive=%s bear_alive=%s — degrading without debate",
            _THREAD_TIMEOUT_SECS, state.ticker, bull_t.is_alive(), bear_t.is_alive(),
        )
        # Graceful degradation: synthesize without bull/bear (manager handles None).
        return {"bull_case": None, "bear_case": None}

    bull_case: BullCase | None = None
    bear_case: BearCase | None = None
    for _ in range(2):
        tag, value = q.get()
        if tag == "bull_ok":
            bull_case = value
        elif tag == "bear_ok":
            bear_case = value
        else:
            log.warning("pipeline: %s failed: %s", tag, value)

    return {"bull_case": bull_case, "bear_case": bear_case}


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
    return {"final": run_manager_agent(
        state.data,
        state.sentiment,
        revision_instruction,
        bull_case=state.bull_case,
        bear_case=state.bear_case,
        filings_context=state.filings_context,
        transcript_context=state.transcript_context,
    )}


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
    graph.add_node("filings", _filings_node)
    graph.add_node("transcript", _transcript_node)
    graph.add_node("debate", _debate_node)
    graph.add_node("manager", _manager_node)
    graph.add_node("critic", _critic_node)

    # data, sentiment, filings, and transcript run in parallel; all four feed into debate
    graph.add_edge(START, "data")
    graph.add_edge(START, "sentiment")
    graph.add_edge(START, "filings")
    graph.add_edge(START, "transcript")
    graph.add_edge("data", "debate")
    graph.add_edge("sentiment", "debate")
    graph.add_edge("filings", "debate")
    graph.add_edge("transcript", "debate")

    # debate feeds into manager
    graph.add_edge("debate", "manager")

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


def run_fast_analysis(ticker: str) -> FinalReport:
    """Lean pipeline: Data + Sentiment + Manager only. No filings/transcript/debate/critic.
    Target wall-clock time: 2-8s.
    """
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("ticker must be non-empty")

    data_report: DataAgentReport | None = None
    sentiment_report: SentimentAgentReport | None = None
    data_exc: BaseException | None = None
    sentiment_exc: BaseException | None = None

    def _fetch_data() -> None:
        nonlocal data_report, data_exc
        try:
            data_report = run_data_agent(normalized)
        except Exception as exc:
            log.exception("pipeline: fast data fetch failed ticker=%s", normalized)
            data_exc = exc

    def _fetch_sentiment() -> None:
        nonlocal sentiment_report, sentiment_exc
        try:
            sentiment_report = run_sentiment_agent(normalized)
        except NoArticlesFoundError:
            sentiment_report = SentimentAgentReport(
                ticker=normalized,
                query="N/A",
                articles_analyzed=0,
                overall_sentiment=Sentiment.NEUTRAL,
                overall_confidence=0.0,
                classified=[],
                is_zero_news=True,
            )
        except Exception as exc:
            log.exception("pipeline: fast sentiment fetch failed ticker=%s", normalized)
            sentiment_exc = exc

    t1 = threading.Thread(target=_fetch_data, daemon=True)
    t2 = threading.Thread(target=_fetch_sentiment, daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=_THREAD_TIMEOUT_SECS)
    t2.join(timeout=_THREAD_TIMEOUT_SECS)
    if t1.is_alive() or t2.is_alive():
        log.critical(
            "pipeline: fast pipeline exceeded %ds ticker=%s data_alive=%s sentiment_alive=%s",
            _THREAD_TIMEOUT_SECS, normalized, t1.is_alive(), t2.is_alive(),
        )
        raise RuntimeError("Fast pipeline: data or sentiment agent exceeded timeout")

    if data_exc:
        raise data_exc
    if sentiment_exc:
        raise sentiment_exc
    if data_report is None or sentiment_report is None:
        raise RuntimeError("Fast pipeline: data or sentiment agent timed out")

    return run_manager_agent(data_report, sentiment_report, is_deep_mode=False)
