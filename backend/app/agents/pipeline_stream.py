"""Streaming pipeline with Critic reflection loop (v3.0).

Yields SSE-ready event dicts in order:

    progress  started           — analysis kicked off
    progress  data_complete     — yfinance quote + overview ready
    progress  sentiment_complete — news articles classified
    progress  synthesizing      — Manager drafting (each round)
    progress  critiquing        — Critic auditing (each round)
    progress  revising          — Critic requested a revision (with short instruction)
    progress  approved          — Critic approved (or cycle cap reached)
    result    <FinalReport>     — complete report payload

On any agent failure a single stream_error event is yielded and the
generator returns — it never raises.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Iterator

from app.agents.critic_agent import MAX_REVISION_CYCLES, run_critic_agent
from app.agents.data_agent import run_data_agent
from app.agents.manager_agent import run_manager_agent
from app.agents.sentiment_agent import NoArticlesFoundError, run_sentiment_agent
from app.models.agents import DataAgentReport
from app.models.critic import CritiqueVerdict
from app.models.manager import FinalReport
from app.models.sentiment import Sentiment, SentimentAgentReport

log = logging.getLogger(__name__)


def _progress(stage: str, message: str) -> dict:
    return {"event": "progress", "data": {"stage": stage, "message": message}}


def _stream_error(message: str) -> dict:
    return {"event": "stream_error", "data": {"message": message}}


def run_full_analysis_stream(ticker: str) -> Iterator[dict]:
    """Yield progress events then the final report as SSE-ready dicts."""
    normalized = ticker.strip().upper()

    # ── Phase 1: Data + Sentiment in parallel ─────────────────────────────────

    result_q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def _run_data() -> None:
        try:
            result_q.put(("data_ok", run_data_agent(normalized)))
        except Exception as exc:  # noqa: BLE001
            result_q.put(("data_err", exc))

    def _run_sentiment() -> None:
        try:
            result_q.put(("sentiment_ok", run_sentiment_agent(normalized)))
        except NoArticlesFoundError:
            empty = SentimentAgentReport(
                ticker=normalized,
                query="N/A",
                articles_analyzed=0,
                overall_sentiment=Sentiment.NEUTRAL,
                overall_confidence=0.0,
                classified=[],
                is_zero_news=True,
            )
            result_q.put(("sentiment_ok", empty))
        except Exception as exc:  # noqa: BLE001
            result_q.put(("sentiment_err", exc))

    yield _progress("started", f"Starting analysis for {normalized}…")

    data_thread = threading.Thread(target=_run_data, daemon=True)
    sentiment_thread = threading.Thread(target=_run_sentiment, daemon=True)
    data_thread.start()
    sentiment_thread.start()

    data_report: DataAgentReport | None = None
    sentiment_report: SentimentAgentReport | None = None
    remaining = 2

    while remaining:
        tag, value = result_q.get()

        if tag == "data_ok":
            data_report = value
            remaining -= 1
            yield _progress("data_complete", "Price & fundamentals ready")

        elif tag == "sentiment_ok":
            sentiment_report = value
            remaining -= 1
            if value.is_zero_news:
                yield _progress(
                    "sentiment_unavailable",
                    "No news articles found — continuing with fundamentals-only analysis",
                )
            else:
                n = value.articles_analyzed
                yield _progress(
                    "sentiment_complete",
                    f"Analyzed {n} news article{'s' if n != 1 else ''}",
                )

        elif tag in ("data_err", "sentiment_err"):
            log.warning("pipeline_stream: %s failed: %s", tag, value)
            yield _stream_error(str(value))
            data_thread.join()
            sentiment_thread.join()
            return

    data_thread.join()
    sentiment_thread.join()

    # ── Phase 2: Manager → Critic reflection loop ─────────────────────────────
    # Runs at most MAX_REVISION_CYCLES times. On each iteration:
    #   manager synthesises → critic audits → approved → done
    #                                       → needs_revision (if rounds remain) → loop

    revision_instruction: str | None = None
    final: FinalReport | None = None

    for revision_round in range(1, MAX_REVISION_CYCLES + 1):
        is_last = revision_round == MAX_REVISION_CYCLES

        # Manager
        round_suffix = f" (revision {revision_round - 1})" if revision_round > 1 else ""
        yield _progress("synthesizing", f"Synthesizing report{round_suffix}…")

        try:
            final = run_manager_agent(
                data_report,  # type: ignore[arg-type]
                sentiment_report,  # type: ignore[arg-type]
                revision_instruction,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("pipeline_stream: manager failed (round %d): %s", revision_round, exc)
            yield _stream_error(str(exc))
            return

        # Critic
        yield _progress("critiquing", f"Critic auditing synthesis{round_suffix}…")

        try:
            critique = run_critic_agent(
                final, data_report, sentiment_report, revision_round  # type: ignore[arg-type]
            )
            cr = critique.critique_result
        except Exception as exc:  # noqa: BLE001
            log.warning("pipeline_stream: critic failed (round %d): %s", revision_round, exc)
            # Critic failure is non-fatal: surface the Manager's last draft.
            break

        if cr.verdict == CritiqueVerdict.APPROVED or is_last:
            label = (
                f"Max revisions reached — confidence {cr.synthesis_confidence:.0%}"
                if is_last and cr.verdict == CritiqueVerdict.NEEDS_REVISION
                else f"Synthesis approved — confidence {cr.synthesis_confidence:.0%}, "
                     f"{len(cr.issues)} issue(s) noted"
            )
            yield _progress("approved", label)
            break

        # needs_revision with rounds remaining
        short_instr = (cr.revision_instruction or "")[:120]
        yield _progress(
            "revising",
            f"Revision {revision_round}/{MAX_REVISION_CYCLES - 1}: {short_instr}…",
        )
        revision_instruction = cr.revision_instruction

    if final is None:
        yield _stream_error("Pipeline produced no report")
        return

    yield {"event": "result", "data": final.model_dump(mode="json")}
