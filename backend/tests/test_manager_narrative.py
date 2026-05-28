"""Tests for deep_narrative field in ManagerSynthesis and FinalReport.

Covers:
  1. deep_narrative is None by default on FinalReport
  2. deep_narrative is stored when passed to FinalReport
  3. ManagerSynthesis.deep_narrative is optional (defaults to None)
  4. ManagerSynthesis accepts 6 items in key_strengths and key_risks
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.models.agents import DataAgentReport
from app.models.financial import CompanyOverview, StockQuote
from app.models.manager import FinalReport, ManagerSynthesis, OverallView
from app.models.sentiment import Sentiment, SentimentAgentReport


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_stock_quote() -> StockQuote:
    return StockQuote.model_validate({
        "symbol": "TEST",
        "open_price": "100.00",
        "high": "105.00",
        "low": "99.00",
        "price": "102.00",
        "volume": 1_000_000,
        "latest_trading_day": date(2026, 5, 28),
        "previous_close": "101.00",
        "change": "1.00",
        "change_percent": "0.99",
    })


def _make_overview() -> CompanyOverview:
    return CompanyOverview.model_validate({
        "symbol": "TEST",
        "name": "Test Corp",
        "asset_type": "Common Stock",
        "description": "A test company.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "country": "USA",
        "sector": "Technology",
        "industry": "Software",
    })


def _make_data_report() -> DataAgentReport:
    return DataAgentReport(
        ticker="TEST",
        quote=_make_stock_quote(),
        overview=_make_overview(),
        fetched_at=datetime.now(timezone.utc),
    )


def _make_sentiment_report() -> SentimentAgentReport:
    return SentimentAgentReport.model_validate({
        "ticker": "TEST",
        "query": "TEST stock news",
        "articles_analyzed": 0,
        "overall_sentiment": Sentiment.NEUTRAL.value,
        "overall_confidence": 0.5,
        "classified": [],
    })


def _make_final_report(**kwargs) -> FinalReport:
    """Build a minimal FinalReport, allowing overrides via kwargs."""
    base = dict(
        ticker="TEST",
        company_name="Test Corp",
        overall_view=OverallView.NEUTRAL,
        one_line_summary="Test summary.",
        key_strengths=["Strength one."],
        key_risks=["Risk one."],
        data_snapshot=_make_data_report(),
        sentiment_snapshot=_make_sentiment_report(),
        model_used="gpt-4o",
    )
    base.update(kwargs)
    return FinalReport(**base)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_deep_narrative_none_by_default():
    """FinalReport.deep_narrative should be None when not supplied."""
    r = _make_final_report()
    assert r.deep_narrative is None


def test_deep_narrative_present():
    """FinalReport stores deep_narrative when explicitly provided."""
    narrative = "Para1\n\nPara2\n\nPara3"
    r = _make_final_report(deep_narrative=narrative)
    assert r.deep_narrative == narrative


def test_manager_synthesis_deep_narrative_optional():
    """ManagerSynthesis.deep_narrative defaults to None when omitted."""
    synthesis = ManagerSynthesis(
        overall_view=OverallView.POSITIVE,
        one_line_summary="Looks good.",
        key_strengths=["Strong revenue growth."],
        key_risks=["High debt load."],
    )
    assert synthesis.deep_narrative is None


def test_manager_synthesis_max_length_six():
    """ManagerSynthesis accepts up to 6 items in key_strengths and key_risks."""
    strengths = [f"Strength {i}." for i in range(1, 7)]
    risks = [f"Risk {i}." for i in range(1, 7)]
    synthesis = ManagerSynthesis(
        overall_view=OverallView.MIXED,
        one_line_summary="Mixed signals.",
        key_strengths=strengths,
        key_risks=risks,
    )
    assert len(synthesis.key_strengths) == 6
    assert len(synthesis.key_risks) == 6
