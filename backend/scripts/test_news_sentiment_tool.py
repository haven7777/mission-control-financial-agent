"""Smoke test for NewsSentimentTool.

Run from the backend directory:
    python scripts/test_news_sentiment_tool.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tools.news_sentiment import get_news_sentiment


def test_news_sentiment():
    result = get_news_sentiment.run("AAPL")
    print("Result keys:", list(result.keys()))
    assert isinstance(result, dict)
    assert result["ticker"] == "AAPL"
    assert "query" in result
    assert "articles" in result
    assert isinstance(result["articles"], list)
    print(f"✓ fetched {len(result['articles'])} narrative articles")
    for a in result["articles"]:
        assert "title" in a and "content" in a, f"article missing keys: {a.keys()}"
        print(f"  - {a['title'][:70]}")


if __name__ == "__main__":
    test_news_sentiment()
