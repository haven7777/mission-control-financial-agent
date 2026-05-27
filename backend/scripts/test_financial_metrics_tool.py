"""Smoke test for FinancialMetricsTool.

Run from the backend directory:
    python scripts/test_financial_metrics_tool.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tools.financial_metrics import get_financial_metrics


def test_financial_metrics():
    result = get_financial_metrics.run("AAPL")
    print("Result:", result)
    assert isinstance(result, dict), "must return a dict"
    assert result["ticker"] == "AAPL"
    for key in ("price", "pe_ratio", "market_cap", "week_52_high", "week_52_low",
                "next_earnings_date", "eps", "beta"):
        assert key in result, f"missing key: {key}"
    print("✓ all required keys present")
    print(f"  next_earnings_date = {result['next_earnings_date']}")
    print(f"  market_cap        = {result['market_cap']}")
    print(f"  pe_ratio          = {result['pe_ratio']}")


if __name__ == "__main__":
    test_financial_metrics()
