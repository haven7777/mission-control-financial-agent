"""Shared retry decorator for LLM calls.

Retries only on transient network/quota errors. ValidationError and other
LLM-output schema problems are NOT retryable — that's a prompt issue, not
a transient failure, and retrying just burns API budget.
"""

from __future__ import annotations

import logging

import httpx
import openai
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger(__name__)

_RETRYABLE = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
    httpx.ConnectError,
    httpx.ReadTimeout,
)

llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
