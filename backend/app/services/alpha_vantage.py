"""Market data service backed by yfinance (Yahoo Finance).

Public surface is identical to the former Alpha Vantage implementation so all
callers (data_agent, routers/quote, test patches) remain unchanged.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import yfinance as yf
from curl_cffi import requests as cf_requests

from app.models.financial import CompanyOverview, StockQuote
from app.services.cache import TTLCache

# Shared curl_cffi session that impersonates Chrome — bypasses Yahoo Finance's
# bot detection and "Invalid Crumb" errors that occur on cloud server IPs.
_yf_session = cf_requests.Session(impersonate="chrome")

# One yfinance .info call returns both quote and overview data.
# Cache the raw dict for 60 s so back-to-back calls (quote then overview in
# the same pipeline run) hit the network only once per ticker per minute.
_INFO_TTL_S = 60.0

_info_cache: TTLCache[dict[str, Any]] = TTLCache(_INFO_TTL_S)

log = logging.getLogger(__name__)


# --- Exception hierarchy (interface-compatible with former AV service) --------


class DataFetchError(Exception):
    """Base class for all market-data fetch failures."""


class TimeoutFetchError(DataFetchError):
    """Upstream request timed out."""


class HTTPFetchError(DataFetchError):
    def __init__(self, status_code: int, body_preview: str) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {body_preview!r}")


class MalformedResponseError(DataFetchError):
    """Response failed Pydantic validation or was unexpectedly shaped."""


class RateLimitedError(DataFetchError):
    """Upstream source is temporarily refusing requests."""


class InvalidTickerError(DataFetchError):
    """Ticker is unknown or returned an empty payload."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"Unknown or empty ticker: {ticker!r}")


# --- Internals ----------------------------------------------------------------


def _to_decimal(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return None


def _fetch_info_raw(ticker: str) -> dict[str, Any]:
    """Return the yfinance .info dict for *ticker*, using the cache when fresh."""
    cached = _info_cache.get(ticker)
    if cached is not None:
        log.info("Cache hit: info %s", ticker)
        return cached

    log.info("Fetching yfinance info: %s", ticker)
    try:
        raw: dict[str, Any] = yf.Ticker(ticker, session=_yf_session).info
    except Exception as exc:
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            raise TimeoutFetchError(f"yfinance timed out for {ticker}") from exc
        raise DataFetchError(f"yfinance fetch failed for {ticker}: {exc}") from exc

    # yfinance returns a near-empty dict (e.g. {"trailingPegRatio": None}) for
    # delisted or completely unknown tickers — detect before caching.
    if not raw or not raw.get("symbol"):
        raise InvalidTickerError(ticker)

    _info_cache.set(ticker, raw)
    return raw


def _trading_day(info: dict[str, Any]) -> date:
    ts = info.get("regularMarketTime")
    if ts:
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
        except (ValueError, OSError):
            pass
    return datetime.now(timezone.utc).date()


# --- Public API ---------------------------------------------------------------


def fetch_global_quote(ticker: str) -> StockQuote:
    key = ticker.upper()
    info = _fetch_info_raw(key)

    price = _to_decimal(info.get("currentPrice") or info.get("regularMarketPrice"))
    prev_close = _to_decimal(
        info.get("previousClose") or info.get("regularMarketPreviousClose")
    )

    if price is None or prev_close is None:
        raise InvalidTickerError(ticker)

    change = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else Decimal("0")

    try:
        return StockQuote(
            symbol=info.get("symbol", key),
            open_price=_to_decimal(info.get("open") or info.get("regularMarketOpen")) or Decimal("0"),
            high=_to_decimal(info.get("dayHigh") or info.get("regularMarketDayHigh")) or Decimal("0"),
            low=_to_decimal(info.get("dayLow") or info.get("regularMarketDayLow")) or Decimal("0"),
            price=price,
            volume=info.get("volume") or info.get("regularMarketVolume") or 0,
            latest_trading_day=_trading_day(info),
            previous_close=prev_close,
            change=change,
            change_percent=change_pct,
        )
    except Exception as exc:
        raise MalformedResponseError(f"StockQuote construction failed: {exc}") from exc


def fetch_company_overview(ticker: str) -> CompanyOverview:
    key = ticker.upper()
    info = _fetch_info_raw(key)

    try:
        return CompanyOverview(
            symbol=info.get("symbol", key),
            name=info.get("longName") or info.get("shortName") or key,
            asset_type=info.get("quoteType", "EQUITY"),
            description=info.get("longBusinessSummary") or "",
            exchange=info.get("exchange") or "",
            currency=info.get("currency") or "USD",
            country=info.get("country") or "",
            sector=info.get("sector") or "",
            industry=info.get("industry") or "",
            market_capitalization=info.get("marketCap"),
            pe_ratio=_to_decimal(info.get("trailingPE")),
            eps=_to_decimal(info.get("trailingEps")),
            dividend_yield=_to_decimal(info.get("dividendYield")),
            beta=_to_decimal(info.get("beta")),
            week_52_high=_to_decimal(info.get("fiftyTwoWeekHigh")),
            week_52_low=_to_decimal(info.get("fiftyTwoWeekLow")),
            analyst_target_price=_to_decimal(info.get("targetMeanPrice")),
        )
    except Exception as exc:
        raise MalformedResponseError(f"CompanyOverview construction failed: {exc}") from exc


def clear_caches() -> None:
    """Test/debug helper: drop all cached payloads."""
    _info_cache.clear()
