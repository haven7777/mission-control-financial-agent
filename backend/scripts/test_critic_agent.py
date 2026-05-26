"""Smoke test: run the full pipeline then audit the result with the Critic Agent.

Usage:
    PYTHONPATH=backend backend/venv/bin/python backend/scripts/test_critic_agent.py [TICKER]
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv("backend/.env")

ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "IBM"
print(f"\nRunning full pipeline + Critic Agent for {ticker}…\n")

# --- Data Agent (with stub fallback) ----------------------------------------

from app.services.alpha_vantage import DataFetchError
from app.agents.data_agent import run_data_agent

try:
    data = run_data_agent(ticker)
    print(f"Data Agent   : {data.ticker} price={data.quote.price}")
except DataFetchError as exc:
    print(f"Data Agent   : live fetch failed ({exc}) — using IBM stub")
    from app.models.financial import CompanyOverview, StockQuote
    from app.models.agents import DataAgentReport
    data = DataAgentReport(
        ticker="IBM",
        quote=StockQuote(
            symbol="IBM", open_price=Decimal("262"), high=Decimal("264"),
            low=Decimal("253"), price=Decimal("253.84"), volume=17_000_000,
            latest_trading_day=date(2026, 5, 22), previous_close=Decimal("252.97"),
            change=Decimal("0.87"), change_percent=Decimal("0.34"),
        ),
        overview=CompanyOverview(
            symbol="IBM", name="International Business Machines Corporation",
            asset_type="EQUITY",
            description="IBM provides integrated IT solutions and services.",
            exchange="NYSE", currency="USD", country="United States",
            sector="Technology", industry="Information Technology Services",
            market_capitalization=238_000_000_000, pe_ratio=Decimal("22.46"),
            eps=Decimal("11.30"), dividend_yield=Decimal("2.66"),
            beta=Decimal("0.58"), week_52_high=Decimal("324.90"),
            week_52_low=Decimal("212.34"), analyst_target_price=Decimal("277.68"),
        ),
    )

# --- Sentiment Agent ---------------------------------------------------------

from app.agents.sentiment_agent import run_sentiment_agent

sentiment = run_sentiment_agent(data.ticker)
print(f"Sentiment    : {sentiment.overall_sentiment.value} "
      f"(confidence {sentiment.overall_confidence:.2f}, "
      f"{sentiment.articles_analyzed} articles)")

# --- Manager Agent -----------------------------------------------------------

from app.agents.manager_agent import run_manager_agent

report = run_manager_agent(data, sentiment)
print(f"Manager      : {report.overall_view.value} — {report.one_line_summary[:80]}…")

# --- Critic Agent ------------------------------------------------------------

from app.agents.critic_agent import run_critic_agent

critique = run_critic_agent(report, data, sentiment)
cr = critique.critique_result

print(f"\n{'─'*60}")
print(f"CRITIC VERDICT     : {cr.verdict.value.upper()}")
print(f"Synthesis confidence: {cr.synthesis_confidence:.2f}")
print(f"Issues found        : {len(cr.issues)}")

for issue in cr.issues:
    print(f"  [{issue.severity.value.upper()}] {issue.field}: {issue.issue}")

if cr.revision_instruction:
    print(f"\nRevision instruction:\n  {cr.revision_instruction}")
else:
    print("\nNo revision instruction (synthesis approved).")

print(f"{'─'*60}\n")
print("Done — check https://smith.langchain.com for the full trace.")
