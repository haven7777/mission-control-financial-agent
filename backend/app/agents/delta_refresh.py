"""Delta refresh engine for cache-hit pipeline paths.

On a cache hit, re-runs only the cheap agents:
  - DataAgent: fresh yfinance price snapshot (~0.5s)
  - Tavily: news published since the cached report's generated_at (days filter)

The expensive synthesis (overall_view, key_strengths/risks, bull/bear cases,
filings_context, transcript_context) is reused from the cached FinalReport.
Returns a new FinalReport with delta_refreshed=True.

All failures are non-fatal: falls back to the cached sub-report on any error.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from math import ceil

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.data_agent import run_data_agent
from app.config import get_settings
from app.models.manager import FinalReport
from app.models.news import NewsArticle
from app.models.sentiment import (
    ClassifiedArticle,
    Sentiment,
    SentimentAgentReport,
    SentimentClassificationBatch,
)
from app.services import tavily as tavily_svc

log = logging.getLogger(__name__)

_CLASSIFY_SYSTEM_PROMPT = (
    "You are a financial sentiment analyst. For each news article provided, "
    "classify the sentiment toward the company's stock as bullish, bearish, or neutral. "
    "Respond as a JSON object: "
    '{"classifications": [{"article_index": <int>, "sentiment": "bullish"|"bearish"|"neutral", '
    '"confidence": <0.0-1.0>, "reason": "<one sentence>"}, ...]}'
)


def _classify_articles(ticker: str, articles: list[NewsArticle]) -> list[ClassifiedArticle]:
    """Run LLM sentiment classification on delta news articles. Non-fatal."""
    if not articles:
        return []
    settings = get_settings()
    if not settings.openai_api_key:
        log.warning("delta_refresh: no OpenAI key — skipping classification")
        return []

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.0,
    )
    structured = llm.with_structured_output(SentimentClassificationBatch, method="json_mode")
    user_payload = "\n\n".join(
        f"[{i}] Title: {a.title}\nSnippet: {a.content.strip()[:600]}"
        for i, a in enumerate(articles)
    )
    try:
        batch: SentimentClassificationBatch = structured.invoke([
            SystemMessage(content=_CLASSIFY_SYSTEM_PROMPT),
            HumanMessage(content=f"Ticker: {ticker}\n\nArticles:\n{user_payload}"),
        ])
    except Exception as exc:  # noqa: BLE001
        log.warning("delta_refresh: LLM classification failed: %s", exc)
        return []

    by_index = {c.article_index: c for c in batch.classifications}
    return [
        ClassifiedArticle(
            article=articles[i],
            sentiment=by_index[i].sentiment if i in by_index else Sentiment.NEUTRAL,
            confidence=by_index[i].confidence if i in by_index else 0.0,
            reason=by_index[i].reason if i in by_index else "Classification omitted.",
        )
        for i in range(len(articles))
    ]


def run_delta_refresh(cached: FinalReport) -> FinalReport:
    """Return a FinalReport with live price + delta news, reusing cached synthesis.

    Never raises — on any sub-failure, falls back to the cached snapshot.
    """
    ticker = cached.ticker

    # 1. Fresh live price
    try:
        fresh_data = run_data_agent(ticker)
        log.info("delta_refresh: live price loaded for %s (price=%s)", ticker, fresh_data.quote.price)
    except Exception as exc:  # noqa: BLE001
        log.warning("delta_refresh: DataAgent failed — reusing cached data: %s", exc)
        fresh_data = cached.data_snapshot

    # 2. Delta news since cache timestamp
    hours_since = (datetime.now(timezone.utc) - cached.generated_at).total_seconds() / 3600
    days_back = max(1, ceil(hours_since / 24))

    fresh_sentiment = cached.sentiment_snapshot  # default: reuse if scan fails
    try:
        result = tavily_svc.search(
            f"{ticker} stock news",
            max_results=5,
            days=days_back,
        )
        if result.articles:
            classified = _classify_articles(ticker, result.articles)
            counts = Counter(c.sentiment for c in classified)
            overall = counts.most_common(1)[0][0] if counts else Sentiment.NEUTRAL
            overall_conf = (
                sum(c.confidence for c in classified) / len(classified)
                if classified else 0.0
            )
            fresh_sentiment = SentimentAgentReport(
                ticker=ticker,
                query=result.query,
                articles_analyzed=len(result.articles),
                overall_sentiment=overall,
                overall_confidence=overall_conf,
                classified=classified,
            )
            log.info("delta_refresh: %d delta articles classified for %s", len(result.articles), ticker)
        else:
            log.info("delta_refresh: no delta news for %s — reusing cached sentiment", ticker)
    except Exception as exc:  # noqa: BLE001
        log.warning("delta_refresh: Tavily scan failed — reusing cached sentiment: %s", exc)

    return FinalReport(
        ticker=ticker,
        company_name=cached.company_name,
        overall_view=cached.overall_view,
        one_line_summary=cached.one_line_summary,
        key_strengths=cached.key_strengths,
        key_risks=cached.key_risks,
        bull_case=cached.bull_case,
        bear_case=cached.bear_case,
        filings_context=cached.filings_context,
        transcript_context=cached.transcript_context,
        deep_narrative=cached.deep_narrative,
        data_snapshot=fresh_data,
        sentiment_snapshot=fresh_sentiment,
        model_used=cached.model_used,
        delta_refreshed=True,
        generated_at=cached.generated_at,
    )
