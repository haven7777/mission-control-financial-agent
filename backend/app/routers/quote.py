"""GET /api/quote/{ticker} — thin pass-through over the Alpha Vantage service.

Error → HTTP mapping (per the architecture's resilience rules):
    InvalidTickerError  -> 404
    everything else     -> 503  (typed `DataFetchError` subclass surfaced in detail)
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException, Path

from app.models.financial import StockQuote
from app.services.alpha_vantage import (
    DataFetchError,
    InvalidTickerError,
    fetch_global_quote,
)

router = APIRouter(prefix="/api", tags=["quote"])
log = logging.getLogger(__name__)

# Cheap input guard: alphanumeric plus dot/dash, 1-10 chars. Anything plausibly
# tickerish gets passed through so the architecture's "graceful unknown ticker"
# rule (typed `InvalidTickerError` -> 404) gets a chance to fire.
_TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-]{1,10}$")


@router.get(
    "/quote/{ticker}",
    response_model=StockQuote,
    response_model_by_alias=False,  # emit snake_case, not raw Alpha Vantage keys
)
def get_quote(
    ticker: str = Path(min_length=1, max_length=10, examples=["IBM"]),
) -> StockQuote:
    normalized = ticker.upper()
    if not _TICKER_PATTERN.match(normalized):
        raise HTTPException(status_code=422, detail=f"Invalid ticker format: {ticker!r}")

    try:
        return fetch_global_quote(normalized)
    except InvalidTickerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataFetchError as exc:
        log.warning("Upstream fetch failed for %s: %s: %s",
                    normalized, type(exc).__name__, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Upstream data error ({type(exc).__name__}): {exc}",
        ) from exc
