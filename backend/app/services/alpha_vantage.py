"""Market data service.

Primary source: Twelve Data — works reliably from cloud IPs, free tier 800/day.
Fallback: yfinance — used when Twelve Data key is absent (local dev).

Public surface is identical to the former Alpha Vantage implementation so all
callers (data_agent, routers/quote, test patches) remain unchanged.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

import httpx
import yfinance as yf

from app.models.financial import CompanyOverview, StockQuote
from app.services.cache import TTLCache

_INFO_TTL_S = 60.0
_info_cache: TTLCache[dict[str, Any]] = TTLCache(_INFO_TTL_S)

log = logging.getLogger(__name__)


# --- Exception hierarchy ------------------------------------------------------


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


# --- Helpers ------------------------------------------------------------------


def _to_decimal(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return None


@lru_cache(maxsize=1)
def _td_key() -> str | None:
    from app.config import get_settings
    return get_settings().twelvedata_api_key or None


# --- Twelve Data backend ------------------------------------------------------

_TD_BASE = "https://api.twelvedata.com"


def _fetch_twelvedata_raw(ticker: str) -> dict[str, Any]:
    """Fetch quote + statistics from Twelve Data and normalize to yfinance-like dict."""
    key = _td_key()
    if not key:
        raise DataFetchError("TWELVEDATA_API_KEY not configured")

    try:
        with httpx.Client(timeout=15) as client:
            q_resp = client.get(
                f"{_TD_BASE}/quote",
                params={"symbol": ticker, "apikey": key},
            )
            s_resp = client.get(
                f"{_TD_BASE}/statistics",
                params={"symbol": ticker, "apikey": key},
            )
    except httpx.TimeoutException as exc:
        raise TimeoutFetchError(f"Twelve Data timed out for {ticker}") from exc
    except Exception as exc:
        raise DataFetchError(f"Twelve Data request failed for {ticker}: {exc}") from exc

    if q_resp.status_code == 429:
        raise RateLimitedError(f"Twelve Data rate limit hit for {ticker}")

    q = q_resp.json() if q_resp.content else {}

    # Twelve Data signals errors via HTTP 4xx or a 200 body with status=error
    if not q_resp.is_success or q.get("status") == "error" or q.get("code") == 404:
        # 404 = ticker not in Twelve Data — treat as unknown ticker, not a crash
        if q_resp.status_code == 404 or q.get("code") == 404:
            raise InvalidTickerError(ticker)
        if q_resp.status_code == 401 or q_resp.status_code == 403:
            raise DataFetchError(f"Twelve Data auth error: {q.get('message', q_resp.text[:100])}")
        msg = q.get("message", q_resp.text[:200])
        raise DataFetchError(f"Twelve Data error for {ticker}: {msg}")

    if not q.get("symbol"):
        raise InvalidTickerError(ticker)

    # Statistics are best-effort — not all tickers have them
    s = s_resp.json() if s_resp.is_success else {}
    stats = s.get("statistics", {})
    valuations = stats.get("valuations_metrics", {})
    financials = stats.get("financials", {})
    stock_stats = stats.get("stock_statistics", {})
    company_info = stats.get("company_information", {})
    fw = q.get("fifty_two_week") or {}

    return {
        "symbol": q.get("symbol", ticker),
        "currentPrice": q.get("close"),
        "previousClose": q.get("previous_close"),
        "open": q.get("open"),
        "dayHigh": q.get("high"),
        "dayLow": q.get("low"),
        "volume": q.get("volume"),
        "regularMarketTime": q.get("timestamp"),
        # company overview
        "longName": q.get("name"),
        "shortName": q.get("name"),
        "quoteType": "EQUITY",
        "longBusinessSummary": company_info.get("description") or "",
        "exchange": q.get("exchange") or "",
        "currency": q.get("currency") or "USD",
        "country": company_info.get("country") or "",
        "sector": company_info.get("sector") or "",
        "industry": company_info.get("industry") or "",
        "marketCap": stock_stats.get("market_capitalization"),
        "trailingPE": valuations.get("trailing_pe"),
        "trailingEps": financials.get("eps_ttm"),
        "dividendYield": financials.get("dividend_yield"),
        "beta": stock_stats.get("beta"),
        "fiftyTwoWeekHigh": fw.get("high"),
        "fiftyTwoWeekLow": fw.get("low"),
        "targetMeanPrice": None,
    }


# --- yfinance fallback --------------------------------------------------------


def _fetch_yf_raw(ticker: str) -> dict[str, Any]:
    log.info("Fetching yfinance info: %s", ticker)
    try:
        raw: dict[str, Any] = yf.Ticker(ticker).info
    except Exception as exc:
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            raise TimeoutFetchError(f"yfinance timed out for {ticker}") from exc
        raise DataFetchError(f"yfinance fetch failed for {ticker}: {exc}") from exc

    if not raw or not raw.get("symbol"):
        raise InvalidTickerError(ticker)
    return raw


# --- Unified entry point ------------------------------------------------------


def _fetch_info_raw(ticker: str) -> dict[str, Any]:
    """Return a yfinance-shaped info dict, using cache and Twelve Data-first strategy."""
    cached = _info_cache.get(ticker)
    if cached is not None:
        log.info("Cache hit: info %s", ticker)
        return cached

    if _td_key():
        log.info("Fetching Twelve Data: %s", ticker)
        raw = _fetch_twelvedata_raw(ticker)
    else:
        raw = _fetch_yf_raw(ticker)

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
