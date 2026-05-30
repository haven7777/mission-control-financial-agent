"""Market data service.

Primary source: Financial Modeling Prep (FMP) — works reliably from cloud IPs.
Fallback: yfinance — used when FMP key is absent (local dev without a key).

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
def _fmp_key() -> str | None:
    from app.config import get_settings
    return get_settings().fmp_api_key or None


# --- FMP backend --------------------------------------------------------------


def _fetch_fmp_raw(ticker: str) -> dict[str, Any]:
    """Fetch combined quote + profile from FMP and normalize to yfinance-like dict."""
    key = _fmp_key()
    if not key:
        raise DataFetchError("FMP_API_KEY not configured")

    base = "https://financialmodelingprep.com/api/v3"
    try:
        with httpx.Client(timeout=15) as client:
            q_resp = client.get(f"{base}/quote/{ticker}", params={"apikey": key})
            p_resp = client.get(f"{base}/profile/{ticker}", params={"apikey": key})
    except httpx.TimeoutException as exc:
        raise TimeoutFetchError(f"FMP timed out for {ticker}") from exc
    except Exception as exc:
        raise DataFetchError(f"FMP request failed for {ticker}: {exc}") from exc

    if q_resp.status_code == 429 or p_resp.status_code == 429:
        raise RateLimitedError(f"FMP rate limit hit for {ticker}")
    if not q_resp.is_success or not p_resp.is_success:
        raise HTTPFetchError(q_resp.status_code, q_resp.text[:200])

    quote_list = q_resp.json()
    profile_list = p_resp.json()

    if not quote_list or not isinstance(quote_list, list):
        raise InvalidTickerError(ticker)

    q = quote_list[0]
    p = profile_list[0] if profile_list and isinstance(profile_list, list) else {}

    # Normalize to yfinance .info shape so the rest of the code is unchanged
    return {
        "symbol": q.get("symbol", ticker),
        "currentPrice": q.get("price"),
        "previousClose": q.get("previousClose"),
        "open": q.get("open"),
        "dayHigh": q.get("dayHigh"),
        "dayLow": q.get("dayLow"),
        "volume": q.get("volume"),
        "regularMarketTime": q.get("timestamp"),
        # company overview fields
        "longName": p.get("companyName") or q.get("name"),
        "shortName": q.get("name"),
        "quoteType": "EQUITY",
        "longBusinessSummary": p.get("description") or "",
        "exchange": p.get("exchangeShortName") or q.get("exchange") or "",
        "currency": p.get("currency") or "USD",
        "country": p.get("country") or "",
        "sector": p.get("sector") or "",
        "industry": p.get("industry") or "",
        "marketCap": q.get("marketCap"),
        "trailingPE": q.get("pe"),
        "trailingEps": q.get("eps"),
        "dividendYield": p.get("lastDiv"),
        "beta": p.get("beta"),
        "fiftyTwoWeekHigh": q.get("yearHigh"),
        "fiftyTwoWeekLow": q.get("yearLow"),
        "targetMeanPrice": p.get("dcf"),
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
    """Return a yfinance-shaped info dict, using cache and FMP-first strategy."""
    cached = _info_cache.get(ticker)
    if cached is not None:
        log.info("Cache hit: info %s", ticker)
        return cached

    if _fmp_key():
        log.info("Fetching FMP data: %s", ticker)
        raw = _fetch_fmp_raw(ticker)
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
