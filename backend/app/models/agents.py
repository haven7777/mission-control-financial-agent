"""Cross-agent data contracts.

Each agent has a typed input and a typed output Pydantic model so that
no untyped dicts cross the boundary between agents (architecture rule:
"every step between agents must pass through strict Pydantic validation").
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.financial import CompanyOverview, StockQuote


class DataAgentReport(BaseModel):
    """The Data Agent's structured output.

    Combines the freshly-validated `StockQuote` and `CompanyOverview` with
    a couple of cheap derived fields useful to downstream agents.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str
    quote: StockQuote
    overview: CompanyOverview
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def market_cap_billions(self) -> Decimal | None:
        if self.overview.market_capitalization is None:
            return None
        return (Decimal(self.overview.market_capitalization) / Decimal(1_000_000_000)).quantize(Decimal("0.01"))

    @property
    def is_within_52_week_band(self) -> bool | None:
        hi = self.overview.week_52_high
        lo = self.overview.week_52_low
        if hi is None or lo is None:
            return None
        return lo <= self.quote.price <= hi
