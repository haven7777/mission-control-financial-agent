"""GET /api/analyze/{ticker} — full Data + Sentiment + Manager pipeline.

Error → HTTP mapping:
    InvalidTickerError / NoArticlesFoundError  -> 404
    MissingNewsAPIKey / MissingLLMKey          -> 500  (server misconfigured)
    DataFetchError / NewsFetchError variants   -> 503
    Anything else                              -> 500
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException, Path

from app.agents.pipeline import run_full_analysis
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

router = APIRouter(prefix="/api", tags=["analyze"])
log = logging.getLogger(__name__)

_TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-]{1,10}$")


@router.get(
    "/analyze/{ticker}",
    response_model=FinalReport,
    response_model_by_alias=False,
)
def analyze(
    ticker: str = Path(min_length=1, max_length=10, examples=["IBM"]),
) -> FinalReport:
    normalized = ticker.upper()
    if not _TICKER_PATTERN.match(normalized):
        raise HTTPException(status_code=422, detail=f"Invalid ticker format: {ticker!r}")

    try:
        return run_full_analysis(normalized)
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
