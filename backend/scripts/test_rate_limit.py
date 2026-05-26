"""Smoke test: verify the per-IP rate limiter fires 429 after the threshold.

Uses FastAPI's TestClient (no network I/O, no real API keys needed).
The limiter uses an in-memory store, so counters reset when the process
exits — each run of this script starts from zero.

Tested endpoints:
  /api/quote/{ticker}   — limit: 30/min  → fire 31 requests, expect 429 on #31
  /api/analyze/{ticker} — limit:  5/min  → fire  6 requests, expect 429 on #6
                          (analyze calls Alpha Vantage + Groq, so we patch the
                           pipeline to avoid real network calls)
"""

from __future__ import annotations

import sys
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

# Patch heavy services before importing app so they never touch the network.
_mock_quote = MagicMock()
_mock_quote.symbol = "IBM"
_mock_quote.open_price = "250.00"
_mock_quote.high = "255.00"
_mock_quote.low = "249.00"
_mock_quote.price = "252.00"
_mock_quote.volume = 1_000_000
_mock_quote.latest_trading_day = "2026-05-26"
_mock_quote.previous_close = "251.00"
_mock_quote.change = "1.00"
_mock_quote.change_percent = "0.40"

with (
    patch("app.services.alpha_vantage.fetch_global_quote", return_value=_mock_quote),
    patch("app.services.alpha_vantage.fetch_company_overview", return_value=MagicMock()),
    patch("app.agents.pipeline.run_full_analysis", return_value=MagicMock()),
):
    from app.main import app

client = TestClient(app, raise_server_exceptions=False)

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
errors = 0


def check(label: str, condition: bool) -> None:
    global errors
    status = PASS if condition else FAIL
    print(f"  [{status}] {label}")
    if not condition:
        errors += 1


# ── /api/quote/{ticker} — 30/min ────────────────────────────────────────────
print("\n── /api/quote/IBM (limit: 30/min) ──")

# The first request might be 503 (AV quota) or 200 — either is within-limit.
responses = [
    client.get("/api/quote/IBM", headers={"x-real-ip": "1.2.3.4"})
    for _ in range(31)
]
statuses = [r.status_code for r in responses]

within_limit = statuses[:30]
over_limit = statuses[30]

check("requests 1-30 are not 429", all(s != 429 for s in within_limit))
check("request 31 is 429", over_limit == 429)
check("429 body has 'detail' key", "detail" in responses[30].json())
check("429 has Retry-After header", "retry-after" in responses[30].headers)

print(f"  statuses: {statuses[:5]} ... {statuses[-3:]}")

# ── /api/analyze/{ticker} — 5/min ────────────────────────────────────────────
print("\n── /api/analyze/IBM (limit: 5/min) ──")

# Patch run_full_analysis at the router level for these requests.
with patch("app.routers.analyze.run_full_analysis", return_value=MagicMock(
    ticker="IBM", company_name="IBM", overall_view="neutral",
    one_line_summary="test", key_strengths=[], key_risks=[],
    data_snapshot=MagicMock(), sentiment_snapshot=MagicMock(),
    model_used="test", generated_at="2026-05-26T00:00:00Z",
)):
    analyze_responses = [
        client.get("/api/analyze/IBM", headers={"x-real-ip": "5.6.7.8"})
        for _ in range(6)
    ]

analyze_statuses = [r.status_code for r in analyze_responses]

check("requests 1-5 are not 429", all(s != 429 for s in analyze_statuses[:5]))
check("request 6 is 429", analyze_statuses[5] == 429)
check("429 body has 'detail' key", "detail" in analyze_responses[5].json())

print(f"  statuses: {analyze_statuses}")

# ── /health is unrestricted ──────────────────────────────────────────────────
print("\n── /health (no limit) ──")
health_statuses = [client.get("/health").status_code for _ in range(10)]
check("10 rapid /health requests all succeed", all(s == 200 for s in health_statuses))

# ── summary ──────────────────────────────────────────────────────────────────
print(f"\n{'All checks passed.' if errors == 0 else f'{errors} check(s) failed.'}")
sys.exit(0 if errors == 0 else 1)
