"""Smoke test for the Manager Agent.

Run from the project root:
    backend/venv/bin/python backend/scripts/test_manager_agent.py [TICKER]

The Data Agent is attempted live; if it fails (e.g. Alpha Vantage daily
quota exhausted), the script falls back to a hand-crafted IBM data stub
so the Manager's synthesis can still be exercised. Sentiment runs live
(Tavily + Groq, both unaffected by the AV quota).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.data_agent import run_data_agent  # noqa: E402
from app.agents.manager_agent import run_manager_agent  # noqa: E402
from app.agents.sentiment_agent import run_sentiment_agent  # noqa: E402
from app.models.agents import DataAgentReport  # noqa: E402
from app.models.financial import CompanyOverview, StockQuote  # noqa: E402
from app.services.alpha_vantage import DataFetchError  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("test_manager_agent")


def _ibm_stub() -> DataAgentReport:
    """Hand-crafted IBM DataAgentReport mirroring values observed during testing.

    Used only when the live Data Agent fails (typically because the
    Alpha Vantage free-tier daily quota is exhausted). The Manager
    Agent's behaviour is invariant to where its inputs come from.
    """
    quote = StockQuote(
        symbol="IBM",
        open_price=Decimal("262.0500"),
        high=Decimal("264.3800"),
        low=Decimal("253.3900"),
        price=Decimal("253.8400"),
        volume=19_072_873,
        latest_trading_day=datetime(2026, 5, 22, tzinfo=timezone.utc).date(),
        previous_close=Decimal("252.9700"),
        change=Decimal("0.8700"),
        change_percent=Decimal("0.3439"),
    )
    overview = CompanyOverview(
        symbol="IBM",
        name="International Business Machines",
        asset_type="Common Stock",
        description=(
            "International Business Machines Corporation (IBM) is an American "
            "multinational technology company headquartered in Armonk, New York. "
            "IBM operates in cloud, AI infrastructure, consulting, and quantum "
            "computing."
        ),
        exchange="NYSE",
        currency="USD",
        country="USA",
        sector="TECHNOLOGY",
        industry="INFORMATION TECHNOLOGY SERVICES",
        market_capitalization=237_762_789_000,
        pe_ratio=Decimal("22.37"),
        eps=Decimal("11.31"),
        dividend_yield=Decimal("0.0299"),
        beta=Decimal("0.581"),
        week_52_high=Decimal("320.70"),
        week_52_low=Decimal("212.34"),
        analyst_target_price=Decimal("277.68"),
    )
    return DataAgentReport(ticker="IBM", quote=quote, overview=overview)


def _get_data(ticker: str) -> tuple[DataAgentReport, bool]:
    """Try the live Data Agent; fall back to an IBM stub on failure."""
    try:
        return run_data_agent(ticker), False
    except DataFetchError as exc:
        log.warning("Data Agent failed (%s): %s", type(exc).__name__, exc)
        if ticker.upper() != "IBM":
            log.error("No stub available for ticker %r; aborting.", ticker)
            raise
        log.warning("Falling back to IBM stub data for synthesis demo.")
        return _ibm_stub(), True


def main() -> int:
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "IBM"

    log.info("Step 1: Data Agent for %s ...", ticker)
    data, used_stub = _get_data(ticker)

    log.info("Step 2: Sentiment Agent for %s ...", ticker)
    sentiment = run_sentiment_agent(ticker)

    log.info("Step 3: Manager Agent (synthesis) ...")
    report = run_manager_agent(data, sentiment)

    print()
    print("=" * 72)
    print(f"  FINAL REPORT — {report.company_name} ({report.ticker})")
    if used_stub:
        print("  ⚠  (Data section came from stub — live Alpha Vantage was unavailable.)")
    print("=" * 72)
    print(f"  Overall view:   {report.overall_view.value.upper()}")
    print(f"  Headline:       {report.one_line_summary}")
    print()
    print("  Key strengths:")
    for s in report.key_strengths:
        print(f"    + {s}")
    print()
    print("  Key risks:")
    for r in report.key_risks:
        print(f"    - {r}")
    print()
    print(f"  Model:          {report.model_used}")
    print(f"  Generated at:   {report.generated_at.isoformat()}")
    print()
    print(f"  Grounded in:    price=${data.quote.price} "
          f"(change {data.quote.change_percent}%), "
          f"market cap {data.market_cap_billions}B, "
          f"news sentiment {sentiment.overall_sentiment.value} "
          f"({sentiment.overall_confidence:.2f}) across "
          f"{sentiment.articles_analyzed} articles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
