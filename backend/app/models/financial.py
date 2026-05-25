"""Pydantic models for Alpha Vantage responses.

Field aliases preserve the original Alpha Vantage key names so a raw
response dict can be passed directly to `Model.model_validate(...)`.
Decimal is used for prices/ratios to avoid float drift on financial data.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

_ABSENT_SENTINELS = {"", "-", "None", "N/A", "none"}


def _coerce_absent_to_none(v: Any) -> Any:
    """Alpha Vantage often returns literal 'None' / '-' for missing scalars."""
    if isinstance(v, str) and v.strip() in _ABSENT_SENTINELS:
        return None
    return v


def _strip_trailing_percent(v: Any) -> Any:
    if isinstance(v, str) and v.endswith("%"):
        return v[:-1]
    return v


NullableDecimal = Annotated[Decimal | None, BeforeValidator(_coerce_absent_to_none)]
NullableInt = Annotated[int | None, BeforeValidator(_coerce_absent_to_none)]
PercentDecimal = Annotated[Decimal, BeforeValidator(_strip_trailing_percent)]


class StockQuote(BaseModel):
    """Validated Alpha Vantage GLOBAL_QUOTE response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    symbol: str = Field(alias="01. symbol")
    open_price: Decimal = Field(alias="02. open")
    high: Decimal = Field(alias="03. high")
    low: Decimal = Field(alias="04. low")
    price: Decimal = Field(alias="05. price")
    volume: int = Field(alias="06. volume")
    latest_trading_day: date = Field(alias="07. latest trading day")
    previous_close: Decimal = Field(alias="08. previous close")
    change: Decimal = Field(alias="09. change")
    change_percent: PercentDecimal = Field(alias="10. change percent")


class CompanyOverview(BaseModel):
    """Validated Alpha Vantage OVERVIEW response — useful subset only."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    symbol: str = Field(alias="Symbol")
    name: str = Field(alias="Name")
    asset_type: str = Field(alias="AssetType")
    description: str = Field(alias="Description")
    exchange: str = Field(alias="Exchange")
    currency: str = Field(alias="Currency")
    country: str = Field(alias="Country")
    sector: str = Field(alias="Sector")
    industry: str = Field(alias="Industry")
    market_capitalization: NullableInt = Field(alias="MarketCapitalization", default=None)
    pe_ratio: NullableDecimal = Field(alias="PERatio", default=None)
    eps: NullableDecimal = Field(alias="EPS", default=None)
    dividend_yield: NullableDecimal = Field(alias="DividendYield", default=None)
    beta: NullableDecimal = Field(alias="Beta", default=None)
    week_52_high: NullableDecimal = Field(alias="52WeekHigh", default=None)
    week_52_low: NullableDecimal = Field(alias="52WeekLow", default=None)
    analyst_target_price: NullableDecimal = Field(alias="AnalystTargetPrice", default=None)
