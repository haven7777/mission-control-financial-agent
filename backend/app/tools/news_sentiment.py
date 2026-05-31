from __future__ import annotations

from typing import TypedDict

from langchain_core.tools import tool

from app.services.tavily import search as _tavily_search


class NewsArticleDict(TypedDict):
    title: str
    content: str
    url: str
    published_date: str | None
    raw_content: str | None  # <--- התוספת הקריטית לטיפוס הנתונים


class NewsSentimentResult(TypedDict):
    ticker: str
    query: str
    articles: list[NewsArticleDict]


@tool
def get_news_sentiment(ticker: str) -> NewsSentimentResult:
    """Fetch recent market narratives for a stock ticker via Tavily.

    Queries specifically for analyst opinions and investor narratives
    rather than generic news headlines, providing richer context for
    sentiment classification.
    """
    symbol = ticker.strip().upper()
    # הרחבתי מעט את השאילתה כדי שתתפוס גם מוצרים והשקות 
    query = f"{symbol} stock analyst outlook investor narrative market view product releases"
    
    # שינוי עומק החיפוש והוספת דרישה לתוכן גולמי
    result = _tavily_search(
        query, 
        max_results=5, 
        search_depth="advanced", 
        include_raw_content=True # הפקודה ששואבת את הכתבה המלאה
    )

    articles: list[NewsArticleDict] = [
        NewsArticleDict(
            title=a.title,
            content=a.content,
            url=a.url,
            published_date=a.published_date,
            # שליפת התוכן המלא מהאובייקט שחזר מ-Tavily
            raw_content=getattr(a, "raw_content", None) 
        )
        for a in result.articles
    ]

    return NewsSentimentResult(
        ticker=symbol,
        query=query,
        articles=articles,
    )
