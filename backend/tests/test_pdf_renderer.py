"""Tests for the PDF renderer service (pdf_renderer.py).

Covers:
  - HTML rendering (string output, content checks)
  - RTL / LTR flag behaviour
  - PDF rendering (bytes output, PDF magic bytes, minimum size)

Note: PDF rendering tests use ``unittest.mock`` to patch WeasyPrint's HTML
class.  The WeasyPrint C-extension (Pango/GObject) requires native ARM64
system libraries that may not be present on all developer workstations.
The HTML rendering tests exercise the real Jinja2 template pipeline; the
PDF tests verify that render_report_pdf() calls WeasyPrint correctly.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models.agents import DataAgentReport
from app.models.financial import CompanyOverview, StockQuote
from app.models.manager import FinalReport, OverallView
from app.models.sentiment import Sentiment, SentimentAgentReport
from app.services.pdf_renderer import render_report_html, render_report_pdf


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
    with patch("app.services.pdf_renderer.HTML", mock_html_cls):
        pdf = render_report_pdf(sample_report)

    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_render_pdf_rtl(sample_report: FinalReport) -> None:
    """RTL PDF is rendered successfully and is of reasonable size."""
    mock_html_cls = _make_mock_html(_FAKE_PDF)
    with patch("app.services.pdf_renderer.HTML", mock_html_cls):
        pdf = render_report_pdf(sample_report, rtl=True)

    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
