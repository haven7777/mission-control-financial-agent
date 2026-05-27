"""Live integration smoke test for the ReportCache service.

Requires:
  - SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in backend/.env
  - The reports table created via backend/scripts/setup_supabase.sql

Run: cd backend && source venv/bin/activate && python scripts/test_report_cache.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.agents import DataAgentReport
from app.models.financial import CompanyOverview, StockQuote
from app.models.manager import FinalReport, OverallView
from app.models.sentiment import Sentiment, SentimentAgentReport
from app.services.report_cache import get_cached_report, store_report
from app.services.supabase_client import get_supabase_client

_TICKER = "_TEST"


def _make_test_report() -> FinalReport:
    quote = StockQuote(
        symbol=_TICKER,
        price=Decimal("100.00"),
        open_price=Decimal("99.00"),
        high=Decimal("101.00"),
        low=Decimal("98.00"),
        previous_close=Decimal("99.00"),
        change=Decimal("1.00"),
        change_percent=Decimal("1.01"),
        volume=1_000_000,
        latest_trading_day=date(2026, 5, 27),
    )
    overview = CompanyOverview(
        symbol=_TICKER,
        name="Test Corp",
        asset_type="Common Stock",
        description="Synthetic ticker for cache smoke test.",
        exchange="TEST",
        currency="USD",
        country="USA",
        sector="Technology",
        industry="Software",
    )
    data_report = DataAgentReport(
        ticker=_TICKER,
        quote=quote,
        overview=overview,
        fetched_at=datetime.now(timezone.utc),
    )
    sentiment_report = SentimentAgentReport(
        ticker=_TICKER,
        query=f"{_TICKER} stock analyst outlook",
        articles_analyzed=0,
        overall_sentiment=Sentiment.NEUTRAL,
        overall_confidence=0.0,
        classified=[],
        fetched_at=datetime.now(timezone.utc),
        is_zero_news=True,
    )
    return FinalReport(
        ticker=_TICKER,
        company_name="Test Corp",
        overall_view=OverallView.NEUTRAL,
        one_line_summary="Smoke-test report — safe to delete.",
        key_strengths=["Test strength"],
        key_risks=["Test risk"],
        data_snapshot=data_report,
        sentiment_snapshot=sentiment_report,
        model_used="test",
    )


def _cleanup() -> None:
    try:
        get_supabase_client().table("reports").delete().eq("ticker", _TICKER).execute()
        print(f"  cleanup: deleted test rows for ticker={_TICKER!r}")
    except Exception as exc:
        print(f"  cleanup: WARNING — {exc}")


def main() -> None:
    print("=== ReportCache smoke test ===\n")

    _cleanup()

    print("1. Cache miss before storing…")
    assert get_cached_report(_TICKER) is None, "Expected None before storing"
    print("   ✓ confirmed cache miss\n")

    print("2. Storing test report…")
    report = _make_test_report()
    store_report(report)
    print("   ✓ stored\n")

    print("3. Retrieving from cache…")
    cached = get_cached_report(_TICKER)
    assert cached is not None, "Expected cache hit after storing"
    assert cached.ticker == _TICKER
    assert cached.overall_view == OverallView.NEUTRAL
    assert cached.one_line_summary == report.one_line_summary
    print(f"   ✓ cache hit: ticker={cached.ticker}, view={cached.overall_view}\n")

    _cleanup()

    print("4. Confirming miss after cleanup…")
    assert get_cached_report(_TICKER) is None, "Expected None after cleanup"
    print("   ✓ confirmed cache miss\n")

    print("✅ All checks passed")


if __name__ == "__main__":
    main()
