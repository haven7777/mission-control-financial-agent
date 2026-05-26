"""Pydantic models for stock quote and company overview data.

Provider-agnostic: constructed with keyword arguments by the market-data
service. Decimal is used for prices and ratios to avoid float drift.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict

_ABSENT_SENTINELS = {"", "-", "None", "N/A", "none"}


def _coerce_absent_to_none(v: Any) -> Any:
    if isinstance(v, str) and v.strip() in _ABSENT_SENTINELS:
        return None
    return v


NullableDecimal = Annotated[Decimal | None, BeforeValidator(_coerce_absent_to_none)]
NullableInt = Annotated[int | None, BeforeValidator(_coerce_absent_to_none)]


class StockQuote(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    open_price: Decimal
    high: Decimal
    low: Decimal
    price: Decimal
    volume: int
    latest_trading_day: date
    previous_close: Decimal
    change: Decimal
    change_percent: Decimal


class CompanyOverview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    name: str
    asset_type: str
    description: str
    exchange: str
    currency: str
    country: str
    sector: str
    industry: str
    market_capitalization: NullableInt = None
    pe_ratio: NullableDecimal = None
    eps: NullableDecimal = None
    dividend_yield: NullableDecimal = None
    beta: NullableDecimal = None
    week_52_high: NullableDecimal = None
    week_52_low: NullableDecimal = None
    analyst_target_price: NullableDecimal = None
