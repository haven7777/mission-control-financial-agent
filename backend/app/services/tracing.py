"""LangSmith tracing activation.

pydantic-settings reads `.env` into the Settings object but does NOT write
values back into os.environ.  LangGraph / LangChain check os.environ at
call-time for both the old LANGCHAIN_* and new LANGSMITH_* variable names.
Call `configure_langsmith_tracing()` once at startup (before any agent
invocations) to bridge the gap.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


def configure_langsmith_tracing() -> bool:
    """Propagate LangSmith settings from the app config into os.environ.

    Returns True when tracing is enabled, False otherwise.
    Idempotent — safe to call more than once.
    """
    from app.config import get_settings  # local import avoids circular deps

    s = get_settings()

    if not s.langsmith_configured:
        log.info(
            "LangSmith tracing disabled "
            "(set LANGSMITH_API_KEY + LANGSMITH_TRACING=true to enable)"
        )
        return False

    # LangGraph 1.x and newer LangChain SDKs read LANGSMITH_* vars.
    # Older LangChain callbacks still check LANGCHAIN_* — set both for safety.
    pairs = {
        "LANGSMITH_API_KEY": s.langsmith_api_key,
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_PROJECT": s.langsmith_project,
        "LANGSMITH_ENDPOINT": s.langsmith_endpoint,
        "LANGCHAIN_TRACING_V2": "true",
        "LANGCHAIN_API_KEY": s.langsmith_api_key,
        "LANGCHAIN_PROJECT": s.langsmith_project,
    }
    for key, value in pairs.items():
        os.environ.setdefault(key, value)  # type: ignore[arg-type]

    log.info(
        "LangSmith tracing enabled — project=%r endpoint=%s",
        s.langsmith_project,
        s.langsmith_endpoint,
    )
    return True
