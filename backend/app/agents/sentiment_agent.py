"""Sentiment Agent — Tavily news fetch + Groq LLM classification.

Two-node LangGraph:
    START -> fetch_news -> classify -> END

`fetch_news` calls our typed Tavily service. `classify` calls Groq with
LangChain's structured-output binding so the LLM is forced into the
`SentimentClassificationBatch` Pydantic shape; any drift surfaces as a
typed validation error rather than a free-form parse.

Public entry point: `run_sentiment_agent(ticker) -> SentimentAgentReport`.
"""

from __future__ import annotations

import logging
from collections import Counter

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.config import get_settings
from app.models.news import NewsArticle
from app.models.sentiment import (
    ArticleSentiment,
    ClassifiedArticle,
    Sentiment,
    SentimentAgentReport,
    SentimentClassificationBatch,
)
from app.services.tavily import MissingNewsAPIKey, NewsFetchError
from app.tools.news_sentiment import get_news_sentiment
from app.utils.llm_retry import llm_retry

log = logging.getLogger(__name__)

DEFAULT_MAX_ARTICLES = 5
SYSTEM_PROMPT = (
"You are a financial sentiment analyst. You will be given a list of recent "
    "news articles about a publicly-traded company. For each article, classify "
    "the sentiment toward the company's stock as one of:\n"
    "  - 'bullish': positive outlook, good news, growth, beats, etc.\n"
    "  - 'bearish': negative outlook, concerns, downgrades, declines, etc.\n"
    "  - 'neutral': informational, mixed, or no clear directional impact.\n\n"
    "CLASSIFICATION RULES:\n"
    "1. Avoid Defaulting to 'neutral': Financial articles almost always include standard risk disclaimers "
    "(e.g., 'macroeconomic headwinds', 'regulatory risks'). Do not classify an article as 'neutral' "
    "just because it contains these standard disclaimers.\n"
    "2. Identify the Dominant Narrative: Weigh the primary focus of the article. If the core catalyst "
    "or headline event is positive, classify as 'bullish', even if minor risks are mentioned at the end. "
    "Only use 'neutral' if the article genuinely presents a 50/50 split of equally impactful good and bad news.\n"
    "3. Be Decisive: Attempt to identify a directional lean ('bullish' or 'bearish') based on the author's "
    "overall tone and the main financial catalyst discussed.\n\n"
    "Respond as a JSON object matching this schema:\n"
    '  {"classifications": [{"article_index": <int>, "sentiment": '
    '"bullish"|"bearish"|"neutral", "confidence": <0.0-1.0>, '
    '"reason": "<one sentence>"}, ...]}\n'
    "Return one entry per article, in order.\n\n"
    "SIGNAL STRENGTH RULE: The `confidence` field represents Signal Strength — "
    "a score from 0.0 to 1.0 based on the QUALITY and QUANTITY of the source, "
    "NOT the probability of the sentiment direction. If the article comes from a "
    "credible financial outlet (major news sites, analyst reports, company filings, "
    "earnings releases, SEC disclosures), the confidence MUST be above 0.85 even "
    "if the sentiment consensus is Neutral or Mixed. Reserve low scores (below 0.5) "
    "only for low-quality, irrelevant, or spam-like content."
)


# --- Exceptions --------------------------------------------------------------

class SentimentAgentError(Exception):
    """Base class for Sentiment Agent failures."""


class MissingLLMKey(SentimentAgentError):
    """No Groq key configured."""


class NoArticlesFoundError(SentimentAgentError):
    """News search returned zero usable articles."""


# --- Graph state -------------------------------------------------------------

class _SentimentAgentState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    query: str | None = None
    articles: list[NewsArticle] | None = None
    classifications: list[ArticleSentiment] | None = None
    news_sentiment_raw: dict = {}


# --- Nodes -------------------------------------------------------------------

def _fetch_news_node(state: _SentimentAgentState) -> dict:
    log.info("sentiment_agent: fetching narratives for %s via NewsSentimentTool", state.ticker)
    raw: dict = get_news_sentiment.run(state.ticker)
    articles = [
        NewsArticle(
            title=a["title"],
            url=a["url"],
            content=a.get("raw_content", a.get("content", "")),
            published_date=a.get("published_date"),
        )
        for a in raw.get("articles", [])
    ]
    if not articles:
        raise NoArticlesFoundError(f"No news articles found for ticker {state.ticker!r}")
    return {"query": raw.get("query", state.ticker), "articles": articles, "news_sentiment_raw": raw}


