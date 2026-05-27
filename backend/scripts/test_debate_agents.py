"""Smoke test for Bull Agent, Bear Agent, and debate-mode Manager synthesis.

Run from the backend directory:
    python scripts/test_debate_agents.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.data_agent import run_data_agent
from app.agents.sentiment_agent import run_sentiment_agent, NoArticlesFoundError
from app.agents.bull_agent import run_bull_agent
from app.agents.bear_agent import run_bear_agent
from app.agents.manager_agent import run_manager_agent
from app.models.sentiment import Sentiment, SentimentAgentReport

TICKER = "AAPL"

print("== Data Agent ==")
data = run_data_agent(TICKER)
print(f"  price={data.quote.price}, pe={data.overview.pe_ratio}")

print("\n== Sentiment Agent ==")
try:
    sentiment = run_sentiment_agent(TICKER)
    print(f"  overall={sentiment.overall_sentiment.value}, confidence={sentiment.overall_confidence:.2f}")
except NoArticlesFoundError:
    sentiment = SentimentAgentReport(
        ticker=TICKER, query="N/A", articles_analyzed=0,
        overall_sentiment=Sentiment.NEUTRAL, overall_confidence=0.0,
        classified=[], is_zero_news=True,
    )
    print("  zero-news sentinel used")

print("\n== Bull Agent ==")
bull = run_bull_agent(data, sentiment)
print(f"  thesis: {bull.thesis[:120]}…")
for a in bull.key_arguments:
    print(f"  + {a}")
assert len(bull.key_arguments) >= 2, "expected at least 2 bull arguments"

print("\n== Bear Agent ==")
bear = run_bear_agent(data, sentiment)
print(f"  thesis: {bear.thesis[:120]}…")
for a in bear.key_arguments:
    print(f"  - {a}")
assert len(bear.key_arguments) >= 2, "expected at least 2 bear arguments"

print("\n== Manager Agent (debate mode) ==")
final = run_manager_agent(data, sentiment, bull_case=bull, bear_case=bear)
print(f"  overall_view: {final.overall_view}")
print(f"  summary: {final.one_line_summary}")
assert final.bull_case is not None, "expected bull_case in FinalReport"
assert final.bear_case is not None, "expected bear_case in FinalReport"
print("\n✓ All debate assertions passed")
