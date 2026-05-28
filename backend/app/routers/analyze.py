"""GET /api/analyze/{ticker}        — full pipeline, single JSON response.
GET /api/analyze/{ticker}/stream   — same pipeline, SSE progress stream.

Error → HTTP mapping (sync endpoint):
    InvalidTickerError / NoArticlesFoundError  -> 404
    MissingNewsAPIKey / MissingLLMKey          -> 500  (server misconfigured)
    DataFetchError / NewsFetchError variants   -> 503
    Anything else                              -> 500

SSE endpoint yields events:
    event: progress      data: {"stage": str, "message": str}
    event: result        data: FinalReport JSON
    event: stream_error  data: {"message": str}
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import StreamingResponse

from app.services.master_code_auth import require_master_code

from app.agents.pipeline import run_full_analysis
from app.agents.pipeline_stream import run_full_analysis_stream
from app.services.limiter import limiter
from app.agents.sentiment_agent import (
    MissingLLMKey,
    NoArticlesFoundError,
)
from app.models.manager import FinalReport
from app.services.alpha_vantage import (
    DataFetchError,
    InvalidTickerError,
)
from app.services.tavily import MissingNewsAPIKey, NewsFetchError
from app.services.report_cache import get_cached_report, store_report

router = APIRouter(prefix="/api", tags=["analyze"])
log = logging.getLogger(__name__)

_TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-]{1,10}$")

_INJECTION_RE = re.compile(
    r"(ignore\s+(previous|all|prior)\s+instructions"
    r"|you\s+are\s+now\s+(a|an)"
    r"|forget\s+(all|everything|previous)"
    r"|jailbreak"
    r"|<\|.{0,50}\|>)",
    re.IGNORECASE | re.DOTALL,
)


def _check_injection(text: str) -> None:
    """Raise 422 if text contains prompt injection patterns (defense-in-depth)."""
    if _INJECTION_RE.search(text):
        raise HTTPException(
            status_code=422,
            detail="Input contains disallowed content.",
        )


@router.get(
    "/analyze/{ticker}",
    response_model=FinalReport,
    response_model_by_alias=False,
)
@limiter.limit("5/minute")
def analyze(
    request: Request,
    ticker: str = Path(min_length=1, max_length=10, examples=["IBM"]),
) -> FinalReport:
    normalized = ticker.upper()
    if not _TICKER_PATTERN.match(normalized):
        raise HTTPException(status_code=422, detail=f"Invalid ticker format: {ticker!r}")
    _check_injection(normalized)

    # Check cache first — returns None when Supabase is not configured or cache is cold
    cached = get_cached_report(normalized)
    if cached is not None:
        log.info("analyze: cache hit for %s", normalized)
        return cached

    try:
        report = run_full_analysis(normalized)
    except (InvalidTickerError, NoArticlesFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (MissingNewsAPIKey, MissingLLMKey) as exc:
        log.error("Server misconfigured: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Server misconfiguration ({type(exc).__name__}): {exc}",
        ) from exc
    except (DataFetchError, NewsFetchError) as exc:
        log.warning("Pipeline upstream failure for %s: %s: %s",
                    normalized, type(exc).__name__, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Upstream error ({type(exc).__name__}): {exc}",
        ) from exc

    # Store fresh report (non-fatal)
    try:
        store_report(report)
    except Exception as exc:  # noqa: BLE001
        log.warning("analyze: failed to cache report for %s: %s", normalized, exc)

    return report


def _sse_message(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get(
    "/analyze/{ticker}/stream",
    response_class=StreamingResponse,
    summary="Stream agent-progress events then the final report via SSE",
    dependencies=[Depends(require_master_code)],
)
@limiter.limit("5/minute")
def analyze_stream(
    request: Request,
    ticker: str = Path(min_length=1, max_length=10, examples=["IBM"]),
) -> StreamingResponse:
    normalized = ticker.upper()
    if not _TICKER_PATTERN.match(normalized):
        raise HTTPException(status_code=422, detail=f"Invalid ticker format: {ticker!r}")
    _check_injection(normalized)

    def _generate() -> Generator[str, None, None]:
        for event_dict in run_full_analysis_stream(normalized):
            yield _sse_message(event_dict["event"], event_dict["data"])

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
