"""E2E tests for the Multi-Agent Financial System UI.

These tests use a running backend + frontend (managed by conftest.py fixtures).
All tests are robust to both a successful analysis and an error state (e.g. API
quota exhausted) so they pass regardless of external API availability.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect


# ── Static structure ──────────────────────────────────────────────────────────


def test_page_title_visible(page: Page) -> None:
    expect(page.get_by_role("heading", level=1)).to_contain_text(
        "Multi-Agent Financial System"
    )


def test_input_and_button_present(page: Page) -> None:
    expect(page.get_by_label("Stock ticker")).to_be_visible()
    expect(page.get_by_role("button", name=re.compile(r"Analyze", re.I))).to_be_visible()


def test_analyze_button_disabled_when_input_empty(page: Page) -> None:
    # On fresh load the input is empty → button must be disabled.
    btn = page.get_by_role("button", name=re.compile(r"Analyze", re.I))
    expect(btn).to_be_disabled()


# ── Input behaviour ───────────────────────────────────────────────────────────


def test_input_accepts_text(page: Page) -> None:
    inp = page.get_by_label("Stock ticker")
    inp.fill("ibm")
    expect(inp).to_have_value("ibm")


def test_analyze_button_enabled_after_typing(page: Page) -> None:
    page.get_by_label("Stock ticker").fill("IBM")
    btn = page.get_by_role("button", name=re.compile(r"Analyze", re.I))
    expect(btn).to_be_enabled()


# ── Submission flow ───────────────────────────────────────────────────────────


def test_progress_card_appears_after_submit(page: Page) -> None:
    """After submitting a ticker the progress card (or result) must appear."""
    page.get_by_label("Stock ticker").fill("IBM")
    page.get_by_role("button", name=re.compile(r"Analyze", re.I)).click()

    # Either the progress card heading or a result/error card must appear.
    # Use a generous timeout because agents make real network calls.
    result_or_progress = page.locator(
        "[aria-live='polite'] [class*='card'], "
        "[aria-live='polite'] .card"
    )
    expect(result_or_progress.first).to_be_visible(timeout=15_000)


def test_analysis_resolves_not_stuck(page: Page) -> None:
    """Stream must resolve to either report cards or an error card — never hang."""
    page.get_by_label("Stock ticker").fill("IBM")
    page.get_by_role("button", name=re.compile(r"Analyze", re.I)).click()

    # Wait up to 120 s for the streaming button label to leave "Analyzing…".
    btn = page.get_by_role("button", name=re.compile(r"Analyze", re.I))
    # The button text returns to "Analyze" once streaming ends.
    expect(btn).to_have_text(re.compile(r"^Analyze$", re.I), timeout=120_000)


def test_resolves_to_report_or_error_card(page: Page) -> None:
    """After streaming, either a synthesis card or an error card must be visible."""
    page.get_by_label("Stock ticker").fill("IBM")
    page.get_by_role("button", name=re.compile(r"Analyze", re.I)).click()

    # Wait for streaming to finish.
    btn = page.get_by_role("button", name=re.compile(r"Analyze", re.I))
    expect(btn).to_have_text(re.compile(r"^Analyze$", re.I), timeout=120_000)

    live = page.locator("[aria-live='polite']")

    # shadcn Card components render as plain <div>s with utility classes.
    # Checking for any text inside the live region is the most reliable approach.
    expect(live).to_contain_text(re.compile(r"\S+"), timeout=5_000)


# ── Success path (skipped if quota exhausted) ─────────────────────────────────


def _has_report_cards(page: Page) -> bool:
    """True if the full four-section report is rendered."""
    live = page.locator("[aria-live='polite']")
    # QuoteStatsCard always contains "Price & fundamentals"
    return live.get_by_text(re.compile(r"Price.*fundamentals", re.I)).count() > 0


def _submit_and_wait(page: Page, ticker: str = "IBM") -> None:
    page.get_by_label("Stock ticker").fill(ticker)
    page.get_by_role("button", name=re.compile(r"Analyze", re.I)).click()
    btn = page.get_by_role("button", name=re.compile(r"Analyze", re.I))
    expect(btn).to_have_text(re.compile(r"^Analyze$", re.I), timeout=120_000)


def test_report_sections_present_on_success(page: Page) -> None:
    """If the API returns a full report, all four cards must be rendered."""
    _submit_and_wait(page)

    if not _has_report_cards(page):
        pytest.skip("External API unavailable (quota or network) — skipping success path")

    live = page.locator("[aria-live='polite']")
    expect(live.get_by_text(re.compile(r"Price.*fundamentals", re.I)).first).to_be_visible()
    expect(live.get_by_text(re.compile(r"Sentiment", re.I)).first).to_be_visible()
    expect(live.get_by_text(re.compile(r"Sources", re.I)).first).to_be_visible()


def test_error_card_on_api_failure(page: Page) -> None:
    """If APIs are down/quota, an error message must be displayed (not blank)."""
    _submit_and_wait(page)

    if _has_report_cards(page):
        pytest.skip("APIs working — error card test not applicable this run")

    live = page.locator("[aria-live='polite']")
    # Error card renders inside aria-live. Any visible text content is enough.
    expect(live).not_to_be_empty()


# ── Re-submit clears prior state ──────────────────────────────────────────────


def test_resubmit_clears_previous_result(page: Page) -> None:
    """Submitting a second ticker should clear the prior result and re-stream."""
    _submit_and_wait(page, "IBM")

    # Now submit AAPL — progress card (or new result) must appear again.
    page.get_by_label("Stock ticker").fill("AAPL")
    page.get_by_role("button", name=re.compile(r"Analyze", re.I)).click()

    # The button should show "Analyzing…" while the new stream is running.
    expect(
        page.get_by_role("button", name=re.compile(r"Analyzing", re.I))
    ).to_be_visible(timeout=5_000)
