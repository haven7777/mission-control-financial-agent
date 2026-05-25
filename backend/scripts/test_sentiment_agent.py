"""Smoke test for the Sentiment Agent (Tavily + Groq via LangGraph).

Run from the project root:
    backend/venv/bin/python backend/scripts/test_sentiment_agent.py [TICKER]

Default ticker is IBM.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.sentiment_agent import (  # noqa: E402
    MissingLLMKey,
    MissingNewsAPIKey,
    NewsFetchError,
    NoArticlesFoundError,
    run_sentiment_agent,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("test_sentiment_agent")


def main() -> int:
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "IBM"
    log.info("Running Sentiment Agent for %s ...", ticker)
    try:
        report = run_sentiment_agent(ticker)
    except (MissingLLMKey, MissingNewsAPIKey) as exc:
        log.error("Missing key: %s", exc)
        return 2
    except NoArticlesFoundError as exc:
        log.error("No articles: %s", exc)
        return 3
    except NewsFetchError as exc:
        log.error("News fetch failed: %s: %s", type(exc).__name__, exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected: %s", exc)
        return 4

    print()
    print(f"=== Sentiment Agent report for {report.ticker} ===")
    print(f"  Query:                {report.query!r}")
    print(f"  Articles analyzed:    {report.articles_analyzed}")
    print(f"  Overall sentiment:    {report.overall_sentiment.value}")
    print(f"  Overall confidence:   {report.overall_confidence:.2f}")
    print(f"  Fetched at:           {report.fetched_at.isoformat()}")
    print()
    for i, ca in enumerate(report.classified, start=1):
        print(f"[{i}] {ca.sentiment.value.upper():<8} ({ca.confidence:.2f})  {ca.article.title}")
        print(f"     {ca.article.url}")
        print(f"     reason: {ca.reason}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
