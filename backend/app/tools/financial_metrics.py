from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

import yfinance as yf
from langchain_core.tools import tool


class FinancialMetricsResult(TypedDict):
    ticker: str
    price: float | None
    pe_ratio: float | None
    market_cap: int | None
    week_52_high: float | None
    week_52_low: float | None
    next_earnings_date: str | None  # ISO-8601 date string e.g. "2024-08-01"
    eps: float | None
    beta: float | None


@tool
def get_financial_metrics(ticker: str) -> FinancialMetricsResult:
    """Fetch structured financial metrics for a stock ticker using yfinance.

    Returns P/E ratio, Market Cap, 52-week High/Low, next earnings date,
    EPS, and Beta. Missing fields are None.
    """
    t = yf.Ticker(ticker.strip().upper())
    info: dict = t.info or {}

    next_earnings: str | None = None
    try:
        earnings_df = t.earnings_dates
        if earnings_df is not None and not earnings_df.empty:
            now = datetime.now(timezone.utc)
            future = earnings_df[earnings_df.index > now]
            if not future.empty:
                # index is sorted descending; last row = nearest future date
                next_earnings = future.index[-1].date().isoformat()
    except Exception:
        pass

    def _float(val: object) -> float | None:
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    def _int(val: object) -> int | None:
        try:
            return int(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    return FinancialMetricsResult(
        ticker=ticker.strip().upper(),
        price=_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        pe_ratio=_float(info.get("trailingPE")),
        market_cap=_int(info.get("marketCap")),
        week_52_high=_float(info.get("fiftyTwoWeekHigh")),
        week_52_low=_float(info.get("fiftyTwoWeekLow")),
        next_earnings_date=next_earnings,
        eps=_float(info.get("trailingEps")),
        beta=_float(info.get("beta")),
    )