def _classify_node(state: _SentimentAgentState) -> dict:
    if not state.articles:
        raise NoArticlesFoundError("classify node reached with no articles in state")

    settings = get_settings()
    if not settings.openai_api_key:
        raise MissingLLMKey("OPENAI_API_KEY is not set in backend/.env")

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.0,
    )
    # `method="json_mode"` keeps us compatible with models that don't expose
    # strict `json_schema` mode (e.g. llama-3.3-70b-versatile). Groq returns
    # raw JSON; Pydantic validates it client-side against
    # `SentimentClassificationBatch`.
    structured = llm.with_structured_output(
        SentimentClassificationBatch, method="json_mode"
    )

    user_payload = "\n\n".join(
        f"[{i}] Title: {a.title}\nSnippet: {a.content.strip()[:600]}"
        for i, a in enumerate(state.articles)
    )

    log.info("sentiment_agent: classifying %d articles via Groq (%s)",
             len(state.articles), settings.openai_model)

    @llm_retry
    def _invoke() -> SentimentClassificationBatch:
        return structured.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Ticker: {state.ticker}\n\nArticles:\n{user_payload}"),
        ])

    batch: SentimentClassificationBatch = _invoke()

    # Defensive: align classifications to articles by index.
    by_index: dict[int, ArticleSentiment] = {c.article_index: c for c in batch.classifications}
    aligned: list[ArticleSentiment] = []
    for i in range(len(state.articles)):
        c = by_index.get(i)
        if c is None:
            log.warning("LLM omitted classification for article %d; defaulting to neutral.", i)
            aligned.append(ArticleSentiment(
                article_index=i,
                sentiment=Sentiment.NEUTRAL,
                confidence=0.0,
                reason="LLM omitted this article; defaulted to neutral.",
            ))
        else:
            aligned.append(c)
    return {"classifications": aligned}


def _build_graph():
    graph: StateGraph = StateGraph(_SentimentAgentState)
    graph.add_node("fetch_news", _fetch_news_node)
    graph.add_node("classify", _classify_node)
    graph.add_edge(START, "fetch_news")
    graph.add_edge("fetch_news", "classify")
    graph.add_edge("classify", END)
    return graph.compile()


_compiled_graph = _build_graph()


# --- Public API --------------------------------------------------------------

def run_sentiment_agent(ticker: str) -> SentimentAgentReport:
    """Invoke the Sentiment Agent for a single ticker.

    Raises `NewsFetchError` / `MissingNewsAPIKey` / `MissingLLMKey` /
    `NoArticlesFoundError` on the corresponding failure mode.
    """
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("ticker must be non-empty")

    result = _compiled_graph.invoke({"ticker": normalized})
    query = result["query"]
    articles: list[NewsArticle] = result["articles"]
    classifications: list[ArticleSentiment] = result["classifications"]
    news_sentiment_raw: dict = result["news_sentiment_raw"] if isinstance(result, dict) else result.news_sentiment_raw

    classified: list[ClassifiedArticle] = [
        ClassifiedArticle(
            article=articles[c.article_index],
            sentiment=c.sentiment,
            confidence=c.confidence,
            reason=c.reason,
        )
        for c in classifications
        if 0 <= c.article_index < len(articles)
    ]

    counts = Counter(c.sentiment for c in classifications)
    overall = counts.most_common(1)[0][0] if counts else Sentiment.NEUTRAL
    overall_confidence = (
        sum(c.confidence for c in classifications) / len(classifications)
        if classifications else 0.0
    )

    return SentimentAgentReport(
        ticker=normalized,
        query=query,
        articles_analyzed=len(articles),
        overall_sentiment=overall,
        overall_confidence=overall_confidence,
        classified=classified,
        news_sentiment=news_sentiment_raw,
    )


# Re-export common errors so callers don't have to know the import path.
__all__ = [
    "run_sentiment_agent",
    "SentimentAgentError",
    "MissingLLMKey",
    "NoArticlesFoundError",
    "NewsFetchError",
    "MissingNewsAPIKey",
]
