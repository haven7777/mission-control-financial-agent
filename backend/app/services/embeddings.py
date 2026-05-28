"""OpenAI text-embedding-3-small wrapper."""

from __future__ import annotations
import logging
from openai import OpenAI
from app.config import get_settings

log = logging.getLogger(__name__)
_MODEL = "text-embedding-3-small"


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed texts with OpenAI text-embedding-3-small. Returns list of 1536-dim float vectors."""
    if not texts:
        return []
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    log.info("embeddings: embedding %d text(s)", len(texts))
    response = client.embeddings.create(model=_MODEL, input=texts)
    return [item.embedding for item in response.data]
