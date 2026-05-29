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
import time
from datetime import datetime, timezone
from typing import Any, Iterator

# Hard upper bound per phase (data/sentiment/filings/transcript and debate).
# Set per audit (Fix 1): prevents one slow LLM from deadlocking the SSE stream.
_PHASE_TIMEOUT_SECS = 45
# Defensive cleanup join — threads should have already exited by this point.
_CLEANUP_JOIN_SECS = 5

from app.agents.delta_refresh import run_delta_refresh
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
from app.models.critic import CritiqueVerdict
from app.models.debate import BearCase, BullCase
from app.models.filings import FilingsContext
from app.models.manager import FinalReport
from app.models.sentiment import Sentiment, SentimentAgentReport
from app.services.report_cache import get_cached_report, store_report

log = logging.getLogger(__name__)


def _progress(stage: str, message: str) -> dict:
    return {"event": "progress", "data": {"stage": stage, "message": message}}


def _stream_error(message: str) -> dict:
    return {"event": "stream_error", "data": {"message": message}}


def run_full_analysis_stream(ticker: str) -> Iterator[dict]:
    """Yield progress events then the final report as SSE-ready dicts."""
    normalized = ticker.strip().upper()

    # ── Cache check ───────────────────────────────────────────────────────────
    cached = get_cached_report(normalized)
    if cached is not None:
        age_minutes = int(
            (datetime.now(timezone.utc) - cached.generated_at).total_seconds() / 60
        )
        yield _progress("cache_hit", f"Cache hit from {age_minutes}m ago — refreshing live data…")
        yield _progress("delta_refreshing", "Fetching live price and scanning recent news…")

        refreshed_holder: list[FinalReport] = []

        def _do_delta() -> None:
            try:
                refreshed_holder.append(run_delta_refresh(cached))
            except Exception:
                log.exception("pipeline_stream: delta refresh failed ticker=%s", normalized)

        _delta_thread = threading.Thread(target=_do_delta, daemon=True)
        _delta_thread.start()
        _delta_thread.join(timeout=25)

        if refreshed_holder:
            refreshed = refreshed_holder[0]
            n_new = refreshed.sentiment_snapshot.articles_analyzed
            old_n = cached.sentiment_snapshot.articles_analyzed
            if n_new != old_n:
                yield _progress(
                    "delta_complete",
                    f"Live price refreshed — {n_new} recent article{'s' if n_new != 1 else ''} found",
                )
            else:
                yield _progress("delta_complete", "Live price refreshed — no new developments found")
        else:
            refreshed = cached
            yield _progress("delta_complete", "Delta refresh unavailable — serving cached analysis")

        yield {"event": "result", "data": refreshed.model_dump(mode="json")}

        try:
            store_report(refreshed)
        except Exception:
            log.exception("pipeline_stream: failed to update cache after delta refresh ticker=%s", normalized)
        return

    yield _progress("cache_miss", "No recent cache — running full analysis…")

    # ── Phase 1: Data + Sentiment + Filings in parallel ──────────────────────

    result_q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def _run_data() -> None:
        try:
            result_q.put(("data_ok", run_data_agent(normalized)))
        except Exception as exc:
            log.exception("pipeline_stream: data agent failed ticker=%s", normalized)
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
        except Exception as exc:
            log.exception("pipeline_stream: sentiment agent failed ticker=%s", normalized)
            result_q.put(("sentiment_err", exc))

    def _run_filings() -> None:
        try:
            result_q.put(("filings_ok", run_filings_agent(normalized)))
        except Exception as exc:
            log.exception("pipeline_stream: filings agent failed ticker=%s", normalized)
            result_q.put(("filings_err", exc))

    def _run_transcript() -> None:
        try:
            result_q.put(("transcript_ok", run_transcript_agent(normalized)))
        except Exception as exc:
            log.exception("pipeline_stream: transcript agent failed ticker=%s", normalized)
            result_q.put(("transcript_err", exc))

    yield _progress("started", f"Starting analysis for {normalized}…")
    yield _progress("filings_fetching", "Retrieving SEC filing from EDGAR…")
    yield _progress("transcript_fetching", "Fetching earnings call transcript from FMP…")

    data_thread = threading.Thread(target=_run_data, daemon=True)
    sentiment_thread = threading.Thread(target=_run_sentiment, daemon=True)
    filings_thread = threading.Thread(target=_run_filings, daemon=True)
    transcript_thread = threading.Thread(target=_run_transcript, daemon=True)
    data_thread.start()
    sentiment_thread.start()
    filings_thread.start()
    transcript_thread.start()

    data_report: DataAgentReport | None = None
    sentiment_report: SentimentAgentReport | None = None
    filings_context: FilingsContext | None = None
    transcript_context: TranscriptContext | None = None
    remaining = 4
    phase_deadline = time.monotonic() + _PHASE_TIMEOUT_SECS

    while remaining:
        budget = phase_deadline - time.monotonic()
        if budget <= 0:
            log.critical(
                "pipeline_stream: phase 1 exceeded %ds ticker=%s missing=%d data=%s sentiment=%s filings=%s transcript=%s",
                _PHASE_TIMEOUT_SECS, normalized, remaining,
                data_report is not None, sentiment_report is not None,
                filings_context is not None, transcript_context is not None,
            )
            if data_report is None or sentiment_report is None:
                yield _stream_error("Analysis timed out fetching market data or sentiment")
                return
            # filings/transcript degrade silently to empty contexts
            if filings_context is None:
                filings_context = FilingsContext(ticker=normalized, form_type="10-K", chunks=[], is_empty=True)
                yield _progress("filings_unavailable", "SEC filing timed out — continuing without filing context")
            if transcript_context is None:
                transcript_context = TranscriptContext(ticker=normalized, is_empty=True)
                yield _progress("transcript_unavailable", "Transcript timed out — continuing without transcript context")
            break

        try:
            tag, value = result_q.get(timeout=budget)
        except queue.Empty:
            continue  # next loop iteration will hit the deadline check

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

        elif tag == "filings_ok":
            filings_context = value
            remaining -= 1
            if value.is_empty:
                yield _progress(
                    "filings_unavailable",
                    "No SEC filing found — continuing without filing context",
                )
            else:
                n = len(value.chunks)
                yield _progress(
                    "filings_complete",
                    f"SEC {value.form_type} analyzed — {n} relevant excerpt{'s' if n != 1 else ''} retrieved",
                )

        elif tag in ("data_err", "sentiment_err"):
            log.warning("pipeline_stream: %s failed: %s", tag, value)
            yield _stream_error(str(value))
            # Defensive cleanup — daemon threads die with the process anyway.
            data_thread.join(timeout=_CLEANUP_JOIN_SECS)
            sentiment_thread.join(timeout=_CLEANUP_JOIN_SECS)
            filings_thread.join(timeout=_CLEANUP_JOIN_SECS)
            transcript_thread.join(timeout=_CLEANUP_JOIN_SECS)
            return

        elif tag == "filings_err":
            log.warning("pipeline_stream: filings_err — %s", value)
            filings_context = FilingsContext(ticker=normalized, form_type="10-K", chunks=[], is_empty=True)
            remaining -= 1
            yield _progress("filings_unavailable", "SEC filing retrieval failed — continuing without filing context")

        elif tag == "transcript_ok":
            transcript_context = value
            remaining -= 1
            if value.is_empty:
                yield _progress(
                    "transcript_unavailable",
                    "No earnings call transcript available — continuing without transcript context",
                )
            else:
                n = len(value.dodged_questions)
                yield _progress(
                    "transcript_complete",
                    f"Q{value.quarter} {value.year} call analyzed"
                    + (f" — {n} dodged question{'s' if n != 1 else ''} detected" if n else ""),
                )

        elif tag == "transcript_err":
            log.warning("pipeline_stream: transcript_err — %s", value)
            transcript_context = TranscriptContext(ticker=normalized, is_empty=True)
            remaining -= 1
            yield _progress(
                "transcript_unavailable",
                "Transcript retrieval failed — continuing without transcript context",
            )

    data_thread.join(timeout=_CLEANUP_JOIN_SECS)
    sentiment_thread.join(timeout=_CLEANUP_JOIN_SECS)
    filings_thread.join(timeout=_CLEANUP_JOIN_SECS)
    transcript_thread.join(timeout=_CLEANUP_JOIN_SECS)

    # ── Phase 1.5: Bull vs. Bear debate (parallel) ────────────────────────────
    yield _progress("debating", "Bull analyst vs. Bear analyst debating the stock…")

    debate_q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def _run_bull_debate() -> None:
        try:
            debate_q.put(("bull_ok", run_bull_agent(data_report, sentiment_report)))  # type: ignore[arg-type]
        except Exception as exc:
            log.exception("pipeline_stream: bull debate failed ticker=%s", normalized)
            debate_q.put(("bull_err", exc))

    def _run_bear_debate() -> None:
        try:
            debate_q.put(("bear_ok", run_bear_agent(data_report, sentiment_report)))  # type: ignore[arg-type]
        except Exception as exc:
            log.exception("pipeline_stream: bear debate failed ticker=%s", normalized)
            debate_q.put(("bear_err", exc))

    bull_t = threading.Thread(target=_run_bull_debate, daemon=True)
    bear_t = threading.Thread(target=_run_bear_debate, daemon=True)
    bull_t.start()
    bear_t.start()

    bull_case: BullCase | None = None
    bear_case: BearCase | None = None

    debate_deadline = time.monotonic() + _PHASE_TIMEOUT_SECS
    debate_collected = 0
    while debate_collected < 2:
        budget = debate_deadline - time.monotonic()
        if budget <= 0:
            log.critical(
                "pipeline_stream: debate exceeded %ds ticker=%s bull=%s bear=%s — degrading without debate",
                _PHASE_TIMEOUT_SECS, normalized,
                bull_case is not None, bear_case is not None,
            )
            # Graceful degradation: manager handles bull_case/bear_case being None.
            break
        try:
            tag, value = debate_q.get(timeout=budget)
        except queue.Empty:
            continue
        debate_collected += 1
        if tag == "bull_ok":
            bull_case = value
        elif tag == "bear_ok":
            bear_case = value
        else:
            log.warning("pipeline_stream: %s failed: %s", tag, value)

    bull_t.join(timeout=_CLEANUP_JOIN_SECS)
    bear_t.join(timeout=_CLEANUP_JOIN_SECS)

    if bull_case and bear_case:
        yield _progress("debate_complete", "Bull vs. Bear debate complete — synthesizing final view…")
    else:
        yield _progress(
            "debate_skipped",
            "Debate agents unavailable — proceeding with direct synthesis",
        )

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
                data_report,       # type: ignore[arg-type]
                sentiment_report,  # type: ignore[arg-type]
                revision_instruction,
                bull_case=bull_case,
                bear_case=bear_case,
                filings_context=filings_context,
                transcript_context=transcript_context,
                is_deep_mode=True,
            )
        except Exception as exc:
            log.exception("pipeline_stream: manager failed ticker=%s round=%d", normalized, revision_round)
            yield _stream_error(str(exc))
            return

        # Critic
        yield _progress("critiquing", f"Critic auditing synthesis{round_suffix}…")

        try:
            critique = run_critic_agent(
                final, data_report, sentiment_report, revision_round  # type: ignore[arg-type]
            )
            cr = critique.critique_result
        except Exception:
            log.exception("pipeline_stream: critic failed ticker=%s round=%d", normalized, revision_round)
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

    # Store in Supabase after the stream completes (non-fatal — never blocks the client)
    try:
        store_report(final)
    except Exception:
        log.exception("pipeline_stream: failed to cache report ticker=%s", normalized)
