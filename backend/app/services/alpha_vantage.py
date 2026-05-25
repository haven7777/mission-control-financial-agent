"""Alpha Vantage data-fetch service.

All financial-data calls go through this module. Returns Pydantic-validated
models on success; raises a typed `DataFetchError` subclass otherwise.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.models.financial import CompanyOverview, StockQuote
from app.services.cache import TTLCache
from app.services.rate_limiter import MinIntervalRateLimiter

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
REQUEST_TIMEOUT_S = 10.0

# Upstream is documented at 1 req/sec burst + 25 req/day quota on the free tier.
# The throttle protects against the burst limit; the cache protects against the
# daily quota (and makes repeat hits on the same ticker effectively free).
# 1.2s leaves a small safety margin over Alpha Vantage's strict 1-req-per-second
# counting (network jitter / clock skew can otherwise push two requests inside
# the same server-side 1s window).
MIN_REQUEST_INTERVAL_S = 1.2
QUOTE_TTL_S = 60.0          # GLOBAL_QUOTE changes intraday; 1 min is a safe window
OVERVIEW_TTL_S = 86_400.0   # OVERVIEW (fundamentals) refreshes ~daily at most

_rate_limiter = MinIntervalRateLimiter(MIN_REQUEST_INTERVAL_S)
_quote_cache: TTLCache[StockQuote] = TTLCache(QUOTE_TTL_S)
_overview_cache: TTLCache[CompanyOverview] = TTLCache(OVERVIEW_TTL_S)

log = logging.getLogger(__name__)


# --- Exception hierarchy -----------------------------------------------------

class DataFetchError(Exception):
    """Base class for all Alpha Vantage fetch failures."""


class TimeoutFetchError(DataFetchError):
    """Upstream request exceeded the timeout budget."""


class HTTPFetchError(DataFetchError):
    """Non-2xx HTTP response from Alpha Vantage."""

    def __init__(self, status_code: int, body_preview: str) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {body_preview!r}")


class MalformedResponseError(DataFetchError):
    """Response was not valid JSON or failed Pydantic validation."""


class RateLimitedError(DataFetchError):
    """Alpha Vantage Note/Information envelope — quota, demo restriction, etc."""


class InvalidTickerError(DataFetchError):
    """Ticker is unknown or returned an empty payload."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"Unknown or empty ticker: {ticker!r}")


# --- Internals ---------------------------------------------------------------

def _resolve_api_key() -> str:
    key = get_settings().alpha_vantage_api_key or "demo"
    if key.lower() == "demo":
        log.warning("ALPHA_VANTAGE_API_KEY not configured; using public 'demo' key (IBM only).")
    return key


def _request(params: dict[str, str]) -> dict[str, Any]:
    _rate_limiter.wait()
    try:
        response = httpx.get(ALPHA_VANTAGE_URL, params=params, timeout=REQUEST_TIMEOUT_S)
    except httpx.TimeoutException as exc:
        raise TimeoutFetchError(
            f"Alpha Vantage timed out after {REQUEST_TIMEOUT_S}s"
        ) from exc
    except httpx.RequestError as exc:
        raise DataFetchError(f"Network error contacting Alpha Vantage: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPFetchError(response.status_code, response.text[:200])

    try:
        payload = response.json()
    except ValueError as exc:
        raise MalformedResponseError(f"Non-JSON response: {exc}") from exc

    if not isinstance(payload, dict):
        raise MalformedResponseError(
            f"Expected JSON object, got {type(payload).__name__}"
        )

    if "Error Message" in payload:
        raise InvalidTickerError(params.get("symbol", "<unknown>"))
    if "Note" in payload:
        raise RateLimitedError(str(payload["Note"]))
    if "Information" in payload:
        raise RateLimitedError(str(payload["Information"]))

    return payload


# --- Public API --------------------------------------------------------------

def fetch_global_quote(ticker: str) -> StockQuote:
    key = ticker.upper()
    cached = _quote_cache.get(key)
    if cached is not None:
        log.info("Cache hit: GLOBAL_QUOTE %s", key)
        return cached

    payload = _request({"function": "GLOBAL_QUOTE", "symbol": key, "apikey": _resolve_api_key()})
    raw = payload.get("Global Quote") or {}
    if not raw:
        raise InvalidTickerError(ticker)
    try:
        quote = StockQuote.model_validate(raw)
    except ValidationError as exc:
        raise MalformedResponseError(f"StockQuote validation failed: {exc}") from exc

    _quote_cache.set(key, quote)
    return quote


def fetch_company_overview(ticker: str) -> CompanyOverview:
    key = ticker.upper()
    cached = _overview_cache.get(key)
    if cached is not None:
        log.info("Cache hit: OVERVIEW %s", key)
        return cached

    payload = _request({"function": "OVERVIEW", "symbol": key, "apikey": _resolve_api_key()})
    if not payload.get("Symbol"):
        raise InvalidTickerError(ticker)
    try:
        overview = CompanyOverview.model_validate(payload)
    except ValidationError as exc:
        raise MalformedResponseError(f"CompanyOverview validation failed: {exc}") from exc

    _overview_cache.set(key, overview)
    return overview


def clear_caches() -> None:
    """Test/debug helper: drop all cached payloads."""
    _quote_cache.clear()
    _overview_cache.clear()
