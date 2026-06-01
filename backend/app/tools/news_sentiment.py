from __future__ import annotations

from typing import TypedDict

from langchain_core.tools import tool

from app.services.tavily import search as _tavily_search


class NewsArticleDict(TypedDict):
    title: str
    content: str
    url: str
    published_date: str | None
    raw_content: str | None


class NewsSentimentResult(TypedDict):
    ticker: str
    query: str
    articles: list[NewsArticleDict]


@tool
def get_news_sentiment(ticker: str) -> NewsSentimentResult:
    """Fetch recent market narratives for a stock ticker via Tavily."""
    symbol = ticker.strip().upper()
    query = f"{symbol} stock analyst outlook investor narrative market view product releases"
    
    result = _tavily_search(
        query, 
        max_results=5, 
        search_depth="advanced", 
        include_raw_content=True
    )

    articles: list[NewsArticleDict] = [
        NewsArticleDict(
            title=a.title,
            content=a.content,
            url=a.url,
            published_date=a.published_date,
            raw_content=getattr(a, "raw_content", None)
        )
        for a in result.articles
    ]

    return NewsSentimentResult(
        ticker=symbol,
        query=query,
        articles=articles,
    )