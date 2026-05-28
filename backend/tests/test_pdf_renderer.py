"""Tests for the PDF renderer service (pdf_renderer.py).

Covers:
  - HTML rendering (string output, content checks)
  - RTL / LTR flag behaviour
  - PDF rendering (bytes output, PDF magic bytes, minimum size)

WeasyPrint uses C system libraries (GObject/Pango) that may not be present
on all developer workstations. We pre-stub the weasyprint module in
sys.modules so that pdf_renderer can be imported and the lazy
``from weasyprint import HTML`` inside render_report_pdf resolves to a mock.
The HTML tests run against the real Jinja2 pipeline with no mocking.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# Pre-stub weasyprint before any import tries to load its C extensions.
# Use setdefault so we get the already-registered stub if another test module
# pre-registered one first (e.g. test_export_router), then read it back from
# sys.modules so _weasyprint_stub always refers to the live stub object.
_weasyprint_stub = MagicMock()
sys.modules.setdefault("weasyprint", _weasyprint_stub)
_weasyprint_stub = sys.modules["weasyprint"]  # always the canonical stub

from app.models.agents import DataAgentReport  # noqa: E402
from app.models.financial import CompanyOverview, StockQuote  # noqa: E402
from app.models.manager import FinalReport, OverallView  # noqa: E402
from app.models.sentiment import Sentiment, SentimentAgentReport  # noqa: E402
from app.services.pdf_renderer import render_report_html, render_report_pdf  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_report() -> FinalReport:
    quote = StockQuote(
        symbol="TEST",
        open_price=Decimal("150.00"),
        high=Decimal("155.00"),
        low=Decimal("148.00"),
        price=Decimal("152.50"),
        volume=1_000_000,
        latest_trading_day=date(2025, 1, 15),
        previous_close=Decimal("149.00"),
        change=Decimal("3.50"),
        change_percent=Decimal("2.35"),
    )

    overview = CompanyOverview(
        symbol="TEST",
        name="Test Corp",
        asset_type="Common Stock",
        description="A test company for unit testing purposes.",
        exchange="NASDAQ",
        currency="USD",
        country="USA",
        sector="Technology",
        industry="Software",
        market_capitalization=500_000_000_000,
        pe_ratio=Decimal("28.5"),
        eps=Decimal("5.35"),
        dividend_yield=Decimal("0.005"),
        beta=Decimal("1.2"),
        week_52_high=Decimal("180.00"),
        week_52_low=Decimal("120.00"),
        analyst_target_price=Decimal("170.00"),
    )

    data_snapshot = DataAgentReport(
        ticker="TEST",
        quote=quote,
        overview=overview,
        fetched_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        financial_metrics={},
    )

    sentiment_snapshot = SentimentAgentReport(
        ticker="TEST",
        query="Test Corp latest news",
        articles_analyzed=0,
        overall_sentiment=Sentiment.BULLISH,
        overall_confidence=0.75,
        classified=[],
        fetched_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        news_sentiment={},
        is_zero_news=True,
    )

    return FinalReport(
        ticker="TEST",
        company_name="Test Corp",
        overall_view=OverallView.POSITIVE,
        one_line_summary="Test Corp is well-positioned for growth.",
        key_strengths=["Strong balance sheet", "Market leadership"],
        key_risks=["Regulatory uncertainty", "Competitive pressure"],
        data_snapshot=data_snapshot,
        sentiment_snapshot=sentiment_snapshot,
        model_used="claude-sonnet-4-6",
        generated_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Minimal but valid PDF bytes (version header + EOF marker).
_FAKE_PDF = b"%PDF-1.4\n%%EOF\n" + b"x" * 2000


def _make_mock_html(return_bytes: bytes = _FAKE_PDF) -> MagicMock:
    """Return a mock that mimics ``weasyprint.HTML(string=...).write_pdf()``."""
    mock_instance = MagicMock()
    mock_instance.write_pdf.return_value = return_bytes
    mock_html_cls = MagicMock(return_value=mock_instance)
    return mock_html_cls


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_render_html_returns_string(sample_report: FinalReport) -> None:
    """render_report_html returns a non-empty HTML string containing the company name."""
    html = render_report_html(sample_report)
    assert isinstance(html, str)
    assert "Test Corp" in html
    assert "<html" in html


def test_render_html_rtl_flag(sample_report: FinalReport) -> None:
    """When rtl=True the template emits RTL direction and Hebrew lang attributes."""
    html = render_report_html(sample_report, rtl=True)
    assert 'dir="rtl"' in html
    assert 'lang="he"' in html


def test_render_html_ltr_default(sample_report: FinalReport) -> None:
    """Default (rtl=False) renders LTR direction."""
    html = render_report_html(sample_report)
    assert 'dir="ltr"' in html


def test_render_pdf_returns_bytes(sample_report: FinalReport) -> None:
    """render_report_pdf returns bytes and starts with the PDF magic bytes."""
    mock_html_cls = _make_mock_html(_FAKE_PDF)
    _weasyprint_stub.HTML = mock_html_cls
    pdf = render_report_pdf(sample_report)
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_render_pdf_rtl(sample_report: FinalReport) -> None:
    """RTL PDF is rendered successfully and is of reasonable size."""
    mock_html_cls = _make_mock_html(_FAKE_PDF)
    _weasyprint_stub.HTML = mock_html_cls
    pdf = render_report_pdf(sample_report, rtl=True)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
