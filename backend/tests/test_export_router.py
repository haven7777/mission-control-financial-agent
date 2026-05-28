"""Integration tests for POST /api/export/pdf.

WeasyPrint cannot load its system libs on this machine (macOS ARM64/Rosetta
mismatch), so we pre-stub the weasyprint module in sys.modules before any
import resolves it, and then mock render_report_pdf to return fake bytes.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Pre-stub weasyprint before any import tries to load its C extensions.
_weasyprint_stub = MagicMock()
sys.modules.setdefault("weasyprint", _weasyprint_stub)

from datetime import date, datetime, timezone  # noqa: E402
from decimal import Decimal  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models.agents import DataAgentReport  # noqa: E402
from app.models.financial import CompanyOverview, StockQuote  # noqa: E402
from app.models.manager import FinalReport, OverallView  # noqa: E402
from app.models.sentiment import Sentiment, SentimentAgentReport  # noqa: E402

client = TestClient(app)

_FAKE_PDF = b"%PDF-1.4\n%%EOF"

# ---------------------------------------------------------------------------
# Helper: build a minimal but valid FinalReport
# ---------------------------------------------------------------------------

def _make_report() -> FinalReport:
    quote = StockQuote(
        symbol="AAPL",
        open_price=Decimal("170.00"),
        high=Decimal("175.00"),
        low=Decimal("168.00"),
        price=Decimal("172.50"),
        volume=50_000_000,
        latest_trading_day=date(2025, 1, 15),
        previous_close=Decimal("169.00"),
        change=Decimal("3.50"),
        change_percent=Decimal("2.07"),
    )

    overview = CompanyOverview(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type="Common Stock",
        description="Apple designs and manufactures consumer electronics.",
        exchange="NASDAQ",
        currency="USD",
        country="USA",
        sector="Technology",
        industry="Consumer Electronics",
    )

    data_snapshot = DataAgentReport(
        ticker="AAPL",
        quote=quote,
        overview=overview,
        fetched_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        financial_metrics={},
    )

    sentiment_snapshot = SentimentAgentReport(
        ticker="AAPL",
        query="Apple Inc latest news",
        articles_analyzed=5,
        overall_sentiment=Sentiment.BULLISH,
        overall_confidence=0.80,
        classified=[],
        fetched_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        news_sentiment={},
        is_zero_news=False,
    )

    return FinalReport(
        ticker="AAPL",
        company_name="Apple Inc.",
        overall_view=OverallView.POSITIVE,
        one_line_summary="Apple is well-positioned for continued growth.",
        key_strengths=["Strong ecosystem", "High margins"],
        key_risks=["Regulatory scrutiny", "China exposure"],
        data_snapshot=data_snapshot,
        sentiment_snapshot=sentiment_snapshot,
        model_used="claude-sonnet-4-6",
        generated_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_export_pdf_returns_pdf() -> None:
    """Valid master code + report body → 200 with PDF response."""
    report = _make_report()
    with patch("app.services.master_code_auth._validate_code", return_value=True), \
         patch("app.routers.export.render_report_pdf", return_value=_FAKE_PDF):
        response = client.post(
            "/api/export/pdf",
            json=report.model_dump(mode="json"),
            headers={"X-Master-Code": "valid-test-code"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
    assert "AAPL_deep_research.pdf" in response.headers["content-disposition"]


def test_export_pdf_rejects_bad_code() -> None:
    """Invalid master code → 403."""
    report = _make_report()
    with patch("app.services.master_code_auth._validate_code", return_value=False):
        response = client.post(
            "/api/export/pdf",
            json=report.model_dump(mode="json"),
            headers={"X-Master-Code": "bad-code"},
        )

    assert response.status_code == 403


def test_export_pdf_rejects_no_auth() -> None:
    """Missing auth header → 401."""
    report = _make_report()
    response = client.post(
        "/api/export/pdf",
        json=report.model_dump(mode="json"),
    )

    assert response.status_code == 401


def test_export_pdf_rtl_flag() -> None:
    """?rtl=true is forwarded to render_report_pdf as rtl=True."""
    report = _make_report()
    with patch("app.services.master_code_auth._validate_code", return_value=True), \
         patch("app.routers.export.render_report_pdf", return_value=_FAKE_PDF) as mock_render:
        response = client.post(
            "/api/export/pdf?rtl=true",
            json=report.model_dump(mode="json"),
            headers={"X-Master-Code": "valid-test-code"},
        )

    assert response.status_code == 200
    mock_render.assert_called_once()
    _, kwargs = mock_render.call_args
    assert kwargs.get("rtl") is True
