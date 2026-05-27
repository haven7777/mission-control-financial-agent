"""Sentiment-classification models.

The LLM returns `ArticleSentiment` per article via structured output;
the agent aggregates into a `SentimentAgentReport`. Confidence is the
model's own self-reported confidence in its classification (0.0-1.0).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.news import NewsArticle


class Sentiment(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ArticleSentiment(BaseModel):
    """The LLM's structured judgement for one article."""

    article_index: int = Field(ge=0, description="0-based index into the article list.")
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(description="One-sentence justification.")


class SentimentClassificationBatch(BaseModel):
    """Shape requested from the LLM in a single call (all articles at once)."""

    classifications: list[ArticleSentiment]


class ClassifiedArticle(BaseModel):
    """An article paired with its classification, returned to callers."""

    model_config = ConfigDict(extra="forbid")

    article: NewsArticle
    sentiment: Sentiment
    confidence: float
    reason: str


class SentimentAgentReport(BaseModel):
    """Final Sentiment Agent output."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    query: str
    articles_analyzed: int
    overall_sentiment: Sentiment
    overall_confidence: float = Field(ge=0.0, le=1.0)
    classified: list[ClassifiedArticle]
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    news_sentiment: dict = Field(default_factory=dict)
    is_zero_news: bool = False
