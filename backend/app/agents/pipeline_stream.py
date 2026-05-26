"""Streaming variant of the full pipeline.

Runs Data + Sentiment agents concurrently via threads, then runs the Manager
agent once both complete.  Yields SSE-ready event dicts:

    {"event": "progress",      "data": {"stage": str, "message": str}}
    {"event": "result",        "data": FinalReport.model_dump(mode="json")}
    {"event": "stream_error",  "data": {"message": str}}

On agent failure a single "stream_error" dict is yielded and the generator
returns — it never raises.  The caller (SSE route) should close the stream
after receiving either "result" or "stream_error".
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Iterator

from app.agents.data_agent import run_data_agent
from app.agents.manager_agent import run_manager_agent
from app.agents.sentiment_agent import run_sentiment_agent
from app.models.agents import DataAgentReport
from app.models.manager import FinalReport
from app.models.sentiment import SentimentAgentReport

log = logging.getLogger(__name__)


def _progress(stage: str, message: str) -> dict:
    return {"event": "progress", "data": {"stage": stage, "message": message}}


def _stream_error(message: str) -> dict:
    return {"event": "stream_error", "data": {"message": message}}


def run_full_analysis_stream(ticker: str) -> Iterator[dict]:
    """Yield progress events then the final report as SSE-ready dicts."""
    normalized = ticker.strip().upper()

    result_q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def _run_data() -> None:
        try:
            result_q.put(("data_ok", run_data_agent(normalized)))
        except Exception as exc:  # noqa: BLE001
            result_q.put(("data_err", exc))

    def _run_sentiment() -> None:
        try:
            result_q.put(("sentiment_ok", run_sentiment_agent(normalized)))
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
            n = value.articles_analyzed
            remaining -= 1
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

    yield _progress("synthesizing", "Synthesizing report…")

    try:
        final: FinalReport = run_manager_agent(data_report, sentiment_report)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        log.warning("pipeline_stream: manager failed: %s", exc)
        yield _stream_error(str(exc))
        return

    yield {"event": "result", "data": final.model_dump(mode="json")}
